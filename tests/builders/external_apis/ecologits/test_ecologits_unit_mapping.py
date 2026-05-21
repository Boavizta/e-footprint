import unittest

from efootprint.builders.external_apis.ecologits.ecologits_utils import (
    ECOLOGITS_LLM_DEPENDENCY_GRAPH, ECOLOGITS_VIDEO_DEPENDENCY_GRAPH)
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING


_WCF_ONLY = ("request_usage_wcf", "if_electricity_mix_wue", "datacenter_wue")
_NON_GWP_SUFFIXES = ("_wue", "_pe", "_adpe")


def _gwp_relevant(name: str) -> bool:
    if name in _WCF_ONLY:
        return False
    return not any(name.endswith(suffix) for suffix in _NON_GWP_SUFFIXES)


class TestEcologitsUnitMapping(unittest.TestCase):
    def test_every_gwp_relevant_llm_dag_output_has_unit_mapping(self):
        missing = [task for task in ECOLOGITS_LLM_DEPENDENCY_GRAPH
                   if _gwp_relevant(task) and task not in ECOLOGITS_UNIT_MAPPING]
        self.assertEqual([], missing, f"LLM DAG outputs missing unit mappings: {missing}")

    def test_every_gwp_relevant_video_dag_output_has_unit_mapping(self):
        missing = [task for task in ECOLOGITS_VIDEO_DEPENDENCY_GRAPH
                   if _gwp_relevant(task) and task not in ECOLOGITS_UNIT_MAPPING]
        self.assertEqual([], missing, f"Video DAG outputs missing unit mappings: {missing}")

    def test_every_video_dag_ancestor_of_a_gwp_relevant_output_has_unit_mapping(self):
        # update_ecologits_video_calculated_attribute filters ancestors to those with a unit mapping,
        # but missing a load-bearing ancestor's unit would silently drop it from explainability ancestors.
        missing = set()
        for task, ancestors in ECOLOGITS_VIDEO_DEPENDENCY_GRAPH.items():
            if not _gwp_relevant(task):
                continue
            for ancestor in ancestors:
                if _gwp_relevant(ancestor) and ancestor not in ECOLOGITS_UNIT_MAPPING:
                    missing.add(ancestor)
        self.assertEqual(set(), missing, f"Video DAG GWP-relevant ancestors missing unit mappings: {missing}")


if __name__ == "__main__":
    unittest.main()
