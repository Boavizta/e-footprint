import json

import efootprint
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import computed_slots


def recursively_write_json_dict(
        output_dict, mod_obj, save_calculated_attributes, deferred_linked_objects=None,
        deferred_linked_object_ids=None, is_processing_deferred_links=False, sources_by_id=None):
    owns_deferred_queue = deferred_linked_objects is None
    if deferred_linked_objects is None:
        deferred_linked_objects = []
        deferred_linked_object_ids = set()
    mod_obj_class = mod_obj.class_as_simple_str
    if mod_obj_class not in output_dict:
        output_dict[mod_obj_class] = {}
    if mod_obj.id not in output_dict[mod_obj_class]:
        output_dict[mod_obj_class][mod_obj.id] = mod_obj.to_json(save_calculated_attributes)

        def add_deferred_linked_object(candidate):
            if (
                    candidate is not None
                    and isinstance(candidate, ModelingObject)
                    and candidate.id not in output_dict.get(candidate.class_as_simple_str, {})
                    and candidate.id not in deferred_linked_object_ids):
                deferred_linked_objects.append(candidate)
                deferred_linked_object_ids.add(candidate.id)

        # Computed values live in the reactive slots, not the instance dict: scan them too so their
        # sources and dict keys are discovered (sources are collected for inputs-only files as well,
        # matching the historical Sources block content). peek, never pull — only materialized values
        # ever contributed, and saving a model must not compute it (dict entries are read through the
        # raw dict for the same reason: facade iteration would pull).
        # efootprint_class, not type(mod_obj): objects reached through relationships arrive wrapped in
        # ContextualModelingObjectAttribute, whose own class declares no computed slots.
        attributes_to_scan = list(mod_obj.__dict__.items()) + [
            (attr_name, peeked_value) for attr_name, descriptor in computed_slots(mod_obj.efootprint_class).items()
            if (peeked_value := descriptor.peek(mod_obj)) is not None]
        for key, value in attributes_to_scan:
            if key.startswith("_"):
                continue
            if sources_by_id is not None:
                if isinstance(value, ExplainableObject) and value.source is not None:
                    sources_by_id.setdefault(value.source.id, value.source)
                elif isinstance(value, ExplainableObjectDict):
                    for elt in dict.values(value):
                        if isinstance(elt, ExplainableObject) and elt.source is not None:
                            sources_by_id.setdefault(elt.source.id, elt.source)
            if isinstance(value, ModelingObject):
                recursively_write_json_dict(output_dict, value, save_calculated_attributes, deferred_linked_objects,
                                            deferred_linked_object_ids, sources_by_id=sources_by_id)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObject):
                for mod_obj_elt in value:
                    recursively_write_json_dict(output_dict, mod_obj_elt, save_calculated_attributes,
                                                deferred_linked_objects, deferred_linked_object_ids,
                                                sources_by_id=sources_by_id)
            elif isinstance(value, ExplainableObjectDict):
                for dict_key in dict.keys(value):
                    add_deferred_linked_object(dict_key)
        for dict_container in mod_obj.explainable_object_dicts_containers:
            add_deferred_linked_object(dict_container.modeling_obj_container)

        if owns_deferred_queue and not is_processing_deferred_links:
            while deferred_linked_objects:
                next_obj = deferred_linked_objects.pop(0)
                deferred_linked_object_ids.discard(next_obj.id)
                recursively_write_json_dict(
                    output_dict, next_obj, save_calculated_attributes, deferred_linked_objects,
                    deferred_linked_object_ids, is_processing_deferred_links=True, sources_by_id=sources_by_id)

    return output_dict


def system_to_json(input_system, save_calculated_attributes, output_filepath=None, indent=4):
    output_dict = {"efootprint_version": efootprint.__version__}
    sources_by_id = {}
    recursively_write_json_dict(output_dict, input_system, save_calculated_attributes, sources_by_id=sources_by_id)

    if sources_by_id:
        sources_block = {sid: src.to_json() for sid, src in sorted(sources_by_id.items())}
        # Insert Sources block right after efootprint_version, before modeling-class blocks.
        output_dict = {"efootprint_version": output_dict["efootprint_version"], "Sources": sources_block,
                       **{k: v for k, v in output_dict.items() if k != "efootprint_version"}}

    if output_filepath is not None:
        with open(output_filepath, "w") as file:
            file.write(json.dumps(output_dict, indent=indent))

    return output_dict
