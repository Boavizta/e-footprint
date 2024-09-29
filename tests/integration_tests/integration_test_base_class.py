from typing import List
from unittest import TestCase
import os
import json

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.network import Network
from efootprint.core.system import System
from efootprint.logger import logger

INTEGRATION_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class IntegrationTestBaseClass(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_energy_footprints = {}
        cls.initial_fab_footprints = {}

        cls.ref_json_filename = None

    def footprint_has_changed(self, objects_to_test: List[ModelingObject]):
        for obj in objects_to_test:
            try:
                initial_energy_footprint = self.initial_energy_footprints[obj]
                self.assertFalse(initial_energy_footprint.value.equals(obj.energy_footprint.value))
                if obj.class_as_simple_str != "Network":
                    initial_fab_footprint = self.initial_fab_footprints[obj]
                    new_footprint = obj.instances_fabrication_footprint + obj.energy_footprint
                    self.assertFalse(
                        (initial_fab_footprint + initial_energy_footprint).value.equals(new_footprint.value))
                    logger.info(
                        f"{obj.name} footprint has changed from {str(initial_fab_footprint + initial_energy_footprint)}"
                        f" to {str(new_footprint)}")
                else:
                    logger.info(f"{obj.name} footprint has changed from "
                                f"{initial_energy_footprint} to {obj.energy_footprint}")
            except AssertionError:
                raise AssertionError(f"Footprint hasn’t changed for {obj.name}")

        for prev_fp, initial_fp in zip(
                (self.system.previous_total_energy_footprints_sum_over_period,
                 self.system.previous_total_fabrication_footprints_sum_over_period),
                (self.initial_system_total_energy_footprint, self.initial_system_total_fab_footprint)):
            for key in ["Servers", "Storage", "Devices", "Network"]:
                self.assertEqual(initial_fp[key], prev_fp[key])

    def footprint_has_not_changed(self, objects_to_test: List[ModelingObject]):
        for obj in objects_to_test:
            try:
                initial_energy_footprint = self.initial_energy_footprints[obj].value
                if obj.class_as_simple_str != "Network":
                    initial_fab_footprint = self.initial_fab_footprints[obj].value
                    self.assertTrue(initial_fab_footprint.equals(obj.instances_fabrication_footprint.value))
                self.assertTrue(initial_energy_footprint.equals(obj.energy_footprint.value))
                logger.info(f"{obj.name} footprint is the same as in setup")
            except AssertionError:
                raise AssertionError(f"Footprint has changed for {obj.name}")

    def run_system_to_json_test(self, input_system):
        mod_obj_list = [input_system] + input_system.all_linked_objects

        old_ids = {}
        for mod_obj in mod_obj_list:
            old_ids[mod_obj.name] = mod_obj.id
            mod_obj.id = "uuid" + mod_obj.id[9:]

        tmp_filepath = os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}_tmp_file.json")
        system_to_json(input_system, save_calculated_attributes=False, output_filepath=tmp_filepath)

        for mod_obj in mod_obj_list:
            mod_obj.id = old_ids[mod_obj.name]

        with (open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), 'r') as ref_file,
              open(tmp_filepath, 'r') as tmp_file):
            ref_file_content = ref_file.read()
            tmp_file_content = tmp_file.read()

            self.assertEqual(ref_file_content, tmp_file_content)

        os.remove(tmp_filepath)

    def run_json_to_system_test(self, input_system):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)

        def retrieve_obj_by_name(name, mod_obj_list):
            for obj in mod_obj_list:
                if obj.name == name:
                    return obj

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        initial_mod_objs = input_system.all_linked_objects
        for obj_id, obj in flat_obj_dict.items():
            corresponding_obj = retrieve_obj_by_name(obj.name, initial_mod_objs)
            for attr_key, attr_value in obj.__dict__.items():
                if isinstance(attr_value, ExplainableQuantity) or isinstance(attr_value, ExplainableHourlyQuantities):
                    self.assertEqual(getattr(corresponding_obj, attr_key), attr_value)
                    self.assertEqual(getattr(corresponding_obj, attr_key).label,attr_value.label)

            logger.info(f"All ExplainableQuantities have right values for generated object {obj.name}")
