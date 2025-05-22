from tests.integration_tests.integration_complex_system_base_class import IntegrationTestComplexSystemBaseClass


class IntegrationTestComplexSystemFromJson(IntegrationTestComplexSystemBaseClass):
    @classmethod
    def setUpClass(cls):
        cls.system, cls.storage_1, cls.storage_2, cls.storage_3, cls.server1, cls.server2, cls.server3, \
            cls.streaming_job, cls.upload_job, cls.dailymotion_job, cls.tiktok_job, cls.tiktok_analytics_job, \
            cls.streaming_step, cls.upload_step, cls.dailymotion_step, cls.tiktok_step, \
            cls.start_date, cls.usage_pattern1, cls.usage_pattern2, cls.uj, cls.network = cls.generate_complex_system()

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
