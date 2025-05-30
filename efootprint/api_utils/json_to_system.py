from copy import copy
from inspect import signature, _empty as empty_annotation, isabstract
from types import UnionType
from typing import List, get_origin, get_args

import efootprint
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.logger import logger


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
            new_obj, new_obj_expl_obj_dicts_to_create_after_objects_creation = current_class.from_json_dict(
                system_dict[class_key][class_instance_key], flat_obj_dict, set_trigger_modeling_updates_to_true=False,
                is_loaded_from_system_with_calculated_attributes=is_loaded_from_system_with_calculated_attributes)

            explainable_object_dicts_to_create_after_objects_creation.update(
                new_obj_expl_obj_dicts_to_create_after_objects_creation)

            if not is_loaded_from_system_with_calculated_attributes and len(new_obj.calculated_attributes) > 0:
                first_new_obj_calculated_attribute = getattr(new_obj, new_obj.calculated_attributes[0], None)
                if not isinstance(first_new_obj_calculated_attribute, EmptyExplainableObject):
                    is_loaded_from_system_with_calculated_attributes = True

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
            {flat_obj_dict[key]: ExplainableObject.from_json_dict(value) for key, value in attr_value.items()})
        modeling_obj.__setattr__(attr_key, explainable_object_dict, check_input_validity=False)
        for explainable_object_item, explainable_object_json \
                in zip(explainable_object_dict.values(), attr_value.values()):
                explainable_object_item.initialize_calculus_graph_data_from_json(explainable_object_json, flat_obj_dict)

    for system in class_obj_dict["System"].values():
        system.set_initial_and_previous_footprints()
        if is_loaded_from_system_with_calculated_attributes:
            system.trigger_modeling_updates = True
        elif launch_system_computations:
            system.after_init()

    return class_obj_dict, flat_obj_dict
