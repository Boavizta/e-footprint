"""Declarative reverse relationships and their reactive read/write hooks."""

from typing import Type

from .computed_slots import _collect_slots, _register_slot
from .graph import invalidate_node_if_exists, record_read_of_node

def reverse_slots(cls: type) -> dict:
    """All reverse-relationship descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_reverse_slots", cls)


CONTAINERS_NODE_NAME = "__containers__"


def bump_reverse_nodes(value_mod_obj, container):
    """Container-field transition write hook: when value_mod_obj gains or loses ``container``, its
    reverse relationships change — invalidate its generic containers node and every typed reverse slot
    whose member type matches the container."""
    if container is None:
        return
    invalidate_node_if_exists(value_mod_obj, CONTAINERS_NODE_NAME)
    for name, descriptor in reverse_slots(type(value_mod_obj)).items():
        member_type = descriptor._resolve_member_type()
        if member_type is not None and isinstance(container, member_type):
            invalidate_node_if_exists(value_mod_obj, name)


def _find_modeling_class(class_name: str) -> Type | None:
    from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

    def _search(cls):
        matches = [cls] if cls.__name__ == class_name else []
        for subclass in cls.__subclasses__():
            matches += _search(subclass)
        return matches

    matches = list(dict.fromkeys(_search(ModelingObject)))
    if len(matches) > 1:
        raise ValueError(
            f"Several ModelingObject subclasses are named {class_name}: "
            f"{[f'{cls.__module__}.{cls.__qualname__}' for cls in matches]}. Reverse-slot member types resolve "
            f"by class name, so the name must be unambiguous.")
    return matches[0] if matches else None


class ReverseCollection:
    """Declarative reverse relationship: the instances of member_type currently holding this object as
    an attribute (read from modeling_obj_containers). member_type may be a class or a class name; names
    resolve lazily against the ModelingObject subclass tree, replacing the circular-import-driven
    function-local imports of the former property implementations. A name matching no imported class
    yields an empty collection — no instance of it can exist yet."""

    def __init__(self, member_type: type | str):
        self.member_type = member_type

    @property
    def member_type_name(self) -> str:
        return self.member_type if isinstance(self.member_type, str) else self.member_type.__name__

    def __set_name__(self, owner, name):
        self.attr_name = name
        _register_slot("_declared_reverse_slots", owner, name, self)

    def _resolve_member_type(self):
        if isinstance(self.member_type, type):
            return self.member_type
        resolved = _find_modeling_class(self.member_type)
        if resolved is not None:
            self.member_type = resolved
        return resolved

    def _containers_of_member_type(self, instance):
        member_type = self._resolve_member_type()
        if member_type is None:
            return []
        # Read the contextual containers directly rather than through the (hooked) generic
        # modeling_obj_containers property: this typed node is a strict refinement of the generic
        # containers node, so recording both would negate the refinement.
        containers = dict.fromkeys(
            contextual_container.modeling_obj_container
            for contextual_container in instance.contextual_modeling_obj_containers
            if contextual_container.modeling_obj_container is not None)
        return [mod_obj for mod_obj in containers if isinstance(mod_obj, member_type)]

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        record_read_of_node(instance, self.attr_name)
        return self._containers_of_member_type(instance)

    def __set__(self, instance, value):
        # Data-descriptor guard: reverse relationships are derived from modeling_obj_containers and are
        # read-only, exactly like the properties they replaced.
        raise AttributeError(
            f"{type(instance).__name__}.{self.attr_name} is a reverse relationship derived from "
            f"modeling_obj_containers and cannot be set directly.")


class ReverseLink(ReverseCollection):
    """Single-container variant of ReverseCollection: the one member_type instance holding this
    object, None when there is none; several containers raise a PermissionError."""

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        record_read_of_node(instance, self.attr_name)
        containers = self._containers_of_member_type(instance)
        if len(containers) > 1:
            raise PermissionError(
                f"{type(instance).__name__} object can only be associated with one {self.member_type_name} "
                f"object but {instance.name} is associated with "
                f"{[mod_obj.name for mod_obj in containers]}")
        return containers[0] if containers else None
