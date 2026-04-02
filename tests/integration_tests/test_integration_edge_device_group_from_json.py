import json
import os

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from tests.integration_tests.integration_edge_device_group_base_class import (
    IntegrationEdgeDeviceGroupBaseClass,
    INTEGRATION_TEST_DIR,
)
from tests.integration_tests.integration_test_base_class import AutoTestMethodsMeta


class IntegrationTestEdgeDeviceGroupFromJson(IntegrationEdgeDeviceGroupBaseClass, metaclass=AutoTestMethodsMeta):
    """Integration tests for EdgeDeviceGroup hierarchy loaded from JSON."""

    @classmethod
    def setUpClass(cls):
        system, start_date, building_group, floor_group, edge_device = cls.generate_edge_device_group_system()

        cls.system_json_filepath = os.path.join(
            INTEGRATION_TEST_DIR, "edge_device_group_system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)

        with open(cls.system_json_filepath, "r") as f:
            system_dict = json.load(f)
        _, flat_obj_dict = json_to_system(system_dict)

        reloaded_system = flat_obj_dict[system.id]
        reloaded_building = flat_obj_dict[building_group.id]
        reloaded_floor = flat_obj_dict[floor_group.id]
        reloaded_device = flat_obj_dict[edge_device.id]

        cls.system = reloaded_system
        cls.start_date = start_date
        cls.building_group = reloaded_building
        cls.floor_group = reloaded_floor
        cls.edge_device = reloaded_device

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.system_json_filepath):
            os.remove(cls.system_json_filepath)
