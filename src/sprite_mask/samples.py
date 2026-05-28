from __future__ import annotations

import csv
from pathlib import Path

from sprite_mask.models import Sample

ALIGNMENT_ALIASES = {"alignment", "bam_or_cram", "bam", "cram"}
SAMPLE_ID_ALIASES = {"sample_id", "sample", "id"}
POPULATION_ALIASES = {"population", "pop"}


def read_samples(path: Path) -> list[Sample]:
    """Read a sample metadata TSV with an optional header."""
    rows = _read_rows(path)
    if not rows:
        raise ValueError(f"{path} does not contain any sample rows")

    first_fields = [field.strip() for field in rows[0][1]]
    header_map = _alignment_header_map(first_fields)

    if header_map is None:
        data_rows = rows
        indices = {"sample_id": 0, "population": 1, "alignment": 2}
    else:
        data_rows = rows[1:]
        indices = header_map

    samples: list[Sample] = []
    for line_number, fields in data_rows:
        if len(fields) <= max(indices.values()):
            raise ValueError(f"{path}:{line_number} must have at least three tab-delimited columns")

        sample_id = fields[indices["sample_id"]].strip()
        population = fields[indices["population"]].strip()
        alignment = _resolve_alignment_path(fields[indices["alignment"]].strip(), path)
        samples.append(Sample(sample_id=sample_id, population=population, alignment=alignment))

    validate_samples(samples)
    return samples


def read_popfile(path: Path) -> list[Sample]:
    """Read a sample/population TSV with an optional header."""
    rows = _read_rows(path)
    if not rows:
        raise ValueError(f"{path} does not contain any sample rows")

    first_fields = [field.strip() for field in rows[0][1]]
    header_map = _population_header_map(first_fields)

    if header_map is None:
        data_rows = rows
        indices = {"sample_id": 0, "population": 1}
    else:
        data_rows = rows[1:]
        indices = header_map

    samples: list[Sample] = []
    for line_number, fields in data_rows:
        if len(fields) <= max(indices.values()):
            raise ValueError(f"{path}:{line_number} must have at least two tab-delimited columns")

        sample_id = fields[indices["sample_id"]].strip()
        population = fields[indices["population"]].strip()
        samples.append(Sample(sample_id=sample_id, population=population))

    validate_sample_populations(samples)
    return samples


def validate_samples(samples: list[Sample]) -> None:
    validate_sample_populations(samples)
    for sample in samples:
        if sample.alignment is None:
            raise ValueError(f"alignment for sample {sample.sample_id!r} is missing")
        if not sample.alignment.exists():
            raise ValueError(
                f"alignment for sample {sample.sample_id!r} does not exist: {sample.alignment}"
            )
        if sample.alignment.is_dir():
            raise ValueError(
                f"alignment for sample {sample.sample_id!r} is a directory: {sample.alignment}"
            )


def validate_sample_populations(samples: list[Sample]) -> None:
    if not samples:
        raise ValueError("at least one sample is required")

    seen: set[str] = set()
    for sample in samples:
        _validate_label(sample.sample_id, "sample_id")
        _validate_label(sample.population, "population")

        if sample.sample_id in seen:
            raise ValueError(f"duplicate sample_id: {sample.sample_id}")
        seen.add(sample.sample_id)


def populations_in_order(samples: list[Sample]) -> list[str]:
    populations: list[str] = []
    for sample in samples:
        if sample.population not in populations:
            populations.append(sample.population)
    return populations


def sample_population_map(samples: list[Sample]) -> dict[str, str]:
    return {sample.sample_id: sample.population for sample in samples}


def _read_rows(path: Path) -> list[tuple[int, list[str]]]:
    rows: list[tuple[int, list[str]]] = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for line_number, fields in enumerate(reader, start=1):
            if not fields:
                continue
            if len(fields) == 1 and not fields[0].strip():
                continue
            if fields[0].lstrip().startswith("#"):
                continue
            rows.append((line_number, fields))
    return rows


def _alignment_header_map(fields: list[str]) -> dict[str, int] | None:
    normalized = [field.strip().lower() for field in fields]
    sample_index = _first_index(normalized, SAMPLE_ID_ALIASES)
    population_index = _first_index(normalized, POPULATION_ALIASES)
    alignment_index = next(
        (index for index, name in enumerate(normalized) if name in ALIGNMENT_ALIASES),
        None,
    )

    has_known_column = (
        sample_index is not None or population_index is not None or alignment_index is not None
    )
    if not has_known_column:
        return None

    missing = []
    if sample_index is None:
        missing.append("sample_id")
    if population_index is None:
        missing.append("population")
    if alignment_index is None:
        missing.append("alignment")
    if missing:
        raise ValueError(f"samples header is missing required column(s): {', '.join(missing)}")

    assert alignment_index is not None
    assert sample_index is not None
    assert population_index is not None
    return {
        "sample_id": sample_index,
        "population": population_index,
        "alignment": alignment_index,
    }


def _population_header_map(fields: list[str]) -> dict[str, int] | None:
    normalized = [field.strip().lower() for field in fields]
    sample_index = _first_index(normalized, SAMPLE_ID_ALIASES)
    population_index = _first_index(normalized, POPULATION_ALIASES)

    if sample_index is None and population_index is None:
        return None

    missing = []
    if sample_index is None:
        missing.append("sample_id")
    if population_index is None:
        missing.append("population")
    if missing:
        raise ValueError(f"popfile header is missing required column(s): {', '.join(missing)}")

    assert sample_index is not None
    assert population_index is not None
    return {"sample_id": sample_index, "population": population_index}


def _first_index(values: list[str], aliases: set[str]) -> int | None:
    return next((index for index, value in enumerate(values) if value in aliases), None)


def _resolve_alignment_path(value: str, samples_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute() or path.exists():
        return path

    relative_to_samples = samples_path.parent / path
    if relative_to_samples.exists():
        return relative_to_samples

    return path


def _validate_label(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} values must be non-empty")
    if any(character.isspace() for character in value):
        raise ValueError(f"{field_name} values must not contain whitespace: {value!r}")
    if "/" in value or "\\" in value:
        raise ValueError(f"{field_name} values must not contain path separators: {value!r}")
