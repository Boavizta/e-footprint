from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj


class ContextualModelingObjectAttribute(ObjectLinkedToModelingObj):
    def __init__(self, value: ModelingObject, modeling_obj_container=None, attr_name_in_mod_obj_container=None):
        super().__init__()
        if isinstance(value, ContextualModelingObjectAttribute):
            self._value = value._value
        elif isinstance(value, ModelingObject):
            self._value = value
        else:
            raise TypeError(f"Expected a ModelingObject or ContextualModelingObjectAttribute, got {type(value)}")
        self._value.add_to_contextual_modeling_obj_containers(self)
        self.modeling_obj_container = modeling_obj_container
        self.attr_name_in_mod_obj_container = attr_name_in_mod_obj_container

    @property
    def id(self):
        return self._value.id

    def __getattr__(self, attr):
        return getattr(self._value, attr)  # Use `getattr` instead of `__getattr__`

    def __getattribute__(self, name):
        if name == "__dict__":
            # Redirect `__dict__` access to the wrapped object's `__dict__`
            return self._value.__dict__
        return super().__getattribute__(name)

    def __setattr__(self, name, input_value):
        if name in ['_value', 'modeling_obj_container', 'attr_name_in_mod_obj_container']:
            # If setting a class attribute, use the superclass's __setattr__
            super().__setattr__(name, input_value)
        else:
            setattr(self._value, name, input_value)  # Use `setattr` instead of `__setattr__`

    def __getitem__(self, key):
        return self._value[key]

    def __repr__(self):
        return repr(self._value)

    def __str__(self):
        return str(self._value)

    def __call__(self, *args, **kwargs):
        return self._value(*args, **kwargs)

    def __eq__(self, other):
        return self._value == other

    def __hash__(self):
        return hash(self._value)  # Use built-in hash directly
