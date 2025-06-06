import json
import os.path
from copy import deepcopy

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.api_utils.json_to_system import json_to_system, compute_classes_generation_order
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_random_hourly_usage_df
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from tests import root_test_dir
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

    def test_compute_object_generation_order(self):
        efootprint_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                   for modeling_object_class in ALL_EFOOTPRINT_CLASSES}
        classes_generation_order = compute_classes_generation_order(efootprint_classes_dict)

        self.assertListEqual(
            ["Device", "Country", "Network", "Storage", "BoaviztaCloudServer", "Server", "GPUServer", "WebApplication",
             "VideoStreaming", "GenAIModel", "Job", "GPUJob", "WebApplicationJob", "VideoStreamingJob", "GenAIJob",
             "UsageJourneyStep", "UsageJourney", "UsagePattern", "System"],
            classes_generation_order
        )

    def test_system_with_calculated_attr_loaded_from_unique_uj_without_uj_step_and_linked_to_up_doesnt_fail(self):
        """
        This is a special case where the unique calculated attribute will be the empty duration of the UsageJourney.
        Even though the duration is empty, the json_to_system function should still understand it’s loading a system
        with calculated attributes, and therefore not try to launch the after_init method of the UsageJourney. In fact,
        this would fail because the duration, however empty, has links to the UsagePattern in its children, but the
        UsagePattern is loaded after the UsageJourney in the json_to_system function.
        """
        uj = UsageJourney("Usage journey", uj_steps=[])
        up = UsagePattern(
            "usage pattern", usage_journey=uj, devices=[], network=Network.wifi_network(), country=Countries.FRANCE(),
            hourly_usage_journey_starts=SourceHourlyValues(create_random_hourly_usage_df(timespan=1 * u.year)))

        system = System("system", usage_patterns=[up])

        system_filepath = os.path.join(
            root_test_dir, "api_utils_tests", "unique_uj_without_uj_step_and_linked_to_up.json")
        system_to_json(
            system, save_calculated_attributes=True, output_filepath=system_filepath)

        with open(system_filepath, "r") as file:
            system_dict = json.load(file)

        class_obj_dict, flat_obj_dict = json_to_system(system_dict)
