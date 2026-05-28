from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO


def normalize_targets_bed(targets_bed: Path, out_bed: Path) -> Path:
    out_bed.parent.mkdir(parents=True, exist_ok=True)
    with targets_bed.open() as source, out_bed.open("w") as out:
        for line_number, line in enumerate(source, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            chrom, start, end = _parse_bed3_fields(stripped.split(), targets_bed, line_number)
            out.write(f"{chrom}\t{start}\t{end}\n")
    return out_bed


def extract_pass_intervals(
    quantized_bed_gz: Path,
    out_bed: Path,
    *,
    pass_label: str = "PASS",
) -> Path:
    out_bed.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(quantized_bed_gz, "rt") as source, out_bed.open("w") as out:
        for line_number, line in enumerate(source, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if len(fields) < 4:
                raise ValueError(
                    f"{quantized_bed_gz}:{line_number} must have at least four columns"
                )
            if fields[3] != pass_label:
                continue
            chrom, start, end = _parse_bed3_fields(fields[:3], quantized_bed_gz, line_number)
            out.write(f"{chrom}\t{start}\t{end}\n")
    return out_bed


def extract_merged_pass_intervals(
    quantized_bed_gz: Path,
    out_bed: Path,
    *,
    pass_label: str = "PASS",
) -> Path:
    out_bed.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(quantized_bed_gz, "rt") as source, out_bed.open("w") as out:
        current: tuple[str, int, int] | None = None
        for line_number, line in enumerate(source, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if len(fields) < 4:
                raise ValueError(
                    f"{quantized_bed_gz}:{line_number} must have at least four columns"
                )
            if fields[3] != pass_label:
                _flush_merged_interval(out, current)
                current = None
                continue

            chrom, start, end = _parse_bed3_fields(fields[:3], quantized_bed_gz, line_number)
            if current and current[0] == chrom and current[2] == start:
                current = (current[0], current[1], end)
            else:
                _flush_merged_interval(out, current)
                current = (chrom, start, end)

        _flush_merged_interval(out, current)
    return out_bed


def count_bed_sites(bed_path: Path) -> int:
    return sum(end - start for _chrom, start, end in iter_bed3(bed_path))


def iter_bed3(bed_path: Path) -> Iterator[tuple[str, int, int]]:
    with bed_path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields = stripped.split()
            if _looks_like_header(fields):
                continue
            yield _parse_bed3_fields(fields, bed_path, line_number)


def write_bed3_from_intervals(intervals: list[tuple[str, int, int]], out_bed: Path) -> Path:
    out_bed.parent.mkdir(parents=True, exist_ok=True)
    with out_bed.open("w") as out:
        for chrom, start, end in intervals:
            if start >= end:
                raise ValueError(f"invalid interval {chrom}:{start}-{end}")
            out.write(f"{chrom}\t{start}\t{end}\n")
    return out_bed


def _parse_bed3_fields(fields: list[str], source: Path, line_number: int) -> tuple[str, int, int]:
    if len(fields) < 3:
        raise ValueError(f"{source}:{line_number} must have at least three columns")
    chrom = fields[0]
    try:
        start = int(fields[1])
        end = int(fields[2])
    except ValueError as error:
        raise ValueError(f"{source}:{line_number} has non-integer BED coordinates") from error
    if start < 0 or end < 0:
        raise ValueError(f"{source}:{line_number} has negative BED coordinates")
    if start >= end:
        raise ValueError(f"{source}:{line_number} must have start < end")
    return chrom, start, end


def _looks_like_header(fields: list[str]) -> bool:
    return len(fields) >= 3 and fields[0].lower() == "chrom" and fields[1].lower() == "start"


def _flush_merged_interval(
    out: TextIO,
    current: tuple[str, int, int] | None,
) -> None:
    if current is None:
        return
    chrom, start, end = current
    out.write(f"{chrom}\t{start}\t{end}\n")
