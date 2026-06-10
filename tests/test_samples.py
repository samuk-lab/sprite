from __future__ import annotations

from pathlib import Path

import pytest

from wisp_mask.models import Sample
from wisp_mask.samples import (
    read_popfile,
    read_samples,
    validate_sample_populations,
    validate_samples,
)


def test_read_samples_with_header(tmp_path: Path) -> None:
    alignment = tmp_path / "sample.bam"
    alignment.write_bytes(b"bam")
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text(
        "sample_id\tpopulation\talignment\n"
        f"sample_1\tpopA\t{alignment}\n"
    )

    samples = read_samples(samples_tsv)

    assert len(samples) == 1
    assert samples[0].sample_id == "sample_1"
    assert samples[0].population == "popA"
    assert samples[0].alignment == alignment


def test_read_samples_without_header_resolves_relative_to_sample_file(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "alignments"
    alignment_dir.mkdir()
    alignment = alignment_dir / "sample.bam"
    alignment.write_bytes(b"bam")
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("sample_1\tpopA\talignments/sample.bam\n")

    samples = read_samples(samples_tsv)

    assert samples[0].alignment == alignment


def test_read_samples_does_not_resolve_paths_beyond_sample_tsv_directory(tmp_path: Path) -> None:
    nested = tmp_path / "metadata" / "tables"
    nested.mkdir(parents=True)
    alignment = tmp_path / "bams" / "sample.bam"
    alignment.parent.mkdir()
    alignment.write_bytes(b"bam")
    samples_tsv = nested / "samples.tsv"
    samples_tsv.write_text("sample_1\tpopA\tbams/sample.bam\n")

    with pytest.raises(ValueError, match="does not exist"):
        read_samples(samples_tsv)


def test_read_samples_rejects_duplicate_ids(tmp_path: Path) -> None:
    alignment = tmp_path / "sample.bam"
    alignment.write_bytes(b"bam")
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text(
        "sample_id\tpopulation\talignment\n"
        f"sample_1\tpopA\t{alignment}\n"
        f"sample_1\tpopB\t{alignment}\n"
    )

    with pytest.raises(ValueError, match="duplicate sample_id"):
        read_samples(samples_tsv)


def test_read_samples_rejects_missing_alignment(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("sample_id\tpopulation\talignment\nsample_1\tpopA\tmissing.bam\n")

    with pytest.raises(ValueError, match="does not exist"):
        read_samples(samples_tsv)


def test_read_samples_rejects_empty_files(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("# comment\n\n")

    with pytest.raises(ValueError, match="does not contain any sample rows"):
        read_samples(samples_tsv)


def test_read_samples_rejects_too_few_columns(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("sample_1\tpopA\n")

    with pytest.raises(ValueError, match="at least three"):
        read_samples(samples_tsv)


def test_read_samples_rejects_incomplete_header(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("sample_id\tpopulation\nsample_1\tpopA\n")

    with pytest.raises(ValueError, match="missing required column.*alignment"):
        read_samples(samples_tsv)


def test_read_samples_rejects_header_missing_sample_id(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("population\talignment\npopA\tmissing.bam\n")

    with pytest.raises(ValueError, match="missing required column.*sample_id"):
        read_samples(samples_tsv)


def test_read_samples_rejects_header_missing_population(tmp_path: Path) -> None:
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text("sample_id\talignment\nsample_1\tmissing.bam\n")

    with pytest.raises(ValueError, match="missing required column.*population"):
        read_samples(samples_tsv)


def test_read_samples_rejects_alignment_directories(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "sample.bam"
    alignment_dir.mkdir()
    samples_tsv = tmp_path / "samples.tsv"
    samples_tsv.write_text(
        "sample_id\tpopulation\talignment\n"
        f"sample_1\tpopA\t{alignment_dir}\n"
    )

    with pytest.raises(ValueError, match="is a directory"):
        read_samples(samples_tsv)


def test_validate_samples_rejects_missing_alignment() -> None:
    with pytest.raises(ValueError, match="alignment.*missing"):
        validate_samples([Sample("sample_1", "popA")])


def test_read_popfile_with_header(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("sample_id\tpopulation\nsample_1\tpopA\nsample_2\tpopB\n")

    samples = read_popfile(popfile)

    assert [(sample.sample_id, sample.population, sample.alignment) for sample in samples] == [
        ("sample_1", "popA", None),
        ("sample_2", "popB", None),
    ]


def test_read_popfile_without_header(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("sample_1\tpopA\n")

    samples = read_popfile(popfile)

    assert samples[0].sample_id == "sample_1"
    assert samples[0].population == "popA"


def test_read_popfile_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text(
        "# comment\n"
        "\n"
        "   \n"
        "sample_id\tpopulation\n"
        "sample_1\tpopA\n"
        "   # indented comment\n"
        "sample_2\tpopB\n"
    )

    samples = read_popfile(popfile)

    assert [(sample.sample_id, sample.population) for sample in samples] == [
        ("sample_1", "popA"),
        ("sample_2", "popB"),
    ]


def test_read_popfile_rejects_empty_files(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("\n# comment\n")

    with pytest.raises(ValueError, match="does not contain any sample rows"):
        read_popfile(popfile)


def test_read_popfile_rejects_too_few_columns(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("sample_1\n")

    with pytest.raises(ValueError, match="at least two"):
        read_popfile(popfile)


def test_read_popfile_rejects_incomplete_header(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("sample_id\nsample_1\n")

    with pytest.raises(ValueError, match="missing required column.*population"):
        read_popfile(popfile)


def test_read_popfile_rejects_header_missing_sample_id(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text("population\npopA\n")

    with pytest.raises(ValueError, match="missing required column.*sample_id"):
        read_popfile(popfile)


def test_read_popfile_rejects_duplicate_ids(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"
    popfile.write_text(
        "sample_id\tpopulation\n"
        "sample_1\tpopA\n"
        "sample_1\tpopB\n"
    )

    with pytest.raises(ValueError, match="duplicate sample_id"):
        read_popfile(popfile)


def test_read_popfile_rejects_empty_whitespace_and_path_labels(tmp_path: Path) -> None:
    popfile = tmp_path / "popfile.tsv"

    popfile.write_text("sample_id\tpopulation\n\tpopA\n")
    with pytest.raises(ValueError, match="non-empty"):
        read_popfile(popfile)

    popfile.write_text("sample_id\tpopulation\nsample 1\tpopA\n")
    with pytest.raises(ValueError, match="whitespace"):
        read_popfile(popfile)

    popfile.write_text("sample_id\tpopulation\nsample_1\tpop/A\n")
    with pytest.raises(ValueError, match="path separators"):
        read_popfile(popfile)


def test_validate_sample_populations_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="at least one sample"):
        validate_sample_populations([])
