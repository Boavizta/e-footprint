import json

import efootprint
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.reactive_core import (
    computed_slots, peek_instance_slot_registry, serialized_slots)

CALCULATION_GRAPH_KEY = "calculation_graph"


def materialize_serialized_state(modeling_objects):
    """Explicitly compute every ``serialize=True`` slot on the supplied modeling objects.

    Serialization itself remains passive and only peeks at cached values. Call this operation at a
    boundary that requires a complete snapshot, such as a user-triggered export, before serializing
    and building the calculation graph.
    """
    if isinstance(modeling_objects, ModelingObject):
        modeling_objects = [modeling_objects] + getattr(modeling_objects, "all_linked_objects", [])

    for modeling_object in dict.fromkeys(modeling_objects):
        for attr_name in serialized_slots(modeling_object.efootprint_class):
            getattr(modeling_object, attr_name)


def recursively_write_json_dict(
        output_dict, mod_obj, save_computed_state, deferred_linked_objects=None,
        deferred_linked_object_ids=None, is_processing_deferred_links=False, sources_by_id=None,
        collected_objects=None):
    owns_deferred_queue = deferred_linked_objects is None
    if deferred_linked_objects is None:
        deferred_linked_objects = []
        deferred_linked_object_ids = set()
    mod_obj_class = mod_obj.class_as_simple_str
    if mod_obj_class not in output_dict:
        output_dict[mod_obj_class] = {}
    if mod_obj.id not in output_dict[mod_obj_class]:
        output_dict[mod_obj_class][mod_obj.id] = mod_obj.to_json(save_computed_state)
        if collected_objects is not None:
            collected_objects.append(mod_obj)

        def add_deferred_linked_object(candidate):
            if (
                    candidate is not None
                    and isinstance(candidate, ModelingObject)
                    and candidate.id not in output_dict.get(candidate.class_as_simple_str, {})
                    and candidate.id not in deferred_linked_object_ids):
                deferred_linked_objects.append(candidate)
                deferred_linked_object_ids.add(candidate.id)

        # Computed values live in the reactive slots, not the instance dict: scan them too so their
        # sources and dict keys are discovered. The sources gathered here are only *candidates* — the
        # block is filtered down to those a serialized value actually references (see
        # ``collect_referenced_source_ids``), so pure computed-attribute provenance, which no
        # serialized value cites and which recompute re-attaches, is dropped rather than persisted as
        # an orphan. peek, never pull — only materialized values ever contributed, and saving a model
        # must not compute it (dict entries are read through the raw dict for the same reason: facade
        # iteration would pull).
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
                recursively_write_json_dict(output_dict, value, save_computed_state, deferred_linked_objects,
                                            deferred_linked_object_ids, sources_by_id=sources_by_id,
                                            collected_objects=collected_objects)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObject):
                for mod_obj_elt in value:
                    recursively_write_json_dict(output_dict, mod_obj_elt, save_computed_state,
                                                deferred_linked_objects, deferred_linked_object_ids,
                                                sources_by_id=sources_by_id, collected_objects=collected_objects)
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
                    output_dict, next_obj, save_computed_state, deferred_linked_objects,
                    deferred_linked_object_ids, is_processing_deferred_links=True, sources_by_id=sources_by_id,
                    collected_objects=collected_objects)

    return output_dict


def _slot_address(obj_id, registry_key):
    if isinstance(registry_key, tuple):
        name, key = registry_key
        return obj_id, name, getattr(key, "id", key)
    return obj_id, registry_key, None


