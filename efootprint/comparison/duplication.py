import uuid

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.utils import css_escape
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.narrate import event, narrate


def assign_fresh_system_id(system) -> "System":
    """Re-id the System in place. Under the name-as-id convention, a fresh uuid suffix keeps the new id
    distinct from the old one even when the system's name is unchanged."""
    narrate("The System takes an id of its own, and every other object keeps its id: **two systems that share "
            "their objects' ids stay distinct**, and a comparison pairs their objects by id.",
            lambda: {"system": system.id})
    suffix = str(uuid.uuid4())[:12]
    system.id = f"{css_escape(system.name)}-{suffix}" if ModelingObject._use_name_as_id else suffix

    return system


def duplicate_system(system) -> "System":
    """A deep copy of ``system``: every object keeps its id, and the System takes a fresh one."""
    event("The modeler duplicates a system.", lambda: {"system": system.id})
    narrate("The copy is a save and a load in memory, at this version: **the copy's values attach as trusted "
            "caches**, so reading it does not recompute what the original had computed.")
    system_dict = system_to_json(system)
    class_obj_dict, _, _ = json_to_system(system_dict)
    duplicated_system = next(iter(class_obj_dict["System"].values()))

    return assign_fresh_system_id(duplicated_system)
