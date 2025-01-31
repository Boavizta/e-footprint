from datetime import datetime

import pytz

import efootprint
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u
from efootprint.core.all_classes_in_order import ALL_CLASSES_IN_CANONICAL_COMPUTATION_ORDER
from efootprint.logger import logger


modeling_object_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_CLASSES_IN_CANONICAL_COMPUTATION_ORDER}


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
    elif "label" in input_dict.keys():
        output = SourceObject(input_dict["value"], source, input_dict["label"])

    return output


def json_to_system(system_dict):
    json_efootprint_version = system_dict.pop("efootprint_version", None)
    if json_efootprint_version != efootprint.__version__:
        logger.warning(
            f"Warning: the version of the efootprint library used to generate the JSON file is "
            f"{json_efootprint_version} while the current version of the efootprint library is "
            f"{efootprint.__version__}. Please make sure that the JSON file is compatible with the current version"
            f" of the efootprint library.")
    class_obj_dict = {}
    flat_obj_dict = {}

    for class_key in system_dict.keys():
        if class_key not in class_obj_dict.keys():
            class_obj_dict[class_key] = {}
        current_class = modeling_object_classes_dict[class_key]
        current_class_dict = {}
        for class_instance_key in system_dict[class_key].keys():
            new_obj = current_class.__new__(current_class)
            new_obj.__dict__["contextual_modeling_obj_containers"] = []
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
            mod_obj.trigger_modeling_updates = False
            for attr_key, attr_value in list(mod_obj.__dict__.items()):
                if type(attr_value) == str and attr_key != "id" and attr_value in flat_obj_dict.keys():
                    mod_obj.__setattr__(attr_key, ContextualModelingObjectAttribute(flat_obj_dict[attr_value]))
                elif type(attr_value) == list and attr_key != "contextual_modeling_obj_containers":
                    output_val = []
                    for elt in attr_value:
                        if type(elt) == str and elt in flat_obj_dict.keys():
                            output_val.append(flat_obj_dict[elt])
                    mod_obj.__setattr__(attr_key, ListLinkedToModelingObj(output_val))
            for calculated_attribute in mod_obj.calculated_attributes:
                mod_obj.__setattr__(calculated_attribute, EmptyExplainableObject())

    for obj_type in class_obj_dict.keys():
        if obj_type != "System":
            for mod_obj in class_obj_dict[obj_type].values():
                mod_obj.after_init()

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
