from datetime import datetime

import pytz
from copy import copy

from efootprint.core.system import System
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.servers.autoscaling import Autoscaling
from efootprint.core.hardware.servers.serverless import Serverless
from efootprint.core.hardware.servers.on_premise import OnPremise
from efootprint.core.hardware.hardware_base_classes import Hardware
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.core.usage.user_journey import UserJourney
from efootprint.core.usage.job import Job
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.hardware.network import Network
from efootprint.constants.countries import Country

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import PREVIOUS_LIST_VALUE_SET_SUFFIX
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u
from efootprint.logger import logger


def json_to_explainable_object(input_dict):
    output = None
    source = None
    if "source" in input_dict.keys():
        source = Source(input_dict["source"]["name"], input_dict["source"]["link"])
    if "value" in input_dict.keys() and "unit" in input_dict.keys():
        value = input_dict["value"] * u(input_dict["unit"])
        output = ExplainableQuantity(
            value, label=input_dict["label"], source=source)
    elif "values" in input_dict.keys() and "unit" in input_dict.keys():
        output = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(
                input_dict["values"],
                pint_unit=u(input_dict["unit"]),
                start_date=datetime.strptime(input_dict["start_date"], "%Y-%m-%d %H:%M:%S"),
            ),
            label=input_dict["label"], source=source)
    elif "value" in input_dict.keys() and input_dict["value"] is None:
        output = EmptyExplainableObject(label=input_dict["label"])
    elif "zone" in input_dict.keys():
        output = SourceObject(
            pytz.timezone(input_dict["zone"]), source, input_dict["label"])

    return output


def json_to_system(system_dict):
    class_obj_dict = {}
    flat_obj_dict = {}

    for class_key in system_dict.keys():
        if class_key not in class_obj_dict.keys():
            class_obj_dict[class_key] = {}
        current_class = globals()[class_key]
        current_class_dict = {}
        for class_instance_key in system_dict[class_key].keys():
            new_obj = current_class.__new__(current_class)
            new_obj.__dict__["modeling_obj_containers"] = []
            for attr_key, attr_value in system_dict[class_key][class_instance_key].items():
                if type(attr_value) == dict:
                    new_obj.__dict__[attr_key] = json_to_explainable_object(attr_value)
                    new_obj.__dict__[attr_key].set_modeling_obj_container(new_obj, attr_key)
                else:
                    new_obj.__dict__[attr_key] = attr_value

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

    for class_key in class_obj_dict.keys():
        for mod_obj_key, mod_obj in class_obj_dict[class_key].items():
            for attr_key, attr_value in list(mod_obj.__dict__.items()):
                if type(attr_value) == str and attr_key != "id" and attr_value in flat_obj_dict.keys():
                    mod_obj.__dict__[attr_key] = flat_obj_dict[attr_value]
                    flat_obj_dict[attr_value].add_obj_to_modeling_obj_containers(mod_obj)
                elif type(attr_value) == list and attr_key != "modeling_obj_containers":
                    output_val = []
                    for elt in attr_value:
                        if type(elt) == str and elt in flat_obj_dict.keys():
                            output_val.append(flat_obj_dict[elt])
                            flat_obj_dict[elt].add_obj_to_modeling_obj_containers(mod_obj)
                    mod_obj.__dict__[attr_key] = output_val
                    mod_obj.__dict__[f"{attr_key}{PREVIOUS_LIST_VALUE_SET_SUFFIX}"] = copy(output_val)
            mod_obj.__dict__["dont_handle_input_updates"] = False
            mod_obj.__dict__["init_has_passed"] = True

    for obj_type in class_obj_dict.keys():
        if obj_type != "System":
            for mod_obj in class_obj_dict[obj_type].values():
                if len(mod_obj.systems) == 0:
                    logger.warning(
                        f"{mod_obj.class_as_simple_str} {mod_obj.name} is not linked to any existing system so needs "
                        f"to compute its own calculated attributes")
                    mod_obj.compute_calculated_attributes()

    for system in class_obj_dict["System"].values():
        system_id = system.id
        system.__init__(system.name, usage_patterns=system.usage_patterns)
        system.id = system_id
        system.after_init()

    return class_obj_dict, flat_obj_dict


def get_obj_by_key_similarity(obj_container_dict, input_key):
    for key in obj_container_dict.keys():
        if input_key in key:
            return obj_container_dict[key]
