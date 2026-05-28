from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, TextIO

import pytest

from sprite_mask.config import AlignmentRunConfig
from sprite_mask.models import Sample
from sprite_mask.mosdepth import (
    build_mosdepth_command,
    mosdepth_outputs_for_prefix,
    run_mosdepth,
)


def test_run_mosdepth_sets_quantize_env_and_returns_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = Sample("s1", "popA", tmp_path / "s1.bam")
    config = AlignmentRunConfig(
        samples_path=tmp_path / "samples.tsv",
        threshold=10,
        out_dir=tmp_path / "out",
        work_dir=tmp_path / "work",
    )
    captured: dict[str, Any] = {}

    def fake_run(
        command: list[str],
        *,
        check: bool,
        env: dict[str, str],
        stdout: object,
        stderr: TextIO,
    ) -> subprocess.CompletedProcess[str]:
        captured.update(
            {
                "command": command,
                "check": check,
                "env": env,
                "stdout": stdout,
            }
        )
        stderr.write("mosdepth log\n")
        outputs = mosdepth_outputs_for_prefix(config.resolved_work_dir / "s1.d10")
        outputs.quantized_bed_gz.write_text("quantized")
        outputs.summary.write_text("summary")
        outputs.global_dist.write_text("dist")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("sprite_mask.mosdepth.subprocess.run", fake_run)

    outputs = run_mosdepth(sample, config)

    assert outputs.prefix == tmp_path / "work" / "s1.d10"
    assert outputs.command == tuple(captured["command"])
    assert captured["check"] is True
    assert captured["stdout"] is subprocess.DEVNULL
    assert captured["env"]["MOSDEPTH_Q0"] == "FAIL"
    assert captured["env"]["MOSDEPTH_Q1"] == "PASS"
    assert outputs.stderr_log.read_text() == "mosdepth log\n"


def test_run_mosdepth_rejects_missing_expected_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = Sample("s1", "popA", tmp_path / "s1.bam")
    config = AlignmentRunConfig(
        samples_path=tmp_path / "samples.tsv",
        threshold=10,
        out_dir=tmp_path / "out",
        work_dir=tmp_path / "work",
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["mosdepth"], 0)

    monkeypatch.setattr("sprite_mask.mosdepth.subprocess.run", fake_run)

    with pytest.raises(FileNotFoundError, match="quantized.bed.gz"):
        run_mosdepth(sample, config)


def test_build_mosdepth_command_requires_alignment(tmp_path: Path) -> None:
    config = AlignmentRunConfig(
        samples_path=tmp_path / "samples.tsv",
        threshold=10,
        out_dir=tmp_path / "out",
    )

    with pytest.raises(ValueError, match="alignment"):
        build_mosdepth_command(Sample("s1", "popA"), config, tmp_path / "s1.d10")


def test_mosdepth_outputs_for_prefix_uses_expected_suffixes(tmp_path: Path) -> None:
    outputs = mosdepth_outputs_for_prefix(tmp_path / "s1.d10")

    assert outputs.quantized_bed_gz == tmp_path / "s1.d10.quantized.bed.gz"
    assert outputs.quantized_bed_index == tmp_path / "s1.d10.quantized.bed.gz.csi"
    assert outputs.summary == tmp_path / "s1.d10.mosdepth.summary.txt"
    assert outputs.global_dist == tmp_path / "s1.d10.mosdepth.global.dist.txt"
    assert outputs.stderr_log == tmp_path / "s1.d10.mosdepth.stderr.log"
