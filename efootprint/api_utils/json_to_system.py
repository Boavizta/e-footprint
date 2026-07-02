from copy import copy
from inspect import _empty as empty_annotation, isabstract
from types import UnionType
from typing import List, get_origin, get_args

import efootprint
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, explainable_object_from_json
from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from efootprint.api_utils.suppressed_efootprint_classes import ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT
from efootprint.constants.sources import Sources
from efootprint.logger import logger
from efootprint.utils.tools import get_init_signature_params


def explainable_object_dict_class_from_init_annotation(modeling_obj_class, attr_name):
    """Dict attributes are rebuilt at load with the class their __init__ annotation declares (e.g.
    WeightedExplainableObjectDict), so invariants enforced by dict subclasses survive deserialization.
    Calculated dict attributes have no init annotation and stay plain ExplainableObjectDicts."""
    init_sig_param = get_init_signature_params(modeling_obj_class).get(attr_name)
    if init_sig_param is not None:
        annotation_origin = get_origin(init_sig_param.annotation)
        if isinstance(annotation_origin, type) and issubclass(annotation_origin, ExplainableObjectDict):
            return annotation_origin
    return ExplainableObjectDict


def validate_system_dict_structure(system_dict, valid_class_keys):
    for class_key, class_dict in system_dict.items():
        if class_key not in valid_class_keys:
            continue
        if not isinstance(class_dict, dict):
            raise TypeError(
                f"Detected invalid data at `{class_key}` level: {class_dict}. "
                f"Only object dictionaries are valid at this level. "
                f"This usually means the JSON file was edited manually or corrupted.")
        for object_key, object_dict in class_dict.items():
            if not isinstance(object_dict, dict) or len(object_dict) == 0:
                raise ValueError(
                    f"Detected invalid data at `{class_key}` level: {object_dict}. "
                    f"Only object dictionaries are valid at this level. "
                    f"This usually means the JSON file was edited manually or corrupted.")
            object_id = object_dict.get("id")
            if object_id is not None and object_id != object_key:
                raise ValueError(
                    f"Invalid JSON structure for `{class_key}.{object_key}`: embedded id is `{object_id}`. "
                    f"Object keys must match their `id`.")


def compute_classes_generation_order(efootprint_classes_dict):
    classes_to_order_dict = copy(efootprint_classes_dict)
    classes_generation_order = []

    def get_all_subclasses_names(efootprint_class, efootprint_classes_dict):
        if isabstract(efootprint_class):
            output = []
            for efootprint_class_name_to_check, efootprint_class_to_check in efootprint_classes_dict.items():
                if issubclass(efootprint_class_to_check, efootprint_class):
                    output.append(efootprint_class_name_to_check)
        else:
            output = [efootprint_class.__name__]

        return output

    while len(classes_to_order_dict) > 0:
        classes_to_append_to_generation_order = []
        for efootprint_class_name, efootprint_class in classes_to_order_dict.items():
            init_sig_params = get_init_signature_params(efootprint_class)
            classes_needed_to_generate_current_class = sum([
                get_all_subclasses_names(efootprint_class, efootprint_classes_dict)
                for efootprint_class in efootprint_class.classes_outside_init_params_needed_for_generating_from_json
            ], start=[])
            for init_sig_param_key in init_sig_params:
                annotation = init_sig_params[init_sig_param_key].annotation
                if annotation is empty_annotation or isinstance(annotation, UnionType):
                    continue
                annotation_origin = get_origin(annotation)
                if annotation_origin and annotation_origin in (list, List):
                    param_type = get_args(annotation)[0]
                elif (annotation_origin is not None
                      and isinstance(annotation_origin, type)
                      and issubclass(annotation_origin, ExplainableObjectDict)):
                    type_arg = get_args(annotation)[0]
                    if isinstance(type_arg, str):
                        param_type = efootprint_classes_dict.get(type_arg)
                    else:
                        param_type = type_arg
                    if param_type is None:
                        continue
                else:
                    param_type = annotation
                if not isinstance(param_type, type):
                    continue
                if param_type is efootprint_class:
                    # Self-reference (e.g. EdgeDeviceGroup.sub_group_counts): instances of the
                    # same class are linked in a second pass, so there's no self-dependency.
                    continue
                if issubclass(param_type, ModelingObject):
                    classes_needed_to_generate_current_class += (
                        get_all_subclasses_names(param_type, efootprint_classes_dict))
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

