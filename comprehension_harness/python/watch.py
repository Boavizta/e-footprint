"""Keeps the narrative tests running: runs the test files again at each save, and never exits on its own.

    python3 -m comprehension_harness.python.watch tests/narratives/test_….py …

pytest has no watch mode, and the local app (``npm run comprehension``) stops when this command exits. It runs
``commands.tests`` of ``comprehension.config.json`` with the files it was given, then again each time a file of
the source folders or of the test folders is saved, created or deleted. A run that fails is waited out like
any other: the next save runs the files again. Ctrl-C stops the run in progress and the loop.

A save is seen by polling modification times, twice a second: no dependency, and the folders are small.

Standard library only.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

CONFIG_FILE = "comprehension.config.json"
ROOT = Path(__file__).resolve().parents[2]
POLL_SECONDS = 0.5
SKIPPED_FOLDERS = ("__pycache__", "node_modules")
SKIPPED_SUFFIXES = (".pyc", ".pyo")


def refuse(what: str):
    sys.exit(f"comprehension-watch: {what}")


def watched() -> tuple[list[str], list[str]]:
    """The command that runs test files once, and the folders whose saves run them again."""
    try:
        settings = json.loads((ROOT / CONFIG_FILE).read_text())
        command = settings["commands"]["tests"]
        folders = [*settings["source"]["app"], *settings["tests"]["roots"]]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        refuse(f'{CONFIG_FILE} — "commands.tests", "source.app" and "tests.roots" are read from it: {error!r}')
    if not command or not all(isinstance(part, str) for part in [*command, *folders]):
        refuse(f'{CONFIG_FILE} — "commands.tests", "source.app" and "tests.roots" are lists of strings')
    return command, folders


def snapshot(folders: list[str]) -> dict[str, int]:
    """Every file under the folders with its modification time."""
    seen = {}
    for folder in folders:
        for directory, names, files in os.walk(ROOT / folder):
            names[:] = [name for name in names if not name.startswith(".") and name not in SKIPPED_FOLDERS]
            for file in files:
                if file.endswith(SKIPPED_SUFFIXES):
                    continue
                path = os.path.join(directory, file)
                try:
                    seen[path] = os.stat(path).st_mtime_ns
                except FileNotFoundError:  # Deleted between the listing and the reading: gone, as the next pass says.
                    pass
    return seen


def changed(before: dict[str, int], after: dict[str, int]) -> list[str]:
    moved = (path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    return sorted(os.path.relpath(path, ROOT) for path in moved)


def main() -> int:
    files = sys.argv[1:]
    if not files:
        refuse("no test file to keep running: the narrative test files follow the command")
    command, folders = watched()
    running: subprocess.Popen | None = None

    def stop(*_):
        if running is not None and running.poll() is None:
            running.send_signal(signal.SIGINT)
            running.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    reason = "start"
    while True:
        # What is on disk when a run starts is what that run reads: a save during it is seen after it.
        before = snapshot(folders)
        print(f"[watch] {reason} — {' '.join([*command, *files])}", flush=True)
        try:
            running = subprocess.Popen([*command, *files], cwd=ROOT)
        except OSError as error:
            refuse(f"`{' '.join(command)}` (\"commands.tests\" of {CONFIG_FILE}) cannot be started: {error}")
        status = running.wait()
        print(f"[watch] the tests {'pass' if status == 0 else f'fail (exit {status})'}; waiting for a save", flush=True)
        while not (moved := changed(before, snapshot(folders))):
            time.sleep(POLL_SECONDS)
        reason = f"{moved[0]} changed" + (f" and {len(moved) - 1} more" if len(moved) > 1 else "")


if __name__ == "__main__":
    sys.exit(main())
