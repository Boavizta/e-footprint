"""Planned conversion and explicit execution of canonical modeling examples."""
from pathlib import Path

from efootprint.narrate import narrate, planned


def read_example_notebook(source_path: Path):
    planned("executable-modeling-documentation#source-format:read-percent", "Read py:percent cells and JSON-form metadata with development-only Jupytext without importing the scenario.")
    narrate.planned("example-publication:read", "The scenario source supplies prose, code cells and presentation tags without importing or executing its modeling code.", changes=("executable-modeling-documentation#source-format:read-percent",))
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")


def select_example_cells(notebook, *, without_plots: bool = False, baseline_only: bool = False,
                         section_ids: tuple[str, ...] = ()):
    planned("executable-modeling-documentation#source-format:ordered-selection", "Select source-order cells using plot, notebook-setup, baseline-end and section:<name> tags; baseline-end marks the cell binding system.")
    narrate.planned("example-publication:select", "Selection preserves source order: plot-dependent prose follows its plot cells, and packaged-model generation stops at the initial construction boundary.", changes=("executable-modeling-documentation#source-format:ordered-selection",))
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")


def write_example_presentations(example, *, output_dir: Path, check: bool = False):
    planned("executable-modeling-documentation#presentations:convert", "Use `read_example_notebook` and `select_example_cells` to write cleared notebooks and output-free Markdown/Python; convert --check compares committed artifacts without execution.")
    narrate.planned("example-publication:convert", "Conversion derives cleared notebooks and complete readings from the same source without running the scenario or contacting external services.", changes=("executable-modeling-documentation#presentations:convert",))
    raise NotImplementedError("planned: executable-modeling-documentation#presentations")


def build_example_documentation(example, *, output_dir: Path):
    planned("executable-modeling-documentation#presentations:execute-docs", "Use `read_example_notebook` and `select_example_cells` to execute fresh notebooks and retain their outputs and resources in generated documentation.")
    narrate.planned("example-publication:publish", "Documentation execution publishes numerical outputs, charts and their resources from a fresh session; its results never overwrite the packaged model.", changes=("executable-modeling-documentation#presentations:execute-docs",))
    raise NotImplementedError("planned: executable-modeling-documentation#presentations")


def regenerate_example(example, *, output_path: Path):
    planned("executable-modeling-documentation#baseline-generation:regenerate", "Use `read_example_notebook` and `select_example_cells` to execute construction with deterministic ids in a fresh kernel and save inputs-only JSON.")
    narrate.planned("example-publication:baseline", "Explicit regeneration saves the initial model with stable ids in an isolated session, leaving later experiments and visualizations outside the packaged example.", changes=("executable-modeling-documentation#baseline-generation:regenerate",))
    raise NotImplementedError("planned: executable-modeling-documentation#baseline-generation")


def main():
    planned("executable-modeling-documentation#source-format:command", "Expose python -m docs_sources.doc_utils.modeling_examples with convert, build-docs and regenerate, dispatching to `write_example_presentations`, `build_example_documentation` and `regenerate_example`.")
    raise NotImplementedError("planned: executable-modeling-documentation#source-format")

