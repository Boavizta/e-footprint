import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.calculus_graph import build_calculus_graph
from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR


class IntegrationTestSimpleEdgeSystemFromJson(IntegrationTestSimpleEdgeSystemBaseClass):
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

    def test_modeling_object_prints(self):
        self.run_test_modeling_object_prints()

    def test_all_objects_linked_to_system(self):
        self.run_test_all_objects_linked_to_system()

    def test_object_relationship_graph(self):
        self.run_test_object_relationship_graph()

    def test_calculation_graph(self):
        self.run_test_calculation_graph()

    def test_check_all_calculus_graph_dependencies_consistencies(self):
        self.run_test_check_all_calculus_graph_dependencies_consistencies()

    # SYSTEM <=> JSON

    def test_json_to_system(self):
        self.run_test_json_to_system(self.system)

    def test_system_to_json(self):
        self.run_test_system_to_json(self.system)

    # INPUTS VARIATION TESTING

    def test_variations_on_inputs(self):
        self.run_test_variations_on_inputs()

    def test_variations_on_inputs_after_json_to_system(self):
        self.run_test_variations_on_inputs_after_json_to_system()
        self.run_test_variations_on_inputs_after_json_to_system()

    def test_update_edge_usage_pattern_hourly_starts(self):
        self.run_test_update_edge_usage_pattern_hourly_starts()
        self.run_test_update_edge_usage_pattern_hourly_starts()

    def test_make_sure_updating_available_capacity_raises_error_if_necessary(self):
        self.run_test_make_sure_updating_available_capacity_raises_error_if_necessary()

    # OBJECT LINKS UPDATES TESTING

    def test_update_edge_device_in_edge_device_need_raises_error(self):
        self.run_test_update_edge_device_in_edge_device_need_raises_error()

    def test_update_edge_component_in_component_need_raises_error(self):
        self.run_test_update_edge_component_in_component_need_raises_error()

    def test_update_edge_process(self):
        self.run_test_update_edge_process()

    def test_update_edge_storage(self):
        self.run_test_update_edge_storage()

    def test_update_edge_computer(self):
        self.run_test_update_edge_computer()

    def test_add_edge_process(self):
        self.run_test_add_edge_process()

    def test_update_edge_processes(self):
        self.run_test_update_edge_processes()

    def test_update_edge_usage_journey(self):
        self.run_test_update_edge_usage_journey()

    def test_update_country_in_edge_usage_pattern(self):
        self.run_test_update_country_in_edge_usage_pattern()

    def test_add_edge_usage_pattern_to_system_and_reuse_existing_edge_process(self):
        self.run_test_add_edge_usage_pattern_to_system_and_reuse_existing_edge_process()

    def test_add_edge_usage_pattern_to_edge_usage_journey(self):
        self.run_test_add_edge_usage_pattern_to_edge_usage_journey()

    def test_add_edge_usage_journey_to_edge_computer(self):
        self.run_test_add_edge_usage_journey_to_edge_computer()

    def test_update_edge_usage_journey_after_json_to_system(self):
        self.run_test_update_edge_usage_journey_after_json_to_system()

    def test_update_edge_processes_after_json_to_system(self):
        self.run_test_update_edge_processes_after_json_to_system()

    # SIMULATION TESTING

    def test_simulation_input_change(self):
        self.run_test_simulation_input_change()

    def test_simulation_multiple_input_changes(self):
        self.run_test_simulation_multiple_input_changes()

    def test_simulation_add_new_edge_process(self):
        self.run_test_simulation_add_new_edge_process()

    def test_simulation_add_existing_edge_process(self):
        self.run_test_simulation_add_existing_edge_process()

    def test_semantic_units_in_calculated_attributes(self):
        self.run_test_semantic_units_in_calculated_attributes()
