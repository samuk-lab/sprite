from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path


def validate_threshold(
    threshold: int,
    *,
    targets_bed: Path | None = None,
    all_sites_vcf: Path | None = None,
) -> None:
    if threshold < 0:
        raise ValueError("--threshold must be a non-negative integer")
    if threshold == 0 and targets_bed is None and all_sites_vcf is None:
        raise ValueError("--threshold 0 requires --targets because no genome.txt is required")


def validate_threads(threads: int) -> None:
    if threads < 1:
        raise ValueError("--threads must be at least 1")


def validate_jobs(jobs: int) -> None:
    if jobs < 1:
        raise ValueError("--jobs must be at least 1")


def validate_vcf_inputs(all_sites_vcf: Path, popfile_path: Path) -> None:
    if not all_sites_vcf.exists():
        raise ValueError(f"--all-sites-vcf does not exist: {all_sites_vcf}")
    if all_sites_vcf.is_dir():
        raise ValueError(f"--all-sites-vcf is a directory: {all_sites_vcf}")
    if not popfile_path.exists():
        raise ValueError(f"--popfile does not exist: {popfile_path}")
    if popfile_path.is_dir():
        raise ValueError(f"--popfile is a directory: {popfile_path}")


def require_executables(names: Iterable[str]) -> None:
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"required executable(s) not found on PATH: {', '.join(missing)}")


def ensure_parent_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def refuse_existing_outputs(paths: Iterable[Path], *, force: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        joined = "\n".join(str(path) for path in existing)
        raise FileExistsError(f"output file(s) already exist; pass --force to overwrite:\n{joined}")
