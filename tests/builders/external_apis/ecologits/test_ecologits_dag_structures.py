import unittest

from ecologits.impacts.llm import dag as llm_dag
from ecologits.impacts.video import dag as video_dag

from efootprint.builders.external_apis.ecologits.ecologits_utils import (
    ECOLOGITS_LLM_DEPENDENCY_GRAPH, ECOLOGITS_VIDEO_DEPENDENCY_GRAPH, get_formula)
from efootprint.builders.external_apis.ecologits.ecologits_external_api import ecologits_calculated_attributes
from efootprint.builders.external_apis.ecologits.ecologits_video_external_api import (
    ecologits_video_calculated_attributes)


class TestEcoLogitsDagStructures(unittest.TestCase):
    def test_get_formula_returns_non_empty_string_for_every_llm_calculated_attribute(self):
        for task_name in ecologits_calculated_attributes:
            formula = get_formula(llm_dag, task_name)
            self.assertIsInstance(formula, str)
            self.assertTrue(formula.strip(), f"Empty formula for LLM task `{task_name}`")
            self.assertIn(task_name, formula)

    def test_get_formula_returns_non_empty_string_for_every_video_calculated_attribute(self):
        for task_name in ecologits_video_calculated_attributes:
            formula = get_formula(video_dag, task_name)
            self.assertIsInstance(formula, str)
            self.assertTrue(formula.strip(), f"Empty formula for video task `{task_name}`")
            self.assertIn(task_name, formula)

    def test_llm_and_video_dependency_graphs_are_distinct(self):
        # The helper must key by (dag, task_name); LLM-only and video-only nodes must not overlap.
        llm_only = set(ECOLOGITS_LLM_DEPENDENCY_GRAPH) - set(ECOLOGITS_VIDEO_DEPENDENCY_GRAPH)
        video_only = set(ECOLOGITS_VIDEO_DEPENDENCY_GRAPH) - set(ECOLOGITS_LLM_DEPENDENCY_GRAPH)
        self.assertIn("gpu_energy", llm_only)
        self.assertIn("server_accelerator_energy", video_only)


if __name__ == "__main__":
    unittest.main()
