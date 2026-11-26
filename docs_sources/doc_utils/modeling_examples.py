"""Planned conversion and explicit execution of canonical modeling examples."""
from pathlib import Path

from efootprint.narrate import planned


def read_example_notebook(source_path: Path):
    planned("executable-modeling-documentation#source-format:read-percent", "Read percent cells and their metadata with development-only Jupytext without importing the scenario.")
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")


def select_example_cells(notebook, *, without_plots: bool = False, baseline_only: bool = False,
                         section_ids: tuple[str, ...] = ()):
    planned("executable-modeling-documentation#source-format:ordered-selection", "Select source-order cells for full, without-plots, baseline or registered guide presentations.")
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")


def write_example_presentations(example, *, output_dir: Path, check: bool = False):
    planned("executable-modeling-documentation#presentations:convert", "Use `read_example_notebook` and `select_example_cells` to derive cleared notebooks, runnable Python and output-free Markdown without execution.")
    raise NotImplementedError("planned: executable-modeling-documentation#presentations")


def build_example_documentation(example, *, output_dir: Path):
    planned("executable-modeling-documentation#presentations:execute-docs", "Use `read_example_notebook` and `select_example_cells` to execute fresh notebooks and retain their outputs and resources in generated documentation.")
    raise NotImplementedError("planned: executable-modeling-documentation#presentations")


def regenerate_example(example, *, output_path: Path):
    planned("executable-modeling-documentation#baseline-generation:regenerate", "Use `read_example_notebook` and `select_example_cells` to execute construction with deterministic ids in a fresh kernel and save inputs-only JSON.")
    raise NotImplementedError("planned: executable-modeling-documentation#baseline-generation")


def main():
    planned("executable-modeling-documentation#source-format:command", "Dispatch explicit convert, build-docs and regenerate commands to `write_example_presentations`, `build_example_documentation` and `regenerate_example`.")
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")

