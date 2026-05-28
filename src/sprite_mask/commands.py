from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


def run_pipeline(commands: Sequence[Sequence[str]], out_path: Path) -> None:
    if len(commands) < 2:
        raise ValueError("pipeline requires at least two commands")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    processes: list[subprocess.Popen[bytes]] = []

    with out_path.open("wb") as out_handle:
        previous_stdout = None
        for index, command in enumerate(commands):
            is_last = index == len(commands) - 1
            process = subprocess.Popen(
                list(command),
                stdin=previous_stdout,
                stdout=out_handle if is_last else subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if previous_stdout is not None:
                previous_stdout.close()
            previous_stdout = process.stdout
            processes.append(process)

        stderr_by_command: list[bytes] = []
        for process in processes:
            _stdout, stderr = process.communicate()
            stderr_by_command.append(stderr)

    failures = [
        (commands[index], process.returncode, stderr_by_command[index])
        for index, process in enumerate(processes)
        if process.returncode != 0
    ]
    if failures:
        command, returncode, stderr = failures[0]
        raise subprocess.CalledProcessError(returncode, list(command), stderr=stderr.decode())
