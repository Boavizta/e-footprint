from copy import copy
from datetime import datetime
from inspect import signature, _empty as empty_annotation, isabstract
from types import UnionType
from typing import List, get_origin, get_args
from functools import lru_cache

from pint import Quantity
import pytz

import efootprint
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.logger import logger


@lru_cache(maxsize=None)
def get_unit(unit_str):
    return u(unit_str)


def json_to_explainable_object(input_dict):
    source = None
    if "source" in input_dict:
        source = Source(input_dict["source"]["name"], input_dict["source"]["link"])
    if "value" in input_dict and "unit" in input_dict:
        value = Quantity(input_dict["value"], get_unit(input_dict["unit"]))
        output = ExplainableQuantity(value, label=input_dict["label"], source=source)
    elif "values" in input_dict and "unit" in input_dict:
        output = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(
                input_dict["values"],
                pint_unit=u(input_dict["unit"]),
                start_date=datetime.strptime(input_dict["start_date"], "%Y-%m-%d %H:%M:%S"),
                timezone=input_dict.get("timezone", None)
            ),
            label=input_dict["label"], source=source)
    elif "compressed_values" in input_dict and "unit" in input_dict:
        output = ExplainableHourlyQuantities(
            {key: input_dict[key] for key in ["compressed_values", "unit", "start_date", "timezone"]},
            label=input_dict["label"], source=source)
    elif "value" in input_dict and input_dict["value"] is None:
        output = EmptyExplainableObject(label=input_dict["label"])
    elif "zone" in input_dict:
        output = SourceObject(
            pytz.timezone(input_dict["zone"]), source, input_dict["label"])
    else:
        output = SourceObject(input_dict["value"], source, input_dict["label"])

    return output


def initialize_calculus_graph_data(explainable_object, json_input, flat_obj_dict):
    if "direct_ancestors_with_id" in json_input:
        explainable_object._keys_of_direct_ancestors_with_id_loaded_from_json = json_input[
            "direct_ancestors_with_id"]
        explainable_object._keys_of_direct_children_with_id_loaded_from_json = json_input[
            "direct_children_with_id"]
        explainable_object.explain_nested_tuples_from_json = json_input["explain_nested_tuples"]
        explainable_object.flat_obj_dict = flat_obj_dict


def compute_classes_generation_order(efootprint_classes_dict):
    classes_to_order_dict = copy(efootprint_classes_dict)
    classes_generation_order = []

    while len(classes_to_order_dict) > 0:
        classes_to_append_to_generation_order = []
        for efootprint_class_name, efootprint_class in classes_to_order_dict.items():
            init_sig_params = signature(efootprint_class.__init__).parameters
            classes_needed_to_generate_current_class = []
            for init_sig_param_key in init_sig_params:
                annotation = init_sig_params[init_sig_param_key].annotation
                if annotation is empty_annotation or isinstance(annotation, UnionType):
                    continue
                if get_origin(annotation) and get_origin(annotation) in (list, List):
                    param_type = get_args(annotation)[0]
                else:
                    param_type = annotation
                if issubclass(param_type, ModelingObject):
                    if isabstract(param_type):
                        # Case for UsageJourneyStep which has jobs params being abstract (JobBase)
                        for efootprint_class_name_to_check, efootprint_class_to_check in efootprint_classes_dict.items():
                            if issubclass(efootprint_class_to_check, param_type):
                                classes_needed_to_generate_current_class.append(efootprint_class_name_to_check)
                    else:
                        classes_needed_to_generate_current_class.append(param_type.__name__)
            append_to_classes_generation_order = True
            for class_needed in classes_needed_to_generate_current_class:
                if class_needed not in classes_generation_order:
                    append_to_classes_generation_order = False

            if append_to_classes_generation_order:
                classes_to_append_to_generation_order.append(efootprint_class_name)
        for class_to_append in classes_to_append_to_generation_order:
            classes_generation_order.append(class_to_append)
            del classes_to_order_dict[class_to_append]

    return classes_generation_order

def json_to_system(
        system_dict, launch_system_computations=True, efootprint_classes_dict=None):
    if efootprint_classes_dict is None:
        efootprint_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                   for modeling_object_class in ALL_EFOOTPRINT_CLASSES}

    efootprint_version_key = "efootprint_version"
    json_efootprint_version = system_dict.get(efootprint_version_key, None)
    if json_efootprint_version is None:
        logger.warning(
            f"Warning: the JSON file does not contain the key '{efootprint_version_key}'.")
    else:
        json_major_version = int(json_efootprint_version.split(".")[0])
        efootprint_major_version = int(efootprint.__version__.split(".")[0])
        if (json_major_version < efootprint_major_version) and json_major_version >= 9:
            from efootprint.api_utils.version_upgrade_handlers import VERSION_UPGRADE_HANDLERS
            for version in range(json_major_version, efootprint_major_version):
                system_dict = VERSION_UPGRADE_HANDLERS[version](system_dict)
        elif json_major_version != efootprint_major_version:
            logger.warning(
                f"Warning: the version of the efootprint library used to generate the JSON file is "
                f"{json_efootprint_version} while the current version of the efootprint library is "
                f"{efootprint.__version__}. Please make sure that the JSON file is compatible with the current version"
                f" of the efootprint library.")

    class_obj_dict = {}
    flat_obj_dict = {}
    explainable_object_dicts_to_create_after_objects_creation = {}

    classes_generation_order = compute_classes_generation_order(efootprint_classes_dict)
    is_loaded_from_system_with_calculated_attributes = False

    for class_key in classes_generation_order:
        if class_key not in system_dict:
            continue
        if class_key not in class_obj_dict:
            class_obj_dict[class_key] = {}
        current_class = efootprint_classes_dict[class_key]
        current_class_dict = {}
        for class_instance_key in system_dict[class_key]:
            new_obj = current_class.__new__(current_class)
            new_obj.__dict__["contextual_modeling_obj_containers"] = []
            new_obj.trigger_modeling_updates = False
            for attr_key, attr_value in system_dict[class_key][class_instance_key].items():
                if isinstance(attr_value, dict) and "label" in attr_value:
                    new_value = json_to_explainable_object(attr_value)
                    new_obj.__setattr__(attr_key, new_value, check_input_validity=False)
                    # Calculus graph data is added after setting as new_obj attribute to not interfere
                    # with set_modeling_obj_container logic
                    initialize_calculus_graph_data(new_value, attr_value, flat_obj_dict)
                elif isinstance(attr_value, dict) and "label" not in attr_value:
                    explainable_object_dicts_to_create_after_objects_creation[(new_obj, attr_key)] = attr_value
                elif isinstance(attr_value, str) and attr_key != "id" and attr_value in flat_obj_dict:
                        new_obj.__setattr__(attr_key, flat_obj_dict[attr_value], check_input_validity=False)
                elif isinstance(attr_value, list):
                    new_obj.__setattr__(
                        attr_key, [flat_obj_dict[elt] for elt in attr_value], check_input_validity=False)
                else:
                    new_obj.__setattr__(attr_key, attr_value)

            if not is_loaded_from_system_with_calculated_attributes:
                for calculated_attribute_name in new_obj.calculated_attributes:
                    calculated_attribute = getattr(new_obj, calculated_attribute_name, None)
                    if calculated_attribute is not None:
                        is_loaded_from_system_with_calculated_attributes = True
                    else:
                        new_obj.__setattr__(
                            calculated_attribute_name, EmptyExplainableObject(), check_input_validity=False)

            if class_key != "System":
                if is_loaded_from_system_with_calculated_attributes:
                    new_obj.trigger_modeling_updates = True
                else:
                    new_obj.after_init()

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

    for (modeling_obj, attr_key), attr_value in explainable_object_dicts_to_create_after_objects_creation.items():
        explainable_object_dict = ExplainableObjectDict(
            {flat_obj_dict[key]: json_to_explainable_object(value) for key, value in attr_value.items()})
        modeling_obj.__setattr__(attr_key, explainable_object_dict, check_input_validity=False)
        for explainable_object_item, explainable_object_json \
                in zip(explainable_object_dict.values(), attr_value.values()):
            initialize_calculus_graph_data(
                explainable_object_item, explainable_object_json, flat_obj_dict)

    for system in class_obj_dict["System"].values():
        system.set_initial_and_previous_footprints()
        if is_loaded_from_system_with_calculated_attributes:
            system.trigger_modeling_updates = True
        elif launch_system_computations:
            system.after_init()

    return class_obj_dict, flat_obj_dict


def get_obj_by_key_similarity(obj_container_dict, input_key):
    for key in obj_container_dict:
        if input_key in key:
            return obj_container_dict[key]
