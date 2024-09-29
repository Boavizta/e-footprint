class ContextualModelingObjectAttribute:
    def __init__(self, value, modeling_obj_container, attr_name_in_mod_obj_container):
        if isinstance(value, ContextualModelingObjectAttribute):
            self._value = value._value
        else:
            self._value = value
        self.modeling_obj_container = modeling_obj_container
        self.attr_name_in_mod_obj_container = attr_name_in_mod_obj_container

    def __getattr__(self, attr):
        return getattr(self._value, attr)  # Use `getattr` instead of `__getattr__`

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

    def __instancecheck__(self, instance):
        return isinstance(instance, self._value.__class__)  # Correctly check instance type
