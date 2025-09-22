import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.utils.calculus_graph import build_calculus_graph
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


class IntegrationTestSimpleSystemFromJson(IntegrationTestSimpleSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        (system, storage, server, job_1, uj_step_1, job_2, uj_step_2, uj, network,
         start_date, usage_pattern) = cls.generate_simple_system()

        cls.system_json_filepath = "system_with_calculated_attributes.json"
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        cls.system, cls.storage, cls.server, cls.job_1, cls.uj_step_1, cls.job_2, cls.uj_step_2, \
            cls.uj, cls.start_date, cls.network, cls.usage_pattern = \
            flat_obj_dict[system.id], flat_obj_dict[storage.id], flat_obj_dict[server.id], \
            flat_obj_dict[job_1.id], flat_obj_dict[uj_step_1.id], flat_obj_dict[job_2.id], \
            flat_obj_dict[uj_step_2.id], flat_obj_dict[uj.id], start_date, flat_obj_dict[network.id], \
            flat_obj_dict[usage_pattern.id]

        cls.initialize_footprints(
            cls.system, cls.storage, cls.server, cls.usage_pattern, cls.network)

        cls.ref_json_filename = "simple_system"

    def test_system_calculation_graph_right_after_json_to_system(self):
        with open(self.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)
        system = flat_obj_dict[self.system.id]
        self.assertFalse("None" in system.total_footprint.explain())
        graph = build_calculus_graph(system.total_footprint)
        graph.show(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_calculation_graph.html"), notebook=False)
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "full_calculation_graph.html"), "r") as f:
            content = f.read()
        self.assertGreater(len(content), 50000)

    def test_modeling_object_prints(self):
        self.run_test_modeling_object_prints()

    def test_all_objects_linked_to_system(self):
        self.run_test_all_objects_linked_to_system()

    def test_calculation_graph(self):
        self.run_test_calculation_graph()

    def test_object_relationship_graph(self):
        self.run_test_object_relationship_graph()

    # SYSTEM <=> JSON

    def test_system_to_json(self):
        self.run_test_system_to_json(self.system)

    def test_json_to_system(self):
        self.run_test_json_to_system(self.system)

    # INPUT VARIATION TESTING

    def test_generate_new_system_with_json_saving_halfway_keeps_calculation_graph_intact(self):
        self.run_test_generate_new_system_with_json_saving_halfway_keeps_calculation_graph_intact()

    def test_variations_on_inputs(self):
        self.run_test_variations_on_inputs()

    def test_variations_on_inputs_after_json_to_system(self):
        self.run_test_variations_on_inputs_after_json_to_system()

    def test_set_uj_duration_to_0_and_back_to_previous_value(self):
        self.run_test_set_uj_duration_to_0_and_back_to_previous_value()

    def test_hourly_usage_journey_starts_update(self):
        self.run_test_hourly_usage_journey_starts_update()

    def test_update_footprint_job_datastored_from_positive_value_to_negative_value(self):
        self.run_test_update_footprint_job_datastored_from_positive_value_to_negative_value()

    def test_storage_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        self.run_test_storage_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty()

    def test_on_premise_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        self.run_test_on_premise_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty()

    # OBJECT LINKS UPDATES TESTING

    def test_uj_step_update(self):
        self.run_test_uj_step_update()

    def test_device_pop_update(self):
        self.run_test_device_pop_update()

    def test_update_server(self):
        self.run_test_update_server()

    def test_update_storage(self):
        self.run_test_update_storage()

    def test_update_jobs(self):
        self.run_test_update_jobs()

    def test_update_uj_steps(self):
        self.run_test_update_uj_steps()

    def test_update_usage_journey(self):
        self.run_test_update_usage_journey()

    def test_update_country_in_usage_pattern(self):
        self.run_test_update_country_in_usage_pattern()

    def test_update_network(self):
        self.run_test_update_network()

    def test_add_uj_step_without_job(self):
        self.run_test_add_uj_step_without_job()

    def test_add_usage_pattern(self):
        self.run_test_add_usage_pattern()

    def test_change_network_and_hourly_usage_journey_starts_simultaneously_recomputes_in_right_order(self):
        self.run_test_change_network_and_hourly_usage_journey_starts_simultaneously_recomputes_in_right_order()

    def test_delete_job(self):
        self.run_test_delete_job()

    # SIMULATION TESTING

    def test_simulation_input_change(self):
        self.run_test_simulation_input_change()

    def test_simulation_multiple_input_changes(self):
        self.run_test_simulation_multiple_input_changes()

    def test_simulation_add_new_object(self):
        self.run_test_simulation_add_new_object()

    def test_simulation_add_existing_object(self):
        self.run_test_simulation_add_existing_object()

    def test_simulation_add_multiple_objects(self):
        self.run_test_simulation_add_multiple_objects()

    def test_simulation_add_objects_and_make_input_changes(self):
        self.run_test_simulation_add_objects_and_make_input_changes()
