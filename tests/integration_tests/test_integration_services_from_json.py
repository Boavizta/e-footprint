import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
from tests.integration_tests.integration_test_base_class import INTEGRATION_TEST_DIR, AutoTestMethodsMeta


class IntegrationTestServicesFromJson(IntegrationTestServicesBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for services system loaded from JSON.

    Test methods are auto-generated from run_test_* methods in the base class.
    """
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
