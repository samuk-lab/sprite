from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from sprite_mask import __version__
from sprite_mask.models import Sample
from sprite_mask.samples import populations_in_order, sample_population_map


def collapse_population_counts(
    samples: list[Sample],
    multiinter_tsv: Path,
    output_bed: Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> Path:
    populations = populations_in_order(samples)
    sample_to_population = sample_population_map(samples)
    population_sample_counts = Counter(sample.population for sample in samples)

    output_bed.parent.mkdir(parents=True, exist_ok=True)
    with multiinter_tsv.open() as source, output_bed.open("w") as out:
        header = _read_multiinter_header(source, multiinter_tsv)
        sample_columns = header[5:]
        if not sample_columns:
            raise ValueError(f"{multiinter_tsv} header does not contain per-sample columns")

        unknown_samples = [
            sample for sample in sample_columns if sample not in sample_to_population
        ]
        if unknown_samples:
            raise ValueError(
                "multiinter sample column(s) are absent from samples.tsv: "
                + ", ".join(unknown_samples)
            )

        population_index = {population: index for index, population in enumerate(populations)}
        column_populations = [sample_to_population[sample] for sample in sample_columns]

        write_quantized_bed_header(
            out,
            columns=["chrom", "start", "end", *populations],
            metadata={
                "format": "population_count_quantized_bed",
                "populations": populations,
                "population_columns": [
                    {"column_number": index + 4, "name": population}
                    for index, population in enumerate(populations)
                ],
                "population_sample_counts": {
                    population: population_sample_counts[population]
                    for population in populations
                },
                **(metadata or {}),
            },
        )
        current: tuple[str, int, int, tuple[int, ...]] | None = None
        for fields in _iter_data_fields_after_header(source):
            chrom, start, end = _parse_interval(fields, multiinter_tsv)
            indicators = fields[5:]
            if len(indicators) != len(column_populations):
                raise ValueError(f"{multiinter_tsv} row has the wrong number of sample indicators")

            counts = [0] * len(populations)
            for indicator, population in zip(indicators, column_populations, strict=True):
                counts[population_index[population]] += int(indicator)
            count_tuple = tuple(counts)

            if (
                current
                and current[0] == chrom
                and current[2] == start
                and current[3] == count_tuple
            ):
                current = (current[0], current[1], end, current[3])
            else:
                _flush_population_count(out, current)
                current = (chrom, start, end, count_tuple)

        _flush_population_count(out, current)
    return output_bed


def write_quantized_bed_header(
    handle: TextIO,
    *,
    columns: list[str],
    metadata: dict[str, Any],
) -> None:
    full_metadata = {
        "sprite_mask_version": __version__,
        "columns": columns,
        "coordinate_system": "BED 0-based half-open",
        "zero_count_intervals_omitted": True,
        **metadata,
    }
    handle.write(
        "#sprite_mask_metadata\t"
        + json.dumps(full_metadata, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    handle.write("#" + "\t".join(columns) + "\n")


def _read_multiinter_header(source: TextIO, path: Path) -> list[str]:
    for line in source:
        fields = line.rstrip("\n").split("\t")
        if not fields or fields == [""]:
            continue
        if not _is_multiinter_header(fields):
            raise ValueError(f"{path} must have a bedtools multiinter header")
        return fields
    raise ValueError(f"{path} is empty")


def _iter_data_fields_after_header(source: TextIO) -> Iterator[list[str]]:
    for line in source:
        fields = line.rstrip("\n").split("\t")
        if fields and fields != [""]:
            yield fields


def _is_multiinter_header(fields: list[str]) -> bool:
    return len(fields) >= 5 and fields[:5] == ["chrom", "start", "end", "num", "list"]


def _parse_interval(fields: list[str], path: Path) -> tuple[str, int, int]:
    if len(fields) < 5:
        raise ValueError(f"{path} row must have at least five columns")
    chrom = fields[0]
    start = int(fields[1])
    end = int(fields[2])
    if start >= end:
        raise ValueError(f"{path} row has start >= end")
    return chrom, start, end


def _flush_population_count(
    handle: TextIO,
    current: tuple[str, int, int, tuple[int, ...]] | None,
) -> None:
    if current is None:
        return
    chrom, start, end, counts = current
    handle.write("\t".join([chrom, str(start), str(end), *[str(count) for count in counts]]) + "\n")
