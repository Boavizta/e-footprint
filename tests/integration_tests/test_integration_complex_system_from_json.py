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
            streaming_job, upload_job, dailymotion_job, tiktok_job, tiktok_analytics_job, \
            streaming_step, upload_step, dailymotion_step, tiktok_step, \
            start_date, usage_pattern1, usage_pattern2, uj, network = cls.generate_complex_system()

        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "complex_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        # Load the system from the JSON file
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        class_obj_dict, flat_obj_dict = json_to_system(system_dict)

        cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2, cls.server3, \
            cls.streaming_job, cls.upload_job, cls.dailymotion_job, cls.tiktok_job, cls.tiktok_analytics_job, \
            cls.streaming_step, cls.upload_step, cls.dailymotion_step, cls.tiktok_step, \
            cls.start_date, cls.usage_pattern1, cls.usage_pattern2, cls.uj, cls.network = \
        flat_obj_dict[system.id], flat_obj_dict[storage_1.id], flat_obj_dict[storage_2.id], flat_obj_dict[storage_3.id], \
        flat_obj_dict[server1.id], flat_obj_dict[server2.id], flat_obj_dict[server3.id], \
        flat_obj_dict[streaming_job.id], flat_obj_dict[upload_job.id], flat_obj_dict[dailymotion_job.id], \
        flat_obj_dict[tiktok_job.id], flat_obj_dict[tiktok_analytics_job.id], \
        flat_obj_dict[streaming_step.id], flat_obj_dict[upload_step.id], flat_obj_dict[dailymotion_step.id], \
        flat_obj_dict[tiktok_step.id], start_date, flat_obj_dict[usage_pattern1.id], \
        flat_obj_dict[usage_pattern2.id], flat_obj_dict[uj.id], flat_obj_dict[network.id]

        cls.initialize_footprints(cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2,
                                  cls.server3, cls.usage_pattern1, cls.usage_pattern2, cls.network)

        cls.ref_json_filename = "complex_system"

    def test_all_objects_linked_to_system(self):
        self.run_test_all_objects_linked_to_system()

    def test_storage_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        self.run_test_storage_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty()

    def test_on_premise_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty(self):
        self.run_test_on_premise_fixed_nb_of_instances_becomes_not_empty_then_back_to_empty()

    def test_remove_dailymotion_and_tiktok_uj_step(self):
        self.run_test_remove_dailymotion_and_tiktok_uj_step()

    def test_remove_dailymotion_single_job(self):
        self.run_test_remove_dailymotion_single_job()

    def test_remove_one_tiktok_job(self):
        self.run_test_remove_one_tiktok_job()

    def test_remove_all_tiktok_jobs(self):
        self.run_test_remove_all_tiktok_jobs()

    def test_add_new_job(self):
        self.run_test_add_new_job()

    def test_add_new_usage_pattern(self):
        self.run_test_add_new_usage_pattern()

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_add_usage_pattern_after_json_to_system(self):
        self.run_test_add_usage_pattern_after_json_to_system()

    def test_plot_footprints_by_category_and_object(self):
        self.run_test_plot_footprints_by_category_and_object()

    def test_plot_footprints_by_category_and_object_return_only_html(self):
        self.run_test_plot_footprints_by_category_and_object_return_only_html()

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
