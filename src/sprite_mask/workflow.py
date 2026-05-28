from __future__ import annotations

import logging
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path

from sprite_mask.bedio import extract_merged_pass_intervals, normalize_targets_bed
from sprite_mask.bedtools import (
    intersect_sort_merge,
    run_multiinter,
    sort_and_merge_bed,
    write_single_input_multiinter,
)
from sprite_mask.collapse import collapse_population_counts
from sprite_mask.config import AlignmentRunConfig, RunConfig, VcfRunConfig
from sprite_mask.models import MosdepthOutputs, Sample, WorkflowOutputs
from sprite_mask.mosdepth import run_mosdepth
from sprite_mask.samples import read_popfile, read_samples
from sprite_mask.validation import (
    ensure_parent_dirs,
    refuse_existing_outputs,
    require_executables,
    validate_jobs,
    validate_threads,
    validate_threshold,
    validate_vcf_inputs,
)
from sprite_mask.vcf import build_population_counts_from_all_sites_vcf

logger = logging.getLogger(__name__)


def run_workflow(config: RunConfig) -> WorkflowOutputs:
    if isinstance(config, VcfRunConfig):
        validate_threshold(
            config.threshold,
            targets_bed=config.targets_bed,
            all_sites_vcf=config.all_sites_vcf,
        )
        validate_vcf_inputs(config.all_sites_vcf, config.popfile_path)
        samples = read_popfile(config.popfile_path)
    else:
        validate_threshold(config.threshold, targets_bed=config.targets_bed)
        validate_threads(config.threads)
        validate_jobs(config.jobs)
        samples = read_samples(config.samples_path)

    require_executables(_required_tools(config))

    outputs = workflow_output_paths(config.out_dir, config.threshold)
    final_paths = [
        outputs.population_count_bed_gz,
        outputs.population_count_bed_index,
    ]
    refuse_existing_outputs(final_paths, force=config.force)

    if config.dry_run:
        mode = "VCF" if isinstance(config, VcfRunConfig) else "alignment"
        logger.info(
            "dry-run: would process %d sample(s) via %s mode with threshold %d",
            len(samples),
            mode,
            config.threshold,
        )
        logger.info("dry-run: output would be written to %s", outputs.population_count_bed_gz)
        return outputs

    ensure_parent_dirs(final_paths)
    config.resolved_work_dir.mkdir(parents=True, exist_ok=True)

    generated_work_files: list[Path] = []
    if isinstance(config, VcfRunConfig):
        _build_from_all_sites_vcf(samples, config, generated_work_files)
    else:
        _build_from_alignments(samples, config, generated_work_files)

    if not config.keep_work:
        _cleanup_work_files(generated_work_files, config.resolved_work_dir)

    return outputs


def _build_from_all_sites_vcf(
    samples: list[Sample],
    config: VcfRunConfig,
    generated_work_files: list[Path],
) -> None:
    metadata = {
        "threshold": config.threshold,
        "sample_count": len(samples),
        "popfile": str(config.popfile_path),
        "all_sites_vcf": str(config.all_sites_vcf),
        "targets_bed": str(config.targets_bed) if config.targets_bed is not None else None,
    }
    population_count_bed = (
        config.resolved_work_dir / f"cohort.d{config.threshold}.population_count_quantized.bed"
    )
    generated_work_files.append(population_count_bed)
    build_population_counts_from_all_sites_vcf(
        samples,
        config.all_sites_vcf,
        population_count_bed,
        threshold=config.threshold,
        targets_bed=config.targets_bed,
        metadata=metadata,
    )

    outputs = workflow_output_paths(config.out_dir, config.threshold)
    _sort_bgzip_tabix_bed(population_count_bed, outputs.population_count_bed_gz)


def _build_from_alignments(
    samples: list[Sample],
    config: AlignmentRunConfig,
    generated_work_files: list[Path],
) -> None:
    target_bed = _prepare_targets(config, generated_work_files)
    passing_beds = _make_sample_pass_beds(samples, config, target_bed, generated_work_files)

    multiinter_tsv = config.resolved_work_dir / f"cohort.d{config.threshold}.multiinter.tsv"
    generated_work_files.append(multiinter_tsv)
    sample_names = [sample.sample_id for sample in samples]
    if len(passing_beds) == 1:
        write_single_input_multiinter(passing_beds[0], sample_names[0], multiinter_tsv)
    else:
        run_multiinter(passing_beds, sample_names, multiinter_tsv)

    metadata = {
        "threshold": config.threshold,
        "sample_count": len(samples),
        "samples_path": str(config.samples_path),
        "targets_bed": str(config.targets_bed) if config.targets_bed is not None else None,
    }
    population_count_bed = (
        config.resolved_work_dir / f"cohort.d{config.threshold}.population_count_quantized.bed"
    )
    generated_work_files.append(population_count_bed)
    collapse_population_counts(
        samples,
        multiinter_tsv,
        population_count_bed,
        metadata=metadata,
    )
    outputs = workflow_output_paths(config.out_dir, config.threshold)
    _sort_bgzip_tabix_bed(population_count_bed, outputs.population_count_bed_gz)


def workflow_output_paths(out_dir: Path, threshold: int) -> WorkflowOutputs:
    population_count_bed_gz = out_dir / "cohort.sprite.bed.gz"
    return WorkflowOutputs(
        population_count_bed_gz=population_count_bed_gz,
        population_count_bed_index=Path(f"{population_count_bed_gz}.tbi"),
    )


