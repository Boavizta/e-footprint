import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR


class IntegrationTestServicesFromJson(IntegrationTestServicesBaseClass):
    @classmethod
    def setUpClass(cls):
        # Generate system from code first
        system, start_date = cls.generate_system_with_services()

        # Save to JSON and reload
        cls.system_json_filepath = os.path.join(
            INTEGRATION_TEST_DIR, "system_with_services_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        _, flat_obj_dict = json_to_system(system_dict)

        # Get the reloaded system and use common setup
        reloaded_system = flat_obj_dict[system.id]
        cls._setup_from_system(reloaded_system, start_date)
    def test_system_to_json(self):
        self.run_test_system_to_json(self.system)

    def test_json_to_system(self):
        self.run_test_json_to_system(self.system)

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
