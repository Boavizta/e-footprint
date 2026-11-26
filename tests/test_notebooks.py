import unittest
import os

import pytest

from tests.optional_dependencies import needs_viz

pytest.importorskip("nbconvert")  # dev dependency, absent from a bare core install
from nbconvert import PythonExporter
from nbformat import read
from comprehension_harness.python.declare import planned_test
from efootprint.narrate import planned


def run_notebook(notebook_path):
    planned.remove("executable-modeling-documentation#presentations", "Replace notebook-to-Python text surgery with fresh-session execution of canonical cell selections and generated scripts.")
    notebook = read(notebook_path, as_version=4)
    exporter = PythonExporter()

    # Execute the notebook and collect the output
    python_code, _ = exporter.from_notebook_node(notebook)
    # exec can’t execute get_ipython so we need to remove the one call to this method that installs efootprint
    python_code = python_code.replace(
        """get_ipython().system('pip install "efootprint[viz]"')""", "# Removed for testing")

    exec(python_code)


root_dir = os.path.dirname(os.path.abspath(__file__))


class TestNotebooks(unittest.TestCase):
    # @planned.remove executable-modeling-documentation#presentations The planned published-sequence execution case below replaces this single-notebook case; no duplicate case is added.

    @needs_viz
    def test_tutorial(self):
        run_notebook(os.path.join(root_dir, "..", "tutorial.ipynb"))

    # Extends test_tutorial above across registered scenarios and guides, retitled; no case is added.
    @planned_test("executable-modeling-documentation#presentations: Published notebook and Python sequences execute in fresh sessions with fixed external responses, with and without plots [selected-example-runs]")
    def test_published_sequences_execute_from_fresh_sessions(self):
        pass
