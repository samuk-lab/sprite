from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from wisp_mask.bedio import (
    count_bed_sites,
    extract_merged_pass_intervals,
    extract_pass_intervals,
    iter_bed3,
    normalize_targets_bed,
    write_bed3_from_intervals,
)


def test_normalize_targets_bed_writes_first_three_columns(tmp_path: Path) -> None:
    targets = tmp_path / "targets.bed"
    targets.write_text(
        "# comment\n"
        "\n"
        "chr1\t10\t20\tname\n"
        "chr1 30 35 other\n"
    )
    out = tmp_path / "targets.3col.bed"

    normalize_targets_bed(targets, out)

    assert out.read_text() == "chr1\t10\t20\nchr1\t30\t35\n"


def test_normalize_targets_bed_rejects_invalid_coordinates(tmp_path: Path) -> None:
    targets = tmp_path / "targets.bed"
    targets.write_text("chr1\t20\t20\n")

    with pytest.raises(ValueError, match="start < end"):
        normalize_targets_bed(targets, tmp_path / "out.bed")


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("chr1\tstart\t20\n", "non-integer"),
        ("chr1\t-1\t20\n", "negative"),
        ("chr1\t1\n", "at least three"),
    ],
)
def test_normalize_targets_bed_rejects_malformed_rows(
    tmp_path: Path,
    line: str,
    message: str,
) -> None:
    targets = tmp_path / "targets.bed"
    targets.write_text(line)

    with pytest.raises(ValueError, match=message):
        normalize_targets_bed(targets, tmp_path / "out.bed")


def test_extract_pass_intervals_streams_quantized_bed(tmp_path: Path) -> None:
    quantized = tmp_path / "sample.quantized.bed.gz"
    with gzip.open(quantized, "wt") as handle:
        handle.write("# comment\n")
        handle.write("\n")
        handle.write("chr1\t0\t10\tFAIL\n")
        handle.write("chr1\t10\t25\tPASS\n")
        handle.write("chr2\t1\t5\tPASS\n")
    out = tmp_path / "pass.bed"

    extract_pass_intervals(quantized, out)

    assert out.read_text() == "chr1\t10\t25\nchr2\t1\t5\n"


def test_extract_pass_intervals_supports_custom_pass_label(tmp_path: Path) -> None:
    quantized = tmp_path / "sample.quantized.bed.gz"
    with gzip.open(quantized, "wt") as handle:
        handle.write("chr1\t0\t10\tLOW\n")
        handle.write("chr1\t10\t20\tHIGH\n")
    out = tmp_path / "pass.bed"

    extract_pass_intervals(quantized, out, pass_label="HIGH")

    assert out.read_text() == "chr1\t10\t20\n"


def test_extract_pass_intervals_rejects_short_rows(tmp_path: Path) -> None:
    quantized = tmp_path / "sample.quantized.bed.gz"
    with gzip.open(quantized, "wt") as handle:
        handle.write("chr1\t0\t10\n")

    with pytest.raises(ValueError, match="at least four columns"):
        extract_pass_intervals(quantized, tmp_path / "pass.bed")


def test_extract_merged_pass_intervals_combines_adjacent_pass_blocks(tmp_path: Path) -> None:
    quantized = tmp_path / "sample.quantized.bed.gz"
    with gzip.open(quantized, "wt") as handle:
        handle.write("# comment\n")
        handle.write("\n")
        handle.write("chr1\t0\t10\tFAIL\n")
        handle.write("chr1\t10\t25\tPASS\n")
        handle.write("chr1\t25\t30\tPASS\n")
        handle.write("chr1\t30\t35\tFAIL\n")
        handle.write("chr1\t35\t40\tPASS\n")
        handle.write("chr2\t1\t5\tPASS\n")
    out = tmp_path / "pass.bed"

    extract_merged_pass_intervals(quantized, out)

    assert out.read_text() == "chr1\t10\t30\nchr1\t35\t40\nchr2\t1\t5\n"


def test_extract_merged_pass_intervals_rejects_short_rows(tmp_path: Path) -> None:
    quantized = tmp_path / "sample.quantized.bed.gz"
    with gzip.open(quantized, "wt") as handle:
        handle.write("chr1\t0\t10\n")

    with pytest.raises(ValueError, match="at least four columns"):
        extract_merged_pass_intervals(quantized, tmp_path / "pass.bed")


def test_count_bed_sites(tmp_path: Path) -> None:
    bed = tmp_path / "pass.bed"
    bed.write_text("chr1\t10\t25\nchr2\t1\t5\n")

    assert count_bed_sites(bed) == 19


def test_iter_bed3_skips_headers_comments_and_blank_lines(tmp_path: Path) -> None:
    bed = tmp_path / "regions.bed"
    bed.write_text(
        "# comment\n"
        "\n"
        "chrom\tstart\tend\tname\n"
        "chr1\t0\t10\ta\n"
        "chr2 5 8 b\n"
    )

    assert list(iter_bed3(bed)) == [("chr1", 0, 10), ("chr2", 5, 8)]


def test_write_bed3_from_intervals_writes_valid_intervals(tmp_path: Path) -> None:
    out = tmp_path / "regions.bed"

    write_bed3_from_intervals([("chr1", 0, 10), ("chr2", 5, 8)], out)

    assert out.read_text() == "chr1\t0\t10\nchr2\t5\t8\n"


def test_write_bed3_from_intervals_rejects_empty_or_negative_width(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid interval"):
        write_bed3_from_intervals([("chr1", 10, 10)], tmp_path / "regions.bed")
