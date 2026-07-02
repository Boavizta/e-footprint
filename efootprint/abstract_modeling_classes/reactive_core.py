"""Declarative descriptors for computed modeling attributes.

The descriptors below are the single source of truth for how each computed attribute is derived: the
decorated getter's body is the calculation and its docstring is the doc-as-code description of the
attribute (consumed by the mkdocs object reference and the interface).

The computation engine itself still runs in an eager shim mode: values are computed eagerly by the
push-based machinery (``calculated_attributes`` ordering, ``ModelingUpdate`` chains), which expects one
``update_<attr>`` method per computed attribute (plus ``update_dict_element_in_<attr>`` for dict
attributes). Each descriptor synthesizes those methods from its getter at class-creation time
(``__set_name__``): call the getter, store the result through the regular ``ModelingObject.__setattr__``
bookkeeping. Computed values are therefore stored as plain instance attributes exactly as before, and
always shadow these (non-data) descriptors on read; ``__get__`` only fires when no value has been stored
yet and mimics a missing attribute.
"""
from typing import Type


def _register_slot(registry_name: str, owner: type, name: str, descriptor):
    if registry_name not in owner.__dict__:
        setattr(owner, registry_name, {})
    owner.__dict__[registry_name][name] = descriptor


def _collect_slots(registry_name: str, cls: type) -> dict:
    slots = {}
    for klass in reversed(cls.__mro__):
        slots.update(klass.__dict__.get(registry_name, {}))
    return slots


def computed_slots(cls: type) -> dict:
    """All computed-attribute descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_computed_slots", cls)


def _inherited_slot_doc(owner: type, name: str) -> str | None:
    for klass in owner.__mro__[1:]:
        slot = klass.__dict__.get("_declared_computed_slots", {}).get(name)
        if slot is not None and slot.__doc__:
            return slot.__doc__
    return None


def reverse_slots(cls: type) -> dict:
    """All reverse-relationship descriptors visible on cls (name -> descriptor), the most derived
    declaration winning."""
    return _collect_slots("_declared_reverse_slots", cls)


class computed_attribute:
    """Non-data descriptor declaring a computed attribute from a getter.

    The getter takes only self and returns the attribute's new value. Calling the descriptor as
    ``ParentClass.<attr>(self)`` runs the parent's getter, mirroring unbound-method syntax for
    overriding getters that refine an inherited calculation.
    """

    def __init__(self, getter):
        self.getter = getter
        self.attr_name = getter.__name__
        self.__doc__ = getter.__doc__
        self.__isabstractmethod__ = getattr(getter, "__isabstractmethod__", False)

    def __set_name__(self, owner, name):
        if name != self.getter.__name__:
            raise ValueError(
                f"Computed attribute declared as {name} but its getter is named {self.getter.__name__}")
        if self.__doc__ is None:
            # An overriding getter without its own docstring keeps the inherited description,
            # exactly as an overriding method resolved through the MRO used to.
            self.__doc__ = _inherited_slot_doc(owner, name)
        _register_slot("_declared_computed_slots", owner, name, self)
        self._synthesize_update_methods(owner, name)

    def _synthesize_update_methods(self, owner, name):
        getter = self.getter

        def update(instance):
            setattr(instance, name, getter(instance))

        update.__name__ = f"update_{name}"
        update.__qualname__ = f"{owner.__qualname__}.update_{name}"
        update.__doc__ = self.__doc__
        setattr(owner, f"update_{name}", update)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        raise AttributeError(f"{type(instance).__name__}.{self.attr_name} has not been computed yet")

    def __call__(self, instance, *args):
        return self.getter(instance, *args)


class _ComputedDictAttribute(computed_attribute):
    """Non-data descriptor declaring a computed ExplainableObjectDict attribute.

    The getter takes self plus one key object and returns the value for that key; the key set is the
    collection read from the ``keys`` attribute of the owning object. The synthesized whole-dict
    update resets the dict then delegates per key through ``update_dict_element_in_<attr>`` so that
    subclasses overriding only the per-key getter are dispatched to, exactly as the former
    hand-written orchestrators did.
    """

    def __init__(self, getter, keys: str):
        super().__init__(getter)
        self.keys = keys

    def _synthesize_update_methods(self, owner, name):
        getter = self.getter
        keys_attr = self.keys

        def update_dict_element(instance, key_obj):
            getattr(instance, name)[key_obj] = getter(instance, key_obj)

        update_dict_element.__name__ = f"update_dict_element_in_{name}"
        update_dict_element.__qualname__ = f"{owner.__qualname__}.update_dict_element_in_{name}"
        setattr(owner, f"update_dict_element_in_{name}", update_dict_element)

        def update(instance):
            from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
            setattr(instance, name, ExplainableObjectDict())
            element_update = getattr(instance, f"update_dict_element_in_{name}")
            for key_obj in getattr(instance, keys_attr):
                element_update(key_obj)

        update.__name__ = f"update_{name}"
        update.__qualname__ = f"{owner.__qualname__}.update_{name}"
        update.__doc__ = self.__doc__
        setattr(owner, f"update_{name}", update)


def computed_dict(keys: str):
    """Decorator declaring a computed dict attribute keyed by the objects listed by the ``keys``
    attribute name, e.g. ``@computed_dict(keys="usage_patterns")``."""
    def decorator(getter):
        return _ComputedDictAttribute(getter, keys)
    return decorator


def add_computed_attribute(cls: type, name: str, getter):
    """Attach a computed attribute to an already-created class (for dynamically generated getters,
    where ``__set_name__`` cannot fire automatically)."""
    descriptor = computed_attribute(getter)
    setattr(cls, name, descriptor)
    descriptor.__set_name__(cls, name)


def _find_modeling_class(class_name: str) -> Type | None:
    from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

    def _search(cls):
        if cls.__name__ == class_name:
            return cls
        for subclass in cls.__subclasses__():
            found = _search(subclass)
            if found is not None:
                return found
        return None

    return _search(ModelingObject)


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
        return [mod_obj for mod_obj in instance.modeling_obj_containers if isinstance(mod_obj, member_type)]

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._containers_of_member_type(instance)


class ReverseLink(ReverseCollection):
    """Single-container variant of ReverseCollection: the one member_type instance holding this
    object, None when there is none; several containers raise a PermissionError."""

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        containers = self._containers_of_member_type(instance)
        if len(containers) > 1:
            raise PermissionError(
                f"{type(instance).__name__} object can only be associated with one {self.member_type_name} "
                f"object but {instance.name} is associated with "
                f"{[mod_obj.name for mod_obj in containers]}")
        return containers[0] if containers else None
