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
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
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
    elif "label" in input_dict.keys():
        output = SourceObject(input_dict["value"], source, input_dict["label"])

    return output


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
                else:
                    new_obj.__dict__[attr_key] = attr_value

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

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
            for calculated_attribute in mod_obj.calculated_attributes:
                mod_obj.__setattr__(calculated_attribute, EmptyExplainableObject(), check_input_validity=False)

    for obj_type in class_obj_dict.keys():
        if obj_type != "System":
            for mod_obj in class_obj_dict[obj_type].values():
                mod_obj.after_init()

    for system in class_obj_dict["System"].values():
        system_id = system.id
        system.__init__(system.name, usage_patterns=system.usage_patterns)
        system.id = system_id
        if launch_system_computations:
            system.after_init()

    return class_obj_dict, flat_obj_dict


def get_obj_by_key_similarity(obj_container_dict, input_key):
    for key in obj_container_dict.keys():
        if input_key in key:
            return obj_container_dict[key]
