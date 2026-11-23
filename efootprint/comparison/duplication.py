import uuid

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.narrate import event, narrate


def assign_fresh_system_id(system) -> "System":
    """Re-id the System object in place with an id distinct from its current one, leaving every other
    object's id untouched.

    Backs the workspace distinct-system-id invariant for the non-duplicate paths (import / example /
    workspace import), where two slots must not hold the same system id while object ids stay shared.
    The new id is always different from the old one — under the name-as-id convention a fresh uuid suffix
    keeps it distinct even when the system name is unchanged (e.g. a duplicate that keeps its name).
    """
    suffix = str(uuid.uuid4())[:12]
    system.id = f"{css_escape(system.name)}-{suffix}" if ModelingObject._use_name_as_id else suffix

    return system


def duplicate_system(system) -> "System":
    """Return a deep copy of ``system`` with a fresh System id and every object id preserved.

    Serialize→deserialize round-trip: the JSON carries the original ids, so the copy's objects keep them
    (which lets the comparison diff pair objects by identity), and only the System gets a new id. The
    round-trip happens in-process at the current version, so cached computed values carry over as
    trusted caches — reading the duplicate does not recompute what the original had already computed.
    """
    event("The modeler duplicates a system.", lambda: {"system": system.id})
    narrate("The copy is a save and a load in memory, at this version: **the copy's values attach as trusted "
            "caches**, so reading it does not recompute what the original had computed.")
    system_dict = system_to_json(system)
    class_obj_dict, _, _ = json_to_system(system_dict)
    duplicated_system = assign_fresh_system_id(next(iter(class_obj_dict["System"].values())))
    narrate("`assign_fresh_system_id` gives the copy's System an id of its own, and every other object keeps "
            "its id: **the copy's objects pair with the original's by id**, and the two systems stay distinct.",
            lambda: {"original": system.id, "copy": duplicated_system.id})

    return duplicated_system
