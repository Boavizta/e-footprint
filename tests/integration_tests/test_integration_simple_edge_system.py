from tests.integration_tests.integration_simple_edge_system_base_class import IntegrationTestSimpleEdgeSystemBaseClass


class IntegrationTestSimpleEdgeSystem(IntegrationTestSimpleEdgeSystemBaseClass):
    def test_system_calculation_graph_right_after_json_to_system(self):
        # Because it exists in the json integration test and classes must implement same methods.
        pass

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
