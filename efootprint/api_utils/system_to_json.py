import json

import efootprint
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


def recursively_write_json_dict(
        output_dict, mod_obj, save_calculated_attributes, deferred_linked_objects=None,
        is_processing_deferred_links=False):
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
    owns_deferred_queue = deferred_linked_objects is None
    if deferred_linked_objects is None:
        deferred_linked_objects = []
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
                    and candidate not in deferred_linked_objects):
                deferred_linked_objects.append(candidate)

        for key, value in mod_obj.__dict__.items():
            if isinstance(value, ModelingObject):
                recursively_write_json_dict(output_dict, value, save_calculated_attributes, deferred_linked_objects)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObject):
                for mod_obj_elt in value:
                    recursively_write_json_dict(output_dict, mod_obj_elt, save_calculated_attributes, deferred_linked_objects)
            elif isinstance(value, ExplainableObjectDict):
                for dict_key in value:
                    add_deferred_linked_object(dict_key)
        for dict_container in mod_obj.explainable_object_dicts_containers:
            add_deferred_linked_object(dict_container.modeling_obj_container)

        if owns_deferred_queue and not is_processing_deferred_links:
            while deferred_linked_objects:
                recursively_write_json_dict(
                    output_dict, deferred_linked_objects.pop(0), save_calculated_attributes, deferred_linked_objects,
                    is_processing_deferred_links=True)

    return output_dict


def collect_referenced_sources(input_system):
    from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
    from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
    sources_by_id = {}
    for mod_obj in [input_system] + input_system.all_linked_objects:
        for value in mod_obj.__dict__.values():
            if isinstance(value, ExplainableObject) and value.source is not None:
                sources_by_id.setdefault(value.source.id, value.source)
            elif isinstance(value, ExplainableObjectDict):
                for elt in value.values():
                    if isinstance(elt, ExplainableObject) and elt.source is not None:
                        sources_by_id.setdefault(elt.source.id, elt.source)
    return sources_by_id


def system_to_json(input_system, save_calculated_attributes, output_filepath=None, indent=4):
    output_dict = {"efootprint_version": efootprint.__version__}
    recursively_write_json_dict(output_dict, input_system, save_calculated_attributes)

    sources_by_id = collect_referenced_sources(input_system)
    if sources_by_id:
        sources_block = {sid: src.to_json() for sid, src in sorted(sources_by_id.items())}
        # Insert Sources block right after efootprint_version, before modeling-class blocks.
        new_output_dict = {"efootprint_version": output_dict["efootprint_version"], "Sources": sources_block}
        for k, v in output_dict.items():
            if k == "efootprint_version":
                continue
            new_output_dict[k] = v
        output_dict = new_output_dict

    if output_filepath is not None:
        with open(output_filepath, "w") as file:
            file.write(json.dumps(output_dict, indent=indent))

    return output_dict
