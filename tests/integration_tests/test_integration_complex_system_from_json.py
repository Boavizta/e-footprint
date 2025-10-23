import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR
from tests.integration_tests.integration_complex_system_base_class import IntegrationTestComplexSystemBaseClass


class IntegrationTestComplexSystemFromJson(IntegrationTestComplexSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        system, storage_1, storage_2, storage_3, server1, server2, server3, \
            server1_job1, server1_job2, server1_job3, server2_job, server3_job, \
            uj_step_1, uj_step_2, uj_step_3, uj_step_4, \
            start_date, usage_pattern1, usage_pattern2, uj, network1, network2, \
            edge_storage, edge_computer, edge_process, edge_function, edge_usage_journey, edge_usage_pattern = \
            cls.generate_complex_system()

        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "complex_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        # Load the system from the JSON file
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        (cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2, cls.server3, \
            cls.server1_job1, cls.server1_job2, cls.server1_job3, cls.server2_job, cls.server3_job, \
            cls.uj_step_1, cls.uj_step_2, cls.uj_step_3, cls.uj_step_4, \
            cls.start_date, cls.usage_pattern1, cls.usage_pattern2, cls.uj, cls.network1, cls.network2, \
            cls.edge_storage, cls.edge_computer, cls.edge_process, cls.edge_function,
            cls.edge_usage_journey, cls.edge_usage_pattern) = \
        flat_obj_dict[system.id], flat_obj_dict[storage_1.id], flat_obj_dict[storage_2.id], flat_obj_dict[storage_3.id], \
        flat_obj_dict[server1.id], flat_obj_dict[server2.id], flat_obj_dict[server3.id], \
        flat_obj_dict[server1_job1.id], flat_obj_dict[server1_job2.id], flat_obj_dict[server1_job3.id], \
        flat_obj_dict[server2_job.id], flat_obj_dict[server3_job.id], \
        flat_obj_dict[uj_step_1.id], flat_obj_dict[uj_step_2.id], flat_obj_dict[uj_step_3.id], \
        flat_obj_dict[uj_step_4.id], start_date, flat_obj_dict[usage_pattern1.id], \
        flat_obj_dict[usage_pattern2.id], flat_obj_dict[uj.id], flat_obj_dict[network1.id], flat_obj_dict[network2.id], \
        flat_obj_dict[edge_storage.id], flat_obj_dict[edge_computer.id], flat_obj_dict[edge_process.id], \
        flat_obj_dict[edge_function.id], flat_obj_dict[edge_usage_journey.id], flat_obj_dict[edge_usage_pattern.id]

        cls.initialize_footprints(cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2,
                                  cls.server3, cls.usage_pattern1, cls.usage_pattern2, cls.network1, cls.network2,
                                  cls.edge_storage, cls.edge_computer)

        cls.ref_json_filename = "complex_system"

    def test_all_objects_linked_to_system(self):
        self.run_test_all_objects_linked_to_system()

    def test_remove_uj_steps_1_and_2(self):
        self.run_test_remove_uj_steps_1_and_2()

    def test_remove_uj_step_3_job(self):
        self.run_test_remove_uj_step_3_job()

    def test_remove_one_uj_step_4_job(self):
        self.run_test_remove_one_uj_step_4_job()

    def test_remove_all_uj_step_4_jobs(self):
        self.run_test_remove_all_uj_step_4_jobs()

    def test_add_new_job(self):
        self.run_test_add_new_job()

    def test_add_new_usage_pattern_with_new_network_and_edit_its_hourly_uj_starts(self):
        self.run_test_add_new_usage_pattern_with_new_network_and_edit_its_hourly_uj_starts()

    def test_add_edge_usage_pattern(self):
        self.run_test_add_edge_usage_pattern()

    def test_system_to_json(self):
        self.run_test_system_to_json(self.system)

    def test_json_to_system(self):
        self.run_test_json_to_system(self.system)

    def test_plot_footprints_by_category_and_object(self):
        self.run_test_plot_footprints_by_category_and_object()

    def test_plot_footprints_by_category_and_object_notebook_false(self):
        self.run_test_plot_footprints_by_category_and_object_notebook_false()

    def test_plot_emission_diffs(self):
        self.run_test_plot_emission_diffs()

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

    def test_semantic_units_in_calculated_attributes(self):
        self.run_test_semantic_units_in_calculated_attributes()
