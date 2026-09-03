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
from efootprint.api_utils.system_to_json import CALCULATION_GRAPH_KEY
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
    elif json_major_version > efootprint_major_version:
        logger.warning(
            f"Warning: the version of the efootprint library used to generate the JSON file is "
            f"{json_efootprint_version} while the current version of the efootprint library is "
            f"{efootprint.__version__}. Please make sure that the JSON file is compatible with the current version"
            f" of the efootprint library.")
    return system_dict


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


def json_to_system(system_dict, efootprint_classes_dict=None):
    """Rebuild a system from its serialized form, without running any computation.

    ``system_dict`` must come from :func:`system_to_json` or a supported version migration. Arbitrary
    untrusted JSON is not supported: this loader performs the structural checks needed for canonical
    persistence, not exhaustive schema or domain validation of externally authored payloads.

    Loading is version-aware: on an exact ``efootprint_version`` match, stored computed values attach
    as trusted slot caches and the serialized calculation graph reinstalls the dependency edges, so
    later edits invalidate exactly as on a live model. On ANY version mismatch, schema upgrade
    handlers run, then whatever stored values survive them are demoted to an in-memory,
    session-scoped baseline retained on each System (see ``System.compare_to_version_baseline``) —
    the slots stay void and recompute on read, so methodology or upstream-data drift surfaces at
    upgrade time instead of persisting silently."""
    if efootprint_classes_dict is None:
        efootprint_classes_dict = {modeling_object_class.__name__: modeling_object_class
                                   for modeling_object_class in ALL_EFOOTPRINT_CLASSES}
    classes_generation_order = compute_classes_generation_order(efootprint_classes_dict)
    valid_class_keys = set(classes_generation_order) | set(ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT)

    validate_system_dict_structure(system_dict, valid_class_keys)

    file_version = system_dict.get("efootprint_version")
    version_matches = file_version == efootprint.__version__
    if not version_matches:
        system_dict = upgrade_system_dict_to_current_version(system_dict, efootprint_classes_dict)
    # Stored values are only trusted as caches when their dependency edges can be reinstalled: a
    # values-bearing file always carries the calculation-graph section, so its absence means an
    # inputs-only file (nothing to attach anyway).
    trust_stored_values = version_matches and CALCULATION_GRAPH_KEY in system_dict

    sources_dict = build_sources_dict_from_system_dict(system_dict)

    class_obj_dict = {}
    flat_obj_dict = {}
    explainable_object_dicts_to_create_after_objects_creation = {}

    for class_key in classes_generation_order:
        if class_key not in system_dict:
            continue
        if class_key not in class_obj_dict:
            class_obj_dict[class_key] = {}
        current_class = efootprint_classes_dict[class_key]
        current_class_dict = {}
        for class_instance_key in system_dict[class_key]:
            new_obj, new_obj_expl_obj_dicts_to_create_after_objects_creation = current_class.from_json_dict(
                system_dict[class_key][class_instance_key], flat_obj_dict,
                attach_stored_computed_values=trust_stored_values, sources_dict=sources_dict)

            explainable_object_dicts_to_create_after_objects_creation.update(
                new_obj_expl_obj_dicts_to_create_after_objects_creation)

            current_class_dict[class_instance_key] = new_obj
            flat_obj_dict[class_instance_key] = new_obj

        class_obj_dict[class_key] = current_class_dict

    for (modeling_obj, attr_key), attr_value in explainable_object_dicts_to_create_after_objects_creation.items():
        if attr_key in modeling_obj.calculated_attributes:
            # Canonical files never serialize computed dicts (no computed_dict slot is
            # serialize-flagged): a trusted file carrying one is corrupted or hand-edited. On a
            # version mismatch the entry is legacy data already demoted to the baseline — skip it.
            if trust_stored_values:
                raise ValueError(
                    f"{type(modeling_obj).__name__} {modeling_obj.id} stores computed dict {attr_key}, which the "
                    f"minimal serialization contract never writes: the file is corrupted or was edited by hand.")
            continue
        new_dict_items = {}
        for key, value in attr_value.items():
            new_dict_items[flat_obj_dict[key]] = explainable_object_from_json(value, sources_dict)

        explainable_object_dict = explainable_object_dict_class_from_init_annotation(type(modeling_obj), attr_key)()
        for key, value in new_dict_items.items():
            explainable_object_dict._set_entry_passively(key, value)
        current_dict = getattr(modeling_obj, attr_key, None)
        if current_dict is not None and isinstance(current_dict, ExplainableObjectDict):
            current_dict.replace_in_mod_obj_container_without_recomputation(explainable_object_dict)
        else:
            modeling_obj.__setattr__(attr_key, explainable_object_dict, check_input_validity=False)
        for explainable_object_item, explainable_object_json \
                in zip(new_dict_items.values(), attr_value.values()):
            explainable_object_item.initialize_calculus_graph_data_from_json(
                explainable_object_json, flat_obj_dict, sources_dict)

    if trust_stored_values:
        invert_children_links_of_stored_values(flat_obj_dict)
        rebuild_dependency_graph(system_dict[CALCULATION_GRAPH_KEY], flat_obj_dict)

    baseline_values = None
    if not trust_stored_values and file_version is not None:
        baseline_values = collect_baseline_values_from_other_version(
            system_dict, efootprint_classes_dict, sources_dict)
    for system in class_obj_dict.get("System", {}).values():
        if baseline_values:
            system.__dict__["_version_baseline"] = {
                "efootprint_version": file_version, "values": baseline_values}
    for modeling_obj in flat_obj_dict.values():
        modeling_obj._mark_live()

    return class_obj_dict, flat_obj_dict, system_dict


