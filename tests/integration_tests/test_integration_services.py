from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass


class IntegrationTestServices(IntegrationTestServicesBaseClass):
    def test_system_to_json(self):
        self.run_system_to_json_test(self.system)

    def test_json_to_system(self):
        self.run_json_to_system_test(self.system)

    def test_variations_on_services_inputs(self):
        self.run_test_variations_on_services_inputs()

    def test_variations_on_services_inputs_after_json_to_system(self):
        self.run_test_variations_on_services_inputs_after_json_to_system()

    def test_update_service_servers(self):
        self.run_test_update_service_servers()

    def test_update_service_jobs(self):
        self.run_test_update_service_jobs()

    def test_install_new_service_on_server_and_make_sure_system_is_recomputed(self):
        self.run_test_install_new_service_on_server_and_make_sure_system_is_recomputed()
