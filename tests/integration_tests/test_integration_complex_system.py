from tests.integration_tests.integration_complex_system_base_class import IntegrationTestComplexSystemBaseClass


class IntegrationTestComplexSystem(IntegrationTestComplexSystemBaseClass):
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
