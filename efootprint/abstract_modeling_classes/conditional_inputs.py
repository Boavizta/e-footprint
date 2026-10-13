"""Query conditional input choices and their declared direct relationships."""

from dataclasses import dataclass
from types import UnionType
from typing import Union, get_args, get_origin

from efootprint.abstract_modeling_classes.input_values import input_values_match
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.utils.tools import get_init_signature_params


@dataclass(frozen=True)
class _Trigger:
    dependent_type: type
    dependent_attribute: str
    reverse_hops: tuple[tuple[type, str], ...]


_trigger_index: dict[tuple[type, str], list[_Trigger]] = {}


def register_conditional_inputs(cls):
    """Index effective declarations when a modeling subclass is defined."""
    pending = {}
    for attribute, declaration in cls.conditional_list_values.items():
        path = declaration["depends_on"]

        def invalid_path(reason):
            return ValueError(f"Invalid conditional input path {path!r} for {cls.__name__}.{attribute}: {reason}")

        if not isinstance(path, str) or not path or any(not part for part in path.split(".")):
            raise invalid_path("expected a nonempty dotted input path")
        parts = path.split(".")

        def register_path(owner_type, position, forward_hops):
            name = parts[position]
            parameter = get_init_signature_params(owner_type).get(name)
            if parameter is None or name == "self":
                raise invalid_path(f"{owner_type.__name__}.{name} is not a constructor input")
            entry = _Trigger(cls, attribute, tuple(reversed(forward_hops)))
            entries = pending.setdefault((owner_type, name), [])
            if entry not in entries:
                entries.append(entry)
            if position == len(parts) - 1:
                return
            annotation = parameter.annotation
            members = get_args(annotation) if get_origin(annotation) in (Union, UnionType) else (annotation,)
            targets = [member for member in members if member is not type(None)]
            if not targets or any(not isinstance(target, type) or not issubclass(target, ModelingObject)
                                  for target in targets):
                raise invalid_path(f"{owner_type.__name__}.{name} must declare a direct ModelingObject relationship")
            for target in targets:
                register_path(target, position + 1, forward_hops + ((owner_type, name),))

        register_path(cls, 0, ())

    # A malformed declaration must not leave partial routes behind.
    for key, entries in pending.items():
        _trigger_index.setdefault(key, []).extend(entries)


def dependent_inputs(changed_addresses, proposed_changes=None):
    """Return the next dependent input addresses through current or proposed direct links."""
    from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import (
        ContextualModelingObjectAttribute)

    proposed_changes = proposed_changes or {}
    proposed_links = {}
    for (owner, attribute), value in proposed_changes.items():
        owner = ModelingObject._unwrap_contextual_input_value(owner)
        value = ModelingObject._unwrap_contextual_input_value(value)
        if isinstance(value, ModelingObject):
            proposed_links.setdefault(value, []).append((owner, attribute))

    def referring_owners(child, owner_type, relationship):
        for wrapper in child.contextual_modeling_obj_containers:
            owner = wrapper.modeling_obj_container
            if (type(wrapper) is ContextualModelingObjectAttribute
                    and isinstance(owner, owner_type)
                    and wrapper.attr_name_in_mod_obj_container == relationship
                    and (owner, relationship) not in proposed_changes
                    and owner.__dict__.get(relationship) is wrapper):
                yield owner
        for owner, attribute in proposed_links.get(child, ()):
            if attribute == relationship and isinstance(owner, owner_type):
                yield owner

    affected = set()
    for changed_owner, changed_attribute in changed_addresses:
        changed_owner = ModelingObject._unwrap_contextual_input_value(changed_owner)
        for owner_type in type(changed_owner).__mro__:
            for entry in _trigger_index.get((owner_type, changed_attribute), ()):
                owners = {changed_owner}
                for referring_type, relationship in entry.reverse_hops:
                    owners = {parent for child in owners
                              for parent in referring_owners(child, referring_type, relationship)}
                affected.update((owner, entry.dependent_attribute) for owner in owners
                                if type(owner) is entry.dependent_type)
    return affected


def resolve_input_path(root, path, proposed_changes=None):
    """Return the actual owner and final input, resolving proposed links without attachment."""
    proposed_changes = proposed_changes or {}
    root = ModelingObject._unwrap_contextual_input_value(root)
    owner = root
    parts = path.split(".")
    for position, name in enumerate(parts):
        address = (owner, name)
        value = proposed_changes[address] if address in proposed_changes else owner.__dict__.get(name)
        if value is None:
            raise ValueError(f"Cannot resolve input path {path!r} on {type(root).__name__}: {name!r} is not set")
        if position == len(parts) - 1:
            return owner, name
        owner = ModelingObject._unwrap_contextual_input_value(value)
        if not isinstance(owner, ModelingObject):
            raise ValueError(f"Cannot resolve input path {path!r} on {type(root).__name__}: "
                             f"{name!r} is not a direct ModelingObject relationship")


def allowed_values(dependent_type, attribute, controller_value):
    """Read ordered choices, returning None for unrestricted and () for no permitted value."""
    static = dependent_type.list_values.get(attribute)
    declaration = dependent_type.conditional_list_values.get(attribute)
    if declaration is not None:
        for controller, choices in declaration["conditional_list_values"].items():
            if input_values_match(controller_value, controller):
                return tuple(choice for choice in choices
                             if static is None or any(input_values_match(choice, allowed) for allowed in static))
    return tuple(static) if static is not None else None
