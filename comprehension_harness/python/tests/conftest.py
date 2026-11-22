"""Shared by the tests of the comprehension tools' Python stack: its commands run as the tools run them."""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
REFERENCE_CALLS = ROOT / "comprehension_harness/python/narrate.py"


@pytest.fixture
def project(tmp_path):
    """Writes a small project, a file a path, and returns its root."""
    def write(files: dict[str, str]) -> Path:
        for file, text in files.items():
            (tmp_path / file).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / file).write_text(textwrap.dedent(text).lstrip("\n"))
        return tmp_path

    return write


def run_stack(module: str, *arguments, stdin: str | None = None) -> subprocess.CompletedProcess:
    command = [sys.executable, "-m", f"comprehension_harness.python.{module}", *map(str, arguments)]
    return subprocess.run(command, input=stdin, cwd=ROOT, capture_output=True, text=True)


def source_index(root: Path, source="app/", tests="checks/", calls="narrate", declare="declare"):
    """The index of a project whose source is one folder and whose test files are `<tests>test_*.py`."""
    settings = {"source": {"app": [source]}, "tests": {"roots": [tests], "files": rf"^{tests}test_[^/]*\.py$"},
                "stack": {"calls": calls}}
    # The configuration is written beside the project, never in it: a project can be a fixture others read.
    with tempfile.TemporaryDirectory() as folder:
        config = Path(folder) / "comprehension.config.json"
        config.write_text(json.dumps(settings))
        return run_stack("source_index", "--root", root, "--config", config, "--declare", declare)
