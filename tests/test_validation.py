from __future__ import annotations

from pathlib import Path

import pytest

from sprite_mask.validation import (
    ensure_parent_dirs,
    refuse_existing_outputs,
    require_executables,
    validate_jobs,
    validate_threads,
    validate_threshold,
)


def test_validate_threshold_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        validate_threshold(-1)


def test_validate_threshold_zero_requires_targets_or_vcf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires --targets"):
        validate_threshold(0)

    validate_threshold(0, targets_bed=tmp_path / "targets.bed")
    validate_threshold(0, all_sites_vcf=tmp_path / "all_sites.vcf")


def test_validate_threads_and_jobs_reject_values_below_one() -> None:
    with pytest.raises(ValueError, match="--threads"):
        validate_threads(0)
    with pytest.raises(ValueError, match="--jobs"):
        validate_jobs(0)

    validate_threads(1)
    validate_jobs(1)


def test_require_executables_reports_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "present":
            return "/usr/bin/present"
        return None

    monkeypatch.setattr("sprite_mask.validation.shutil.which", fake_which)

    with pytest.raises(RuntimeError, match="missing1, missing2"):
        require_executables(["present", "missing1", "missing2"])


def test_ensure_parent_dirs_creates_all_parent_directories(tmp_path: Path) -> None:
    first = tmp_path / "a" / "b" / "out.bed"
    second = tmp_path / "c" / "out.bed"

    ensure_parent_dirs([first, second])

    assert first.parent.is_dir()
    assert second.parent.is_dir()


def test_refuse_existing_outputs_rejects_existing_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "cohort.sprite.bed.gz"
    missing = tmp_path / "cohort.sprite.bed.gz.tbi"
    existing.write_text("old")

    with pytest.raises(FileExistsError, match=str(existing)):
        refuse_existing_outputs([existing, missing], force=False)


def test_refuse_existing_outputs_allows_existing_with_force(tmp_path: Path) -> None:
    existing = tmp_path / "cohort.sprite.bed.gz"
    existing.write_text("old")

    refuse_existing_outputs([existing], force=True)
