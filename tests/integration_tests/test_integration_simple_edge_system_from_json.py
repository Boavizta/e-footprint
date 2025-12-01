import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.calculus_graph import build_calculus_graph
from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR, AutoTestMethodsMeta


class IntegrationTestSimpleEdgeSystemFromJson(IntegrationTestSimpleEdgeSystemBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for simple edge system loaded from JSON.

    Test methods are auto-generated from run_test_* methods in the base class.
    """
    @classmethod
    def setUpClass(cls):
        # Generate system from code first
        system, start_date = cls.generate_simple_edge_system()

        # Save to JSON and reload
        cls.system_json_filepath = os.path.join(
            INTEGRATION_TEST_DIR, "simple_edge_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        _, flat_obj_dict = json_to_system(system_dict)

        # Get the reloaded system and use common setup
        reloaded_system = flat_obj_dict[system.id]
        cls._setup_from_system(reloaded_system, start_date)

    def test_system_calculation_graph_right_after_json_to_system(self):
        with open(self.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)
        system = flat_obj_dict[self.system.id]
        self.assertFalse("None" in system.total_footprint.explain())
        graph = build_calculus_graph(system.total_footprint)
        graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_edge_calculation_graph.html"),
            notebook=False)
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_edge_calculation_graph.html"), "r") as f:
            content = f.read()
        self.assertGreater(len(content), 30000)
