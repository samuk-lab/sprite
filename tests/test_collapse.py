from __future__ import annotations

import json
from pathlib import Path

import pytest

from sprite_mask.collapse import collapse_population_counts
from sprite_mask.models import Sample


def test_collapse_population_counts_merges_equal_population_vectors(tmp_path: Path) -> None:
    samples = [
        Sample("s1", "popA", tmp_path / "s1.bam"),
        Sample("s2", "popA", tmp_path / "s2.bam"),
        Sample("s3", "popB", tmp_path / "s3.bam"),
    ]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text(
        "chrom\tstart\tend\tnum\tlist\ts1\ts2\ts3\n"
        "chr1\t0\t10\t2\ts1,s3\t1\t0\t1\n"
        "chr1\t10\t20\t2\ts2,s3\t0\t1\t1\n"
        "chr1\t20\t25\t1\ts3\t0\t0\t1\n"
    )
    out = tmp_path / "population_counts.bed"

    collapse_population_counts(samples, multiinter, out)

    metadata = _read_header_metadata(out)
    assert metadata["format"] == "population_count_quantized_bed"
    assert metadata["populations"] == ["popA", "popB"]
    assert metadata["population_columns"] == [
        {"column_number": 4, "name": "popA"},
        {"column_number": 5, "name": "popB"},
    ]
    assert metadata["population_sample_counts"] == {"popA": 2, "popB": 1}
    assert out.read_text().splitlines()[1:] == [
        "#chrom\tstart\tend\tpopA\tpopB",
        "chr1\t0\t20\t1\t1",
        "chr1\t20\t25\t0\t1",
    ]


def test_collapse_population_counts_rejects_unknown_sample_column(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\ts2\nchr1\t0\t10\t1\ts2\t1\n")

    with pytest.raises(ValueError, match="absent from samples.tsv"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_empty_multiinter(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("")

    with pytest.raises(ValueError, match="is empty"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_skips_blank_lines_before_header(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("\n\nchrom\tstart\tend\tnum\tlist\ts1\nchr1\t0\t10\t1\ts1\t1\n")
    out = tmp_path / "out.bed"

    collapse_population_counts(samples, multiinter, out)

    assert out.read_text().splitlines()[-1] == "chr1\t0\t10\t1"


def test_collapse_population_counts_rejects_malformed_header(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("not\tmultiinter\n")

    with pytest.raises(ValueError, match="must have a bedtools multiinter header"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_header_without_sample_columns(
    tmp_path: Path,
) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\n")

    with pytest.raises(ValueError, match="per-sample columns"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_wrong_indicator_count(tmp_path: Path) -> None:
    samples = [
        Sample("s1", "popA", tmp_path / "s1.bam"),
        Sample("s2", "popB", tmp_path / "s2.bam"),
    ]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\ts1\ts2\nchr1\t0\t10\t1\ts1\t1\n")

    with pytest.raises(ValueError, match="wrong number"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_invalid_interval(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\ts1\nchr1\t10\t10\t1\ts1\t1\n")

    with pytest.raises(ValueError, match="start >= end"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_short_rows(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\ts1\nchr1\t0\t10\t1\n")

    with pytest.raises(ValueError, match="at least five"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def test_collapse_population_counts_rejects_non_integer_indicators(tmp_path: Path) -> None:
    samples = [Sample("s1", "popA", tmp_path / "s1.bam")]
    multiinter = tmp_path / "multiinter.tsv"
    multiinter.write_text("chrom\tstart\tend\tnum\tlist\ts1\nchr1\t0\t10\t1\ts1\tyes\n")

    with pytest.raises(ValueError, match="invalid literal"):
        collapse_population_counts(samples, multiinter, tmp_path / "out.bed")


def _read_header_metadata(path: Path) -> dict[str, object]:
    first_line = path.read_text().splitlines()[0]
    prefix, encoded = first_line.split("\t", maxsplit=1)
    assert prefix == "#sprite_mask_metadata"
    metadata = json.loads(encoded)
    assert metadata["columns"][0:3] == ["chrom", "start", "end"]
    assert metadata["coordinate_system"] == "BED 0-based half-open"
    assert metadata["zero_count_intervals_omitted"] is True
    return metadata
