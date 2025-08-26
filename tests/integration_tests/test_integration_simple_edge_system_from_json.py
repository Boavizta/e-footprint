import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.calculus_graph import build_calculus_graph
from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass


class IntegrationTestSimpleEdgeSystemFromJson(IntegrationTestSimpleEdgeSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        (system, edge_storage, edge_device, edge_process, edge_usage_journey,
         edge_usage_pattern, start_date) = cls.generate_simple_edge_system()

        cls.system_json_filepath = "simple_edge_system_with_calculated_attributes.json"
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        (cls.system, cls.edge_storage, cls.edge_device, cls.edge_process, cls.edge_usage_journey,
         cls.edge_usage_pattern, cls.start_date) = \
             (flat_obj_dict[system.id], flat_obj_dict[edge_storage.id], flat_obj_dict[edge_device.id],
              flat_obj_dict[edge_process.id], flat_obj_dict[edge_usage_journey.id],
              flat_obj_dict[edge_usage_pattern.id], start_date)

        cls.initialize_footprints(cls.system, cls.edge_storage, cls.edge_device)

        cls.ref_json_filename = "simple_edge_system"

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

    # OBJECT LINKS UPDATES TESTING

    def test_update_edge_process(self):
        self.run_test_update_edge_process()

    def test_update_edge_storage(self):
        self.run_test_update_edge_storage()

    def test_update_edge_device(self):
        self.run_test_update_edge_device()

    def test_add_edge_process(self):
        self.run_test_add_edge_process()

    def test_update_edge_processes(self):
        self.run_test_update_edge_processes()

    def test_update_edge_usage_journey(self):
        self.run_test_update_edge_usage_journey()

    def test_update_country_in_edge_usage_pattern(self):
        self.run_test_update_country_in_edge_usage_pattern()

    def test_add_edge_usage_pattern(self):
        self.run_test_add_edge_usage_pattern()

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