def upgrade_system_dict_to_current_version(system_dict, efootprint_classes_dict=None):
    efootprint_version_key = "efootprint_version"
    json_efootprint_version = system_dict.get(efootprint_version_key, None)
    if json_efootprint_version is None:
        logger.warning(
            f"Warning: the JSON file does not contain the key '{efootprint_version_key}'.")
        return system_dict
    json_major_version = int(json_efootprint_version.split(".")[0])
    efootprint_major_version = int(efootprint.__version__.split(".")[0])
    if (json_major_version < efootprint_major_version) and json_major_version >= 9:
        from copy import deepcopy
        from efootprint.api_utils.version_upgrade_handlers import VERSION_UPGRADE_HANDLERS
        if efootprint_classes_dict is None:
            efootprint_classes_dict = {cls.__name__: cls for cls in ALL_EFOOTPRINT_CLASSES}
        system_dict = deepcopy(system_dict)
        for version in range(json_major_version, efootprint_major_version):
            system_dict = VERSION_UPGRADE_HANDLERS[version](system_dict, efootprint_classes_dict)
    elif json_major_version != efootprint_major_version:
        logger.warning(
            f"Warning: the version of the efootprint library used to generate the JSON file is "
            f"{json_efootprint_version} while the current version of the efootprint library is "
            f"{efootprint.__version__}. Please make sure that the JSON file is compatible with the current version"
            f" of the efootprint library.")
    return system_dict


def detect_system_saved_with_calculated_attributes(
        system_dict, classes_generation_order, efootprint_classes_dict) -> bool:
    """True when the file stores computed values (an object serializes every one of its computed
    attributes). Detected up front so loading can attach stored computed values as caches — or skip
    the stray now-computed attributes older inputs-only files stored back when they were inputs."""
    from efootprint.abstract_modeling_classes.reactive_core import computed_slots

    for class_key in classes_generation_order:
        if class_key not in system_dict:
            continue
        computed_names = list(computed_slots(efootprint_classes_dict[class_key]))
        if not computed_names:
            continue
        for object_json_dict in system_dict[class_key].values():
            if all(computed_name in object_json_dict for computed_name in computed_names):
                return True
    return False


def build_sources_dict_from_system_dict(system_dict):
    raw_sources = system_dict.get("Sources", {}) or {}
    sources_dict = {}
    sentinel_singletons = {Sources.USER_DATA.id: Sources.USER_DATA, Sources.HYPOTHESIS.id: Sources.HYPOTHESIS}
    for source_id, source_payload in raw_sources.items():
        if source_id in sentinel_singletons:
            sources_dict[source_id] = sentinel_singletons[source_id]
        else:
            sources_dict[source_id] = Source.from_json_dict(source_payload)
    return sources_dict


