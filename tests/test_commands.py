from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from sprite_mask.commands import run_pipeline


def test_run_pipeline_requires_at_least_two_commands(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least two commands"):
        run_pipeline([[sys.executable, "-c", "print('one')"]], tmp_path / "out.txt")


def test_run_pipeline_writes_last_command_stdout(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "out.txt"

    run_pipeline(
        [
            [sys.executable, "-c", "import sys; sys.stdout.write('a\\nb\\n')"],
            [
                sys.executable,
                "-c",
                "import sys; sys.stdout.write(sys.stdin.read().upper())",
            ],
        ],
        out,
    )

    assert out.read_text() == "A\nB\n"


def test_run_pipeline_raises_first_failing_command_with_stderr(tmp_path: Path) -> None:
    failing_command = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('nope\\n'); sys.exit(7)",
    ]

    with pytest.raises(subprocess.CalledProcessError) as error:
        run_pipeline(
            [
                failing_command,
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write(sys.stdin.read())",
                ],
            ],
            tmp_path / "out.txt",
        )

    assert error.value.returncode == 7
    assert error.value.cmd == failing_command
    assert error.value.stderr == "nope\n"
