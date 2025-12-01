import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR
from tests.integration_tests.integration_complex_system_base_class import IntegrationTestComplexSystemBaseClass


class IntegrationTestComplexSystemFromJson(IntegrationTestComplexSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        # Generate system from code first
        system, start_date = cls.generate_complex_system()

        # Save to JSON and reload
        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "complex_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        _, flat_obj_dict = json_to_system(system_dict)

        # Get the reloaded system and use common setup
        reloaded_system = flat_obj_dict[system.id]
        cls._setup_from_system(reloaded_system, start_date)

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
