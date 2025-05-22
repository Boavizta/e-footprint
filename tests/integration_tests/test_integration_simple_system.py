from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


class IntegrationTestSimpleSystem(IntegrationTestSimpleSystemBaseClass):
    def test_all_objects_linked_to_system(self):
        self.run_test_all_objects_linked_to_system()

    def test_calculation_graph(self):
        self.run_test_calculation_graph()

    def test_object_relationship_graph(self):
        self.run_test_object_relationship_graph()

    def test_variations_on_inputs(self):
        self.run_test_variations_on_inputs()

    def test_set_uj_duration_to_0_and_back_to_previous_value(self):
        self.run_test_set_uj_duration_to_0_and_back_to_previous_value()

    def test_hourly_usage_journey_starts_update(self):
        self.run_test_hourly_usage_journey_starts_update()

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

    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_variations_on_inputs_after_json_to_system(self):
        self.run_test_variations_on_inputs_after_json_to_system()

    def test_update_usage_journey_after_json_to_system(self):
        self.run_test_update_usage_journey_after_json_to_system()

    def test_update_jobs_after_json_to_system(self):
        self.run_test_update_jobs_after_json_to_system()

    def test_modeling_object_prints(self):
        self.run_test_modeling_object_prints()

    def test_update_footprint_job_datastored_from_positive_value_to_negative_value(self):
        self.run_test_update_footprint_job_datastored_from_positive_value_to_negative_value()

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