def invert_children_links_of_stored_values(flat_obj_dict):
    """Serialized values carry only their direct-ancestor addresses; the reciprocal children links
    are derived here by inversion, once every object is loaded (ancestors resolving to void slots are
    filtered by computed-structure hydration — a stored total's ancestors are themselves stored, by
    construction of the serialize set)."""
    from efootprint.abstract_modeling_classes.reactive_core import instance_slot_registry

    for obj in flat_obj_dict.values():
        for slot in list(instance_slot_registry(obj).values()):
            if slot.getter is None or not slot.has_cached_value:
                continue
            ancestors = getattr(slot._value, "direct_ancestors_with_id", None)
            if not ancestors:
                continue
            for ancestor in ancestors:
                ancestor.add_child_to_direct_children_with_id(slot._value)


def rebuild_dependency_graph(calculation_graph, flat_obj_dict):
    """Reinstall the serialized slot-level dependency edges (calculus and structural): materialize
    each node's slot — computed attribute, computed structure, dict sub-slot or getter-less bump node — then wire the edges,
    so later writes invalidate through the graph exactly as on the model that was saved."""
    from efootprint.abstract_modeling_classes.reactive_core import (
        _node_slot, computed_slots, computed_structures)

    slots = []
    for container_id, attr_name, key_id in calculation_graph["nodes"]:
        container = flat_obj_dict.get(container_id)
        if container is None or (key_id is not None and key_id not in flat_obj_dict):
            raise ValueError(
                f"Calculation-graph node ({container_id}, {attr_name}, {key_id}) references an object absent "
                f"from the file: the file is corrupted or was edited by hand.")
        key = flat_obj_dict[key_id] if key_id is not None else None
        container_class = container.efootprint_class
        declared_computed_slots = computed_slots(container_class)
        declared_computed_structures = computed_structures(container_class)
        if attr_name in declared_computed_slots:
            descriptor = declared_computed_slots[attr_name]
            slots.append(descriptor.sub_slot(container, key) if key is not None else descriptor.slot(container))
        elif attr_name in declared_computed_structures:
            slots.append(declared_computed_structures[attr_name].slot(container))
        else:
            slots.append(_node_slot(container, attr_name, key))

    for node_index, calculus_indices, structural_indices in calculation_graph["edges"]:
        slots[node_index].replace_dependencies(
            {slots[index] for index in calculus_indices}, {slots[index] for index in structural_indices})

    for node_index_str, label in calculation_graph.get("labels", {}).items():
        slots[int(node_index_str)].serialized_label = label


def collect_baseline_values_from_other_version(system_dict, efootprint_classes_dict, sources_dict):
    """Parse the stored computed values a version-mismatched file carries (after upgrade handlers
    ran) into a side-band value bag keyed by (object id, attribute name, dict key id or None) — the
    in-memory, never-serialized "as computed by vX" baseline the drift-comparison hook reads."""
    from efootprint.abstract_modeling_classes.reactive_core import computed_slots, serialized_slots

    baseline_values = {}
    for class_key, class_dict in system_dict.items():
        if class_key in ("efootprint_version", "Sources", CALCULATION_GRAPH_KEY) or not isinstance(class_dict, dict):
            continue
        efootprint_class = efootprint_classes_dict.get(class_key)
        if efootprint_class is None:
            continue
        computed_names = set(computed_slots(efootprint_class))
        raw_serialized_names = {
            name for name, descriptor in serialized_slots(efootprint_class).items() if name not in computed_names}
        for obj_id, obj_dict in class_dict.items():
            for attr_key, attr_value in obj_dict.items():
                if attr_key in computed_names and isinstance(attr_value, dict):
                    if "label" in attr_value:
                        baseline_values[(obj_id, attr_key, None)] = explainable_object_from_json(
                            attr_value, sources_dict)
                    else:
                        for key_id, value_json in attr_value.items():
                            baseline_values[(obj_id, attr_key, key_id)] = explainable_object_from_json(
                                value_json, sources_dict)
                elif attr_key in raw_serialized_names and isinstance(attr_value, (list, dict)):
                    baseline_values[(obj_id, attr_key, None)] = (
                        list(attr_value) if isinstance(attr_value, list) else dict(attr_value))
    return baseline_values
