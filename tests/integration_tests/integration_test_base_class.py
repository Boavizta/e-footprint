import re
from copy import copy
from typing import List, Optional
from unittest import TestCase
import os
import json

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, get_instance_attributes
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.constants.units import u
from efootprint.logger import logger

INTEGRATION_TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class IntegrationTestBaseClass(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_energy_footprints = {}
        cls.initial_fab_footprints = {}

        cls.ref_json_filename = None

    def footprint_has_changed(self, objects_to_test: List[ModelingObject], system=None):
        for obj in objects_to_test:
            try:
                initial_energy_footprint = self.initial_energy_footprints[obj]
                self.assertNotEqual(initial_energy_footprint, obj.energy_footprint)
                if obj.class_as_simple_str != "Network":
                    initial_fab_footprint = self.initial_fab_footprints[obj]
                    new_footprint = obj.instances_fabrication_footprint + obj.energy_footprint
                    self.assertNotEqual(
                        (initial_fab_footprint + initial_energy_footprint), new_footprint)
                    logger.info(
                        f"{obj.name} footprint has changed from {str(initial_fab_footprint + initial_energy_footprint)}"
                        f" to {str(new_footprint)}")
                else:
                    logger.info(f"{obj.name} footprint has changed from "
                                f"{initial_energy_footprint} to {obj.energy_footprint}")
            except AssertionError:
                raise AssertionError(f"Footprint hasn’t changed for {obj.name}")
        if objects_to_test[0].systems:
            system = objects_to_test[0].systems[0]
        else:
            assert system is not None
        for prev_fp, initial_fp in zip(
                (system.previous_total_energy_footprints_sum_over_period,
                 system.previous_total_fabrication_footprints_sum_over_period),
                (self.initial_system_total_energy_footprint, self.initial_system_total_fab_footprint)):
            for key in ["Servers", "Storage", "Devices", "Network"]:
                self.assertEqual(round(initial_fp[key], 4), round(prev_fp[key], 4), f"{key} footprint is not equal")

    def footprint_has_not_changed(self, objects_to_test: List[ModelingObject]):
        for obj in objects_to_test:
            try:
                initial_energy_footprint = round(self.initial_energy_footprints[obj], 3)
                if obj.class_as_simple_str != "Network":
                    initial_fab_footprint = round(self.initial_fab_footprints[obj], 3)
                    self.assertEqual(initial_fab_footprint, round(obj.instances_fabrication_footprint, 3))
                self.assertEqual(initial_energy_footprint, round(obj.energy_footprint, 3))
                logger.info(f"{obj.name} footprint is the same as in setup")
            except AssertionError:
                raise AssertionError(f"Footprint has changed for {obj.name}")

    def run_test_system_to_json(self, input_system):
        tmp_filepath = os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}_tmp_file.json")
        system_to_json(input_system, save_calculated_attributes=False, output_filepath=tmp_filepath)

        with (open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), 'r') as ref_file,
              open(tmp_filepath, 'r') as tmp_file):
            ref_file_content = ref_file.read()
            tmp_file_content = tmp_file.read()

            self.assertEqual(ref_file_content, tmp_file_content)

        os.remove(tmp_filepath)

    def run_test_json_to_system(self, input_system):
        with open(os.path.join(INTEGRATION_TEST_DIR, f"{self.ref_json_filename}.json"), "rb") as file:
            full_dict = json.load(file)

        def retrieve_obj_by_name(name, mod_obj_list):
            for obj in mod_obj_list:
                if obj.name == name:
                    return obj

        class_obj_dict, flat_obj_dict = json_to_system(full_dict)

        initial_mod_objs = input_system.all_linked_objects + [input_system]
        for obj_id, obj in flat_obj_dict.items():
            corresponding_obj = retrieve_obj_by_name(obj.name, initial_mod_objs)
            for attr_key, attr_value in obj.__dict__.items():
                if isinstance(attr_value, ExplainableQuantity) or isinstance(attr_value, ExplainableHourlyQuantities):
                    self.assertEqual(round(getattr(corresponding_obj, attr_key), 3), round(attr_value, 3),
                                     f"Attribute {attr_key} is not equal for {obj.name}")
                    self.assertEqual(getattr(corresponding_obj, attr_key).label,attr_value.label,
                                     f"Attribute {attr_key} label is not equal for {obj.name}")

            logger.info(f"All ExplainableQuantities have right values for generated object {obj.name}")

    def _test_input_change(
            self, expl_attr, expl_attr_new_value, input_object, expl_attr_name,
            calculated_attributes_that_should_be_updated:Optional[List[ExplainableObject]]=None):
        expl_attr_new_value.label = expl_attr.label
        logger.info(f"{expl_attr_new_value.label} changing from {expl_attr} to {expl_attr_new_value.value}")
        calc_attrs_that_should_change_metadata = []
        if calculated_attributes_that_should_be_updated is not None:
            for calc_attr in calculated_attributes_that_should_be_updated:
                calc_attrs_that_should_change_metadata.append(
                    {"mod_obj_container": calc_attr.modeling_obj_container,
                     "attr_name": calc_attr.attr_name_in_mod_obj_container,
                     "initial_calc_attr": calc_attr}
                )
        system = input_object.systems[0]
        input_object.__setattr__(expl_attr_name, expl_attr_new_value)
        new_footprint = system.total_footprint
        logger.info(f"system footprint went from \n{self.initial_footprint} to \n{new_footprint}")
        self.assertNotEqual(self.initial_footprint, new_footprint)
        for calc_attr_metadata in calc_attrs_that_should_change_metadata:
            new_calc_attr = getattr(calc_attr_metadata["mod_obj_container"], calc_attr_metadata["attr_name"])
            self.assertNotEqual(
                calc_attr_metadata["initial_calc_attr"], new_calc_attr,
                f"Calculated attribute {calc_attr_metadata['attr_name']} of "
                f"{calc_attr_metadata['mod_obj_container'].name} did not change")
            logger.info(f"Calculated attribute {calc_attr_metadata['attr_name']} of "
                        f"{calc_attr_metadata['mod_obj_container'].name} changed from "
                        f"{calc_attr_metadata['initial_calc_attr']} to {new_calc_attr}")
        logger.info(f"Setting back {expl_attr_new_value.label} to {expl_attr}")
        input_object.__setattr__(expl_attr_name, expl_attr)
        self.assertEqual(system.total_footprint, self.initial_footprint)

    def _test_variations_on_obj_inputs(self, input_object: ModelingObject, attrs_to_skip=None, special_mult=None):
        if attrs_to_skip is None:
            attrs_to_skip = []
        logger.warning(f"Testing input variations on {input_object.name}")
        for expl_attr_name, expl_attr in get_instance_attributes(input_object, ExplainableObject).items():
            if expl_attr_name not in attrs_to_skip and expl_attr_name not in input_object.calculated_attributes:
                expl_attr_new_value = copy(expl_attr)
                if special_mult and expl_attr_name in special_mult:
                    logger.info(f"Multiplying {expl_attr_name} by {special_mult[expl_attr_name]}")
                    expl_attr_new_value.value *= special_mult[expl_attr_name] * u.dimensionless
                else:
                    logger.info(f"Multiplying {expl_attr_name} by 100")
                    expl_attr_new_value.value *= 100 * u.dimensionless

                self._test_input_change(expl_attr, expl_attr_new_value, input_object, expl_attr_name)