def json_to_system(
        system_dict, launch_system_computations=True, efootprint_classes_dict=None):
    if efootprint_classes_dict is None:
        efootprint_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                   for modeling_object_class in ALL_EFOOTPRINT_CLASSES}
    classes_generation_order = compute_classes_generation_order(efootprint_classes_dict)
    valid_class_keys = set(classes_generation_order) | set(ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT)

    validate_system_dict_structure(system_dict, valid_class_keys)

    system_dict = upgrade_system_dict_to_current_version(system_dict, efootprint_classes_dict)

    sources_dict = build_sources_dict_from_system_dict(system_dict)

    class_obj_dict = {}
    flat_obj_dict = {}
    explainable_object_dicts_to_create_after_objects_creation = {}
    is_loaded_from_system_with_calculated_attributes = detect_system_saved_with_calculated_attributes(
        system_dict, classes_generation_order, efootprint_classes_dict)

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
                is_loaded_from_system_with_calculated_attributes=is_loaded_from_system_with_calculated_attributes,
                sources_dict=sources_dict)

            explainable_object_dicts_to_create_after_objects_creation.update(
                new_obj_expl_obj_dicts_to_create_after_objects_creation)

            if class_key != "System":
                if is_loaded_from_system_with_calculated_attributes:
                    new_obj.trigger_modeling_updates = True
                else:
                    new_obj.after_init()

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

    for (modeling_obj, attr_key), attr_value in explainable_object_dicts_to_create_after_objects_creation.items():
        new_dict_items = {}
        for key, value in attr_value.items():
            new_dict_items[flat_obj_dict[key]] = explainable_object_from_json(value, sources_dict)

        if attr_key in modeling_obj.calculated_attributes:
            if not is_loaded_from_system_with_calculated_attributes:
                continue
            # Stored computed dict: attach as cached sub-slot values, never read the attribute first
            # (reading a void computed dict would compute it).
            from efootprint.abstract_modeling_classes.reactive_core import computed_slots
            explainable_object_dict = ExplainableObjectDict(new_dict_items)
            computed_slots(type(modeling_obj))[attr_key].attach_cached_value(
                modeling_obj, explainable_object_dict)
        else:
            explainable_object_dict = explainable_object_dict_class_from_init_annotation(
                type(modeling_obj), attr_key)(new_dict_items)
            current_dict = getattr(modeling_obj, attr_key, None)
            if current_dict is not None and isinstance(current_dict, ExplainableObjectDict):
                current_dict.replace_in_mod_obj_container_without_recomputation(explainable_object_dict)
            else:
                modeling_obj.__setattr__(attr_key, explainable_object_dict, check_input_validity=False)
            explainable_object_dict.trigger_modeling_updates = True

        for explainable_object_item, explainable_object_json \
                in zip(new_dict_items.values(), attr_value.values()):
            explainable_object_item.initialize_calculus_graph_data_from_json(
                explainable_object_json, flat_obj_dict, sources_dict)

    if is_loaded_from_system_with_calculated_attributes:
        rebuild_computed_dependency_edges(flat_obj_dict)

    for system in class_obj_dict["System"].values():
        if is_loaded_from_system_with_calculated_attributes:
            # Calculus edges above make input edits invalidate precisely; structural edges only exist
            # once getters have run, so the first relationship change triggers a full recompute.
            from efootprint.abstract_modeling_classes.modeling_object import mark_system_edges_incomplete
            mark_system_edges_incomplete(system)
            system.trigger_modeling_updates = True
        elif launch_system_computations:
            system.after_init()

    return class_obj_dict, flat_obj_dict, system_dict


def rebuild_computed_dependency_edges(flat_obj_dict):
    """Rebuild the calculus dependency edges of every stored computed value from its serialized
    arithmetic ancestry, so input edits on a loaded model invalidate exactly as on a computed one."""
    from efootprint.abstract_modeling_classes.reactive_core import (
        _node_slot, instance_slot_registry, slot_of_attached_value)

    for obj in flat_obj_dict.values():
        for slot in list(instance_slot_registry(obj).values()):
            if slot.getter is None or not slot.has_cached_value:
                continue
            ancestors = getattr(slot._value, "direct_ancestors_with_id", None)
            if not ancestors:
                continue
            dependencies = set()
            for ancestor in ancestors:
                is_input_dict_value = ancestor._reactive_slot is None and ancestor.dict_container is not None
                dependencies.add(slot_of_attached_value(ancestor))
                if is_input_dict_value:
                    # An input-dict value: reading it live also couples the reader to the whole-dict
                    # node (replacing the dict invalidates readers of any of its entries).
                    dependencies.add(_node_slot(
                        ancestor.modeling_obj_container, ancestor.attr_name_in_mod_obj_container))
            slot.replace_dependencies(calculus_dependencies=dependencies)
