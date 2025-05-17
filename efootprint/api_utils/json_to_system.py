import array
import base64
from copy import copy
from datetime import datetime
from inspect import signature, _empty as empty_annotation, isabstract
from types import UnionType
from typing import List, get_origin, get_args

import pytz
import zstandard as zstd

import efootprint
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.logger import logger
from efootprint.utils.tools import time_it


def decompress_values(compressed_str):
    """Decompress a base64-encoded, zstd-compressed array of doubles."""
    compressed = base64.b64decode(compressed_str)
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed)
    arr = array.array("d")
    arr.frombytes(decompressed)
    return arr.tolist()


def json_to_explainable_object(input_dict, flat_obj_dict=None):
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
    elif "compressed_values" in input_dict.keys() and "unit" in input_dict.keys():
        output = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(
                decompress_values(input_dict["compressed_values"]),
                pint_unit=u(input_dict["unit"]),
                start_date=datetime.strptime(input_dict["start_date"], "%Y-%m-%d %H:%M:%S"),
            ),
            label=input_dict["label"], source=source)
    elif "value" in input_dict.keys() and input_dict["value"] is None:
        output = EmptyExplainableObject(label=input_dict["label"])
    elif "zone" in input_dict.keys():
        output = SourceObject(
            pytz.timezone(input_dict["zone"]), source, input_dict["label"])
    elif "label" not in input_dict.keys():
        if flat_obj_dict is not None:
            output = ExplainableObjectDict(
                {flat_obj_dict[key]: json_to_explainable_object(value) for key, value in input_dict.items()}
            )
        else:
            output = ExplainableObjectDict(
                {key: json_to_explainable_object(value) for key, value in input_dict.items()}
            )
    else:
        output = SourceObject(input_dict["value"], source, input_dict["label"])

    return output


def get_attribute_from_flat_obj_dict(attr_key: str, flat_obj_dict: dict):
    modeling_obj_container_id, attr_name_in_mod_obj_container, key_in_dict = eval(attr_key)
    if key_in_dict:
        return getattr(flat_obj_dict[modeling_obj_container_id], attr_name_in_mod_obj_container)[
            key_in_dict]
    else:
        return getattr(flat_obj_dict[modeling_obj_container_id], attr_name_in_mod_obj_container)


def connect_explainable_object_to_calculation_graph(explainable_object, flat_obj_dict):
    explainable_object.direct_ancestors_with_id = [
        get_attribute_from_flat_obj_dict(direct_ancestor_key, flat_obj_dict) for direct_ancestor_key in
        explainable_object.direct_ancestors_with_id
    ]
    explainable_object.direct_children_with_id = [
        get_attribute_from_flat_obj_dict(direct_child_key, flat_obj_dict) for direct_child_key in
        explainable_object.direct_children_with_id
    ]

    return explainable_object


def compute_classes_generation_order(efootprint_classes_dict):
    classes_to_order_dict = copy(efootprint_classes_dict)
    classes_generation_order = []

    while len(classes_to_order_dict) > 0:
        classes_to_append_to_generation_order = []
        for efootprint_class_name, efootprint_class in classes_to_order_dict.items():
            init_sig_params = signature(efootprint_class.__init__).parameters
            classes_needed_to_generate_current_class = []
            for init_sig_param_key in init_sig_params.keys():
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

    for class_key in [key for key in system_dict.keys() if key != efootprint_version_key]:
        if class_key not in class_obj_dict.keys():
            class_obj_dict[class_key] = {}
        current_class = efootprint_classes_dict[class_key]
        current_class_dict = {}
        for class_instance_key in system_dict[class_key].keys():
            new_obj = current_class.__new__(current_class)
            new_obj.__dict__["contextual_modeling_obj_containers"] = []
            new_obj.trigger_modeling_updates = False
            for attr_key, attr_value in system_dict[class_key][class_instance_key].items():
                if type(attr_value) == dict:
                    new_obj.__setattr__(attr_key, json_to_explainable_object(attr_value), check_input_validity=False)
                    set_attribute = getattr(new_obj, attr_key)
                    if isinstance(set_attribute, ExplainableObject):
                        if "direct_ancestors_with_id" in attr_value.keys():
                            getattr(new_obj, attr_key).direct_ancestors_with_id = attr_value["direct_ancestors_with_id"]
                            getattr(new_obj, attr_key).direct_children_with_id = attr_value["direct_children_with_id"]
                    elif isinstance(set_attribute, ExplainableObjectDict):
                        for key, value in set_attribute.items():
                            if "direct_ancestors_with_id" in attr_value[key].keys():
                                value.direct_ancestors_with_id = attr_value[key]["direct_ancestors_with_id"]
                                value.direct_children_with_id = attr_value[key]["direct_children_with_id"]
                    else:
                        raise ValueError(f"Unexpected type {type(set_attribute)} for attribute {attr_key}")
                else:
                    new_obj.__dict__[attr_key] = attr_value

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

    for class_key in class_obj_dict.keys():
        for mod_obj_key, mod_obj in class_obj_dict[class_key].items():
            for calculated_attribute_name in mod_obj.calculated_attributes:
                calculated_attribute = getattr(mod_obj, calculated_attribute_name, None)
                if isinstance(calculated_attribute, ExplainableObjectDict):
                    mod_obj.__setattr__(
                        calculated_attribute_name,
                        ExplainableObjectDict(
                            {flat_obj_dict[key]: connect_explainable_object_to_calculation_graph(value, flat_obj_dict)
                             for key, value in calculated_attribute.items()}),
                        check_input_validity=False
                    )
                if calculated_attribute is None:
                    is_loaded_from_system_with_calculated_attributes = False
                    mod_obj.__setattr__(calculated_attribute_name, EmptyExplainableObject(), check_input_validity=False)
                else:
                    is_loaded_from_system_with_calculated_attributes = True

    for class_key in class_obj_dict.keys():
        for mod_obj_key, mod_obj in class_obj_dict[class_key].items():
            for attr_key, attr_value in list(mod_obj.__dict__.items()):
                if type(attr_value) == str and attr_key != "id" and attr_value in flat_obj_dict.keys():
                    mod_obj.__setattr__(attr_key, ContextualModelingObjectAttribute(flat_obj_dict[attr_value]),
                                        check_input_validity=False)
                elif type(attr_value) == list and attr_key != "contextual_modeling_obj_containers":
                    output_val = []
                    for elt in attr_value:
                        if type(elt) == str and elt in flat_obj_dict.keys():
                            output_val.append(flat_obj_dict[elt])
                    mod_obj.__setattr__(attr_key, ListLinkedToModelingObj(output_val), check_input_validity=False)
                elif isinstance(attr_value, ExplainableObject):
                    connect_explainable_object_to_calculation_graph(attr_value, flat_obj_dict)


    for obj_type in class_obj_dict.keys():
        if obj_type != "System":
            for mod_obj in class_obj_dict[obj_type].values():
                if is_loaded_from_system_with_calculated_attributes:
                    mod_obj.trigger_modeling_updates = True
                else:
                    mod_obj.after_init()

    for system in class_obj_dict["System"].values():
        system_id = system.id
        total_footprint = system.total_footprint
        system.__init__(system.name, usage_patterns=system.usage_patterns)
        system.id = system_id
        system.total_footprint = total_footprint
        if launch_system_computations and not is_loaded_from_system_with_calculated_attributes:
            system.after_init()

    return class_obj_dict, flat_obj_dict


def get_obj_by_key_similarity(obj_container_dict, input_key):
    for key in obj_container_dict.keys():
        if input_key in key:
            return obj_container_dict[key]
