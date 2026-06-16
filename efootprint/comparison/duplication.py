import uuid

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json


def assign_fresh_system_id(system) -> "System":
    """Re-id the System object in place with an id distinct from its current one, leaving every other
    object's id untouched.

    Backs the workspace distinct-system-id invariant for the non-duplicate paths (import / template /
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
    (which lets the comparison diff pair objects by identity), and only the System gets a new id.
    """
    system_dict = system_to_json(system, save_calculated_attributes=False)
    class_obj_dict, _, _ = json_to_system(system_dict)
    duplicated_system = next(iter(class_obj_dict["System"].values()))

    return assign_fresh_system_id(duplicated_system)
