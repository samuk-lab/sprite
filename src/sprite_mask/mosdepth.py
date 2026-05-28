from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sprite_mask.config import AlignmentRunConfig
from sprite_mask.models import MosdepthOutputs, Sample


def run_mosdepth(sample: Sample, config: AlignmentRunConfig) -> MosdepthOutputs:
    prefix = config.resolved_work_dir / f"{sample.sample_id}.d{config.threshold}"
    outputs = mosdepth_outputs_for_prefix(prefix)
    outputs.stderr_log.parent.mkdir(parents=True, exist_ok=True)

    command = build_mosdepth_command(sample, config, prefix)
    env = os.environ.copy()
    env.update({"MOSDEPTH_Q0": "FAIL", "MOSDEPTH_Q1": "PASS"})

    with outputs.stderr_log.open("w") as stderr_log:
        subprocess.run(
            command,
            check=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=stderr_log,
        )

    missing_outputs = [
        path
        for path in (outputs.quantized_bed_gz, outputs.summary, outputs.global_dist)
        if not path.exists()
    ]
    if missing_outputs:
        raise FileNotFoundError(
            "mosdepth did not create expected file(s): "
            + ", ".join(str(path) for path in missing_outputs)
        )

    return MosdepthOutputs(
        prefix=outputs.prefix,
        quantized_bed_gz=outputs.quantized_bed_gz,
        quantized_bed_index=outputs.quantized_bed_index,
        summary=outputs.summary,
        global_dist=outputs.global_dist,
        stderr_log=outputs.stderr_log,
        command=tuple(command),
    )


def build_mosdepth_command(sample: Sample, config: AlignmentRunConfig, prefix: Path) -> list[str]:
    if sample.alignment is None:
        raise ValueError(f"alignment for sample {sample.sample_id!r} is required")

    command = [
        "mosdepth",
        "--threads",
        str(config.threads),
        "--no-per-base",
        "--quantize",
        f"0:{config.threshold}:",
    ]
    if not config.strict_depth:
        command.append("--fast-mode")
    if config.mapq is not None:
        command.extend(["--mapq", str(config.mapq)])
    if config.exclude_flag is not None:
        command.extend(["--flag", str(config.exclude_flag)])
    if config.reference is not None:
        command.extend(["--fasta", str(config.reference)])

    command.extend([str(prefix), str(sample.alignment)])
    return command


def mosdepth_outputs_for_prefix(prefix: Path) -> MosdepthOutputs:
    prefix_text = str(prefix)
    return MosdepthOutputs(
        prefix=prefix,
        quantized_bed_gz=Path(f"{prefix_text}.quantized.bed.gz"),
        quantized_bed_index=Path(f"{prefix_text}.quantized.bed.gz.csi"),
        summary=Path(f"{prefix_text}.mosdepth.summary.txt"),
        global_dist=Path(f"{prefix_text}.mosdepth.global.dist.txt"),
        stderr_log=Path(f"{prefix_text}.mosdepth.stderr.log"),
    )
