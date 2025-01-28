import unittest
from nbconvert import PythonExporter
from nbformat import read
import os


def run_notebook(notebook_path):
    notebook = read(notebook_path, as_version=4)
    exporter = PythonExporter()

    # Execute the notebook and collect the output
    python_code, _ = exporter.from_notebook_node(notebook)
    # exec can’t execute get_ipython so we need to remove the one call to this method that installs efootprint
    python_code = python_code.replace("get_ipython().system('pip install efootprint')", "# Removed for testing")

    exec(python_code)


root_dir = os.path.dirname(os.path.abspath(__file__))


class TestNotebooks(unittest.TestCase):
    def test_tutorial(self):
        run_notebook(os.path.join(root_dir, "..", "tutorial.ipynb"))
