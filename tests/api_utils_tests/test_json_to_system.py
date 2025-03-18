import json
import os.path
from copy import deepcopy

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.constants.units import u
from tests.integration_tests.integration_test_base_class import IntegrationTestBaseClass


API_UTILS_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestJsonToSystem(IntegrationTestBaseClass):
    def setUp(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system.json"), "rb") as file:
            self.base_system_dict = json.load(file)

    def test_create_unlinked_server(self):
        full_dict = deepcopy(self.base_system_dict)
        with open(os.path.join(API_UTILS_TEST_DIR, "server_not_linked_to_usage_journey.json"), "rb") as file:
            full_dict["Server"].update(json.load(file))

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        self.assertEqual(2, len(list(class_obj_dict["Server"].values())))

    def test_create_unlinked_uj(self):
        full_dict = deepcopy(self.base_system_dict)
        with open(os.path.join(API_UTILS_TEST_DIR, "uj_not_linked_to_usage_pattern.json"), "rb") as file:
            full_dict["UsageJourney"].update(json.load(file))

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        new_uj = flat_obj_dict["uuid-New-UJ"]

        self.assertFalse(isinstance(new_uj.duration, EmptyExplainableObject))

    def test_update_value_after_system_creation(self):
        class_obj_dict, flat_obj_dict = json_to_system(self.base_system_dict)

        list(class_obj_dict["Job"].values())[0].data_transferred = SourceValue(100 * u.GB, label="new value")

    def test_system_id_doesnt_change(self):
        class_obj_dict, flat_obj_dict = json_to_system(self.base_system_dict)

        self.assertEqual(
            list(class_obj_dict["System"].values())[0].id, list(self.base_system_dict["System"].values())[0]["id"])

    def test_loads_when_usage_journey_step_has_no_jobs(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_no_jobs.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict = json_to_system(base_system_dict)

    def test_loads_version_9_system(self):
        with open(os.path.join(API_UTILS_TEST_DIR, "base_system_v9.json"), "rb") as file:
            base_system_dict = json.load(file)

        class_obj_dict, flat_obj_dict = json_to_system(base_system_dict)

    def test_json_to_system_doesnt_update_input_dict(self):
        input_dict = deepcopy(self.base_system_dict)

        json_to_system(input_dict)

        self.assertDictEqual(input_dict, self.base_system_dict)