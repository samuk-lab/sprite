from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    sample_id: str
    population: str
    alignment: Path | None = None


@dataclass(frozen=True)
class MosdepthOutputs:
    prefix: Path
    quantized_bed_gz: Path
    quantized_bed_index: Path
    summary: Path
    global_dist: Path
    stderr_log: Path
    command: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkflowOutputs:
    population_count_bed_gz: Path
    population_count_bed_index: Path