def _required_tools(config: RunConfig) -> tuple[str, ...]:
    if isinstance(config, VcfRunConfig):
        return ("bgzip", "tabix")
    if config.threshold == 0:
        return ("bedtools", "bgzip", "tabix")
    return ("mosdepth", "bedtools", "bgzip", "tabix")


def _prepare_targets(config: RunConfig, generated_work_files: list[Path]) -> Path | None:
    if config.targets_bed is None:
        return None

    normalized = config.resolved_work_dir / "targets.3col.bed"
    sorted_merged = config.resolved_work_dir / "targets.3col.sorted.merged.bed"
    generated_work_files.extend([normalized, sorted_merged])
    normalize_targets_bed(config.targets_bed, normalized)
    sort_and_merge_bed(normalized, sorted_merged)
    return sorted_merged


def _make_sample_pass_beds(
    samples: list[Sample],
    config: AlignmentRunConfig,
    target_bed: Path | None,
    generated_work_files: list[Path],
) -> list[Path]:
    if config.jobs == 1 or len(samples) == 1:
        results = [_make_sample_pass_bed(sample, config, target_bed) for sample in samples]
    else:
        max_workers = min(config.jobs, len(samples))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda sample: _make_sample_pass_bed(sample, config, target_bed),
                    samples,
                )
            )

    passing_beds: list[Path] = []
    for pass_bed, _mosdepth_output, sample_work_files in results:
        passing_beds.append(pass_bed)
        generated_work_files.extend(sample_work_files)
    return passing_beds


def _make_sample_pass_bed(
    sample: Sample,
    config: AlignmentRunConfig,
    target_bed: Path | None,
) -> tuple[Path, MosdepthOutputs | None, list[Path]]:
    sample_prefix = config.resolved_work_dir / f"{sample.sample_id}.d{config.threshold}"
    generated_work_files: list[Path] = []

    if config.threshold == 0:
        if target_bed is None:
            raise ValueError("--threshold 0 requires --targets")
        target_copy = Path(f"{sample_prefix}.pass.targets.bed")
        shutil.copyfile(target_bed, target_copy)
        generated_work_files.append(target_copy)
        return target_copy, None, generated_work_files

    logger.info("processing sample %s", sample.sample_id)
    mosdepth_outputs = run_mosdepth(sample, config)
    generated_work_files.extend(
        [
            mosdepth_outputs.quantized_bed_gz,
            mosdepth_outputs.quantized_bed_index,
            mosdepth_outputs.summary,
            mosdepth_outputs.global_dist,
            mosdepth_outputs.stderr_log,
        ]
    )

    merged_pass_bed = Path(f"{sample_prefix}.pass.bed")
    generated_work_files.append(merged_pass_bed)
    extract_merged_pass_intervals(mosdepth_outputs.quantized_bed_gz, merged_pass_bed)

    if target_bed is None:
        return merged_pass_bed, mosdepth_outputs, generated_work_files

    clipped_pass_bed = Path(f"{sample_prefix}.pass.targets.bed")
    generated_work_files.append(clipped_pass_bed)
    intersect_sort_merge(merged_pass_bed, target_bed, clipped_pass_bed)
    return clipped_pass_bed, mosdepth_outputs, generated_work_files


def _sort_bgzip_tabix_bed(in_bed: Path, out_bed_gz: Path) -> None:
    sorted_bed = out_bed_gz.with_suffix("")
    body_bed = sorted_bed.with_suffix(f"{sorted_bed.suffix}.body")
    sorted_body_bed = sorted_bed.with_suffix(f"{sorted_bed.suffix}.sorted_body")
    header_lines: list[str] = []

    out_bed_gz.parent.mkdir(parents=True, exist_ok=True)
    with in_bed.open() as source, body_bed.open("w") as body:
        for line in source:
            fields = line.rstrip("\n").split("\t")
            if not fields or fields == [""]:
                continue
            if line.startswith("#"):
                header_lines.append(line)
                continue
            if len(fields) >= 3 and fields[0] == "chrom" and fields[1] == "start":
                header_lines.append("#" + line)
                continue
            body.write(line)

    try:
        with sorted_body_bed.open("w") as sorted_body_out:
            subprocess.run(
                ["sort", "-k1,1", "-k2,2n", str(body_bed)],
                check=True,
                stdout=sorted_body_out,
                text=True,
                env={**__import__("os").environ, "LC_ALL": "C"},
            )

        with sorted_bed.open("w") as sorted_out, sorted_body_bed.open() as sorted_body:
            sorted_out.writelines(header_lines)
            for line in sorted_body:
                sorted_out.write(line)

        subprocess.run(["bgzip", "-f", str(sorted_bed)], check=True)
        subprocess.run(["tabix", "-f", "-p", "bed", str(out_bed_gz)], check=True)
    finally:
        with suppress(FileNotFoundError):
            body_bed.unlink()
        with suppress(FileNotFoundError):
            sorted_body_bed.unlink()
        with suppress(FileNotFoundError):
            sorted_bed.unlink()


def _cleanup_work_files(paths: list[Path], work_dir: Path) -> None:
    for path in reversed(paths):
        try:
            path.unlink()
        except FileNotFoundError:
            continue

    with suppress(OSError):
        work_dir.rmdir()