def calculation_graph_section(objects) -> dict:
    """The values-free calculation-graph section: every computing slot's dependency edges (calculus
    and structural), slot-addressed as (container id, attribute name, dict key id or null) triples.
    At load, these edges are reinstalled directly, so invalidation waves triggered by later edits
    traverse valueless intermediate slots and reach the cached serialized values below them. Labels
    of currently cached values ride along (best effort) so consumers can display the graph shape
    without computing. Node order and edge lists are sorted, so the section is deterministic for a
    given model state."""
    serialized_object_ids = {obj.id for obj in objects}
    address_by_slot_id = {}
    slot_by_address = {}
    for obj in objects:
        registry = peek_instance_slot_registry(obj)
        for registry_key, slot in registry.items():
            if (isinstance(registry_key, tuple)
                    and getattr(registry_key[1], "id", None) not in serialized_object_ids):
                # A slot keyed by an object outside the serialized set (e.g. a deleted dict member
                # still referenced by the stale edges of valueless slots): dead post-load, like any
                # dependency on a foreign object.
                continue
            address = _slot_address(obj.id, registry_key)
            address_by_slot_id[id(slot)] = address
            slot_by_address[address] = slot

    edges_by_address = {}
    referenced_addresses = set()
    for address, slot in slot_by_address.items():
        if slot.getter is None:
            continue
        # Dependencies on objects outside the serialized set (e.g. a formerly linked object) are
        # dropped: they cannot be written to after a load, so their edges are dead.
        calculus_addresses = sorted(
            {dep_address for dependency in slot.calculus_dependencies
             if (dep_address := address_by_slot_id.get(id(dependency))) is not None}, key=_address_sort_key)
        structural_addresses = sorted(
            {dep_address for dependency in slot.structural_dependencies
             if (dep_address := address_by_slot_id.get(id(dependency))) is not None}, key=_address_sort_key)
        if not calculus_addresses and not structural_addresses:
            continue
        edges_by_address[address] = (calculus_addresses, structural_addresses)
        referenced_addresses.update(calculus_addresses)
        referenced_addresses.update(structural_addresses)

    node_addresses = sorted(set(edges_by_address) | referenced_addresses, key=_address_sort_key)
    index_by_address = {address: index for index, address in enumerate(node_addresses)}
    labels = {}
    for address in node_addresses:
        slot = slot_by_address[address]
        label = getattr(slot._value, "label", None) if slot.has_cached_value else slot.serialized_label
        if label:
            labels[str(index_by_address[address])] = label

    return {
        "nodes": [list(address) for address in node_addresses],
        "edges": [
            [index_by_address[address],
             [index_by_address[dep] for dep in calculus_addresses],
             [index_by_address[dep] for dep in structural_addresses]]
            for address, (calculus_addresses, structural_addresses) in sorted(
                edges_by_address.items(), key=lambda item: _address_sort_key(item[0]))],
        "labels": labels,
    }


def _address_sort_key(address):
    return address[0], address[1], address[2] or ""


def collect_referenced_source_ids(serialized_blocks) -> set:
    """The set of source ids a serialized value actually cites — every ``"source"`` string reachable
    in the written object payloads. Only these belong in the top-level ``Sources`` block: a source no
    serialized value references is pure computed-attribute provenance (re-attached deterministically
    whenever the value is recomputed), so persisting it would only leave an orphan block entry."""
    referenced = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "source" and isinstance(value, str):
                    referenced.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(serialized_blocks)
    return referenced


def system_to_json(input_system, output_filepath=None, indent=4, save_computed_state=True):
    """Serialize a system under the minimal persistence contract: every object's inputs, the cached
    values of serialize-flagged slots (with their formulas), and the values-free calculation graph.
    Anything absent recomputes on read after a load. ``save_computed_state=False`` writes a pure
    inputs-only file (no stored values, no calculation graph) — for lean committed files and
    from-scratch rebuilds. The top-level ``Sources`` block holds only sources a serialized value
    references; pure computed-attribute provenance is re-attached on recompute, so it is not
    persisted (see ``collect_referenced_source_ids``)."""
    output_dict = {"efootprint_version": efootprint.__version__}
    sources_by_id = {}
    collected_objects = []
    recursively_write_json_dict(
        output_dict, input_system, save_computed_state, sources_by_id=sources_by_id,
        collected_objects=collected_objects)

    if sources_by_id:
        referenced_source_ids = collect_referenced_source_ids(output_dict)
        sources_block = {
            sid: src.to_json() for sid, src in sorted(sources_by_id.items()) if sid in referenced_source_ids}
        if sources_block:
            # Insert Sources block right after efootprint_version, before modeling-class blocks.
            output_dict = {"efootprint_version": output_dict["efootprint_version"], "Sources": sources_block,
                           **{k: v for k, v in output_dict.items() if k != "efootprint_version"}}

    if save_computed_state:
        output_dict[CALCULATION_GRAPH_KEY] = calculation_graph_section(collected_objects)

    if output_filepath is not None:
        with open(output_filepath, "w") as file:
            file.write(json.dumps(output_dict, indent=indent))

    return output_dict
