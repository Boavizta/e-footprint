import unittest
import tomllib
from pathlib import Path

import efootprint
from efootprint.logger import logger


def get_version_from_pyproject():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    logger.info(f"Reading version from {pyproject_path}")
    if pyproject_path.exists():
        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)
            return pyproject["tool"]["poetry"]["version"]
    raise FileNotFoundError("pyproject.toml not found")


class TestVersion(unittest.TestCase):
    def test_version_is_up_to_date(self):
        self.assertEqual(get_version_from_pyproject(), efootprint.__version__)
