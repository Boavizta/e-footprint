from typing import Type

_NOT_CACHED = object()  # Sentinel for distinguishing "not cached" from "cached as None"

# Attributes that ObjectLinkedToModelingObj instances need
_OBJECT_LINKED_SLOTS = (
    'modeling_obj_container',
    'attr_name_in_mod_obj_container',
    'former_modeling_obj_container_id',
    'former_attr_name_in_mod_obj_container',
    '_cached_id',
    '_cached_full_str_tuple_id',
    '_cached_attribute_id',
    '_cached_dict_container',
    '_cached_key_in_dict',
    '_cached_list_container',
    '_cached_indexes_in_list',
    '_reactive_slot',
)


def peek_attribute_value(container, attr_name):
    """The object stored at a (container, attribute) address, without ever running a computation:
    instance dict for inputs, facade or cached slot value for computed attributes. Used by the graph
    bookkeeping (id resolution, dict containers, lazy calculus-graph rehydration), which must never
    re-enter the engine — pulling there would recurse into the very slot being attached or recompute
    slots mid-invalidation."""
    if attr_name in container.__dict__:
        return container.__dict__[attr_name]
    facade = container.__dict__.get("_computed_dict_facades", {}).get(attr_name)
    if facade is not None:
        return facade
    slot = container.__dict__.get("_reactive_slots", {}).get(attr_name)
    if slot is not None and slot.has_cached_value:
        return slot._value
    return None


class ObjectLinkedToModelingObjBase:
    """Base class with all methods.

    Used by classes that need multiple inheritance with built-in types (dict, list).
    Has empty __slots__ to allow subclasses to define their own slots.
    Dict/list hybrid classes inherit from this and will have __dict__ because
    built-in types don't support slots.
    """
    __slots__ = ()  # Empty slots - subclasses add their own

    def __init__(self):
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None
        # kept in memory just for easier debugging and error messages
        self.former_modeling_obj_container_id = None
        self.former_attr_name_in_mod_obj_container = None
        self._cached_id = None
        self._cached_full_str_tuple_id = None
        self._cached_attribute_id = None
        self._cached_dict_container = _NOT_CACHED
        self._cached_key_in_dict = None
        self._cached_list_container = _NOT_CACHED
        self._cached_indexes_in_list = None
        # Backpointer to this value's node in the reactive dependency graph, set when the engine
        # attaches the value to a computed slot (input values resolve their node lazily instead).
        self._reactive_slot = None

    def set_modeling_obj_container(
            self, new_parent_modeling_object: Type["ModelingObject"] | None, attr_name: str | None):
        if new_parent_modeling_object is None or attr_name is None:
            assert new_parent_modeling_object == attr_name, (
                f"Both new_parent_modeling_object and attr_name should be None or not None. "
                f"Here new_parent_modeling_object is {new_parent_modeling_object} and attr_name is {attr_name}.")
        if (self.modeling_obj_container is not None and new_parent_modeling_object is not None and
                new_parent_modeling_object != self.modeling_obj_container):
            raise PermissionError(
                f"A {self.__class__.__name__} can’t be attributed to more than one ModelingObject. Here "
                f"{self} is trying to be linked to {new_parent_modeling_object.name} but is already linked to "
                f"{self.modeling_obj_container.name}.")
        self.former_modeling_obj_container_id = self.modeling_obj_container.id \
            if self.modeling_obj_container is not None else None
        self.former_attr_name_in_mod_obj_container = self.attr_name_in_mod_obj_container
        self.modeling_obj_container = new_parent_modeling_object
        self.attr_name_in_mod_obj_container = attr_name
        if new_parent_modeling_object is None:
            self._reactive_slot = None
        self._cached_id = None
        self._cached_full_str_tuple_id = None
        self._cached_attribute_id = None
        self._cached_dict_container = _NOT_CACHED
        self._cached_key_in_dict = None
        self._cached_list_container = _NOT_CACHED
        self._cached_indexes_in_list = None

    def raise_error_if_modeling_obj_container_is_none(self):
        if self.modeling_obj_container is None:
            raise ValueError(
                f"{self} doesn’t have a modeling_obj_container but is still retrieved in the context of calculation "
                f"graph parsing. It probably means that it has been replaced in its former container but all "
                f"dependencies haven’t been duly updated. Its former modeling_obj_container id was "
                f"{self.former_modeling_obj_container_id} and its former attribute name in this container was"
                f" {self.former_attr_name_in_mod_obj_container}.")

    @property
    def id(self):
        if self._cached_id is None:
            self.raise_error_if_modeling_obj_container_is_none()
            if self.dict_container is None:
                self._cached_id = f"{self.attr_name_in_mod_obj_container}-in-{self.modeling_obj_container.id}"
            else:
                self._cached_id = f"{self.attr_name_in_mod_obj_container}[{self.key_in_dict.id}]-in-{self.modeling_obj_container.id}"
        return self._cached_id

    @property
    def full_str_tuple_id(self):
        if self._cached_full_str_tuple_id is None:
            self.raise_error_if_modeling_obj_container_is_none()
            self._cached_full_str_tuple_id = str((self.modeling_obj_container.id,
                    self.attr_name_in_mod_obj_container,
                    self.key_in_dict.id if self.dict_container is not None else None))
        return self._cached_full_str_tuple_id

    @property
    def attribute_id(self):
        if self._cached_attribute_id is None:
            self.raise_error_if_modeling_obj_container_is_none()
            self._cached_attribute_id = f"{self.attr_name_in_mod_obj_container}-in-{self.modeling_obj_container.id}"
        return self._cached_attribute_id

    def _container_attr_value_without_computing(self):
        return peek_attribute_value(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    @property
    def dict_container(self):
        if self._cached_dict_container is not _NOT_CACHED:
            return self._cached_dict_container
        output = None
        if self.modeling_obj_container is not None:
            container_attr_value = self._container_attr_value_without_computing()
            if isinstance(container_attr_value, dict) and id(container_attr_value) != id(self):
                output = container_attr_value
        self._cached_dict_container = output
        return output

    @property
    def key_in_dict(self):
        if self._cached_key_in_dict is not None:
            return self._cached_key_in_dict
        dict_container = self.dict_container
        if dict_container is None:
            raise ValueError(f"{self} is not linked to a ModelingObject through a dictionary attribute.")
        else:
            output_key = None
            for key, value in dict.items(dict_container):
                if id(value) == id(self):
                    if output_key is None:
                        output_key = key
                    else:
                        raise ValueError(f"Multiple keys found for {self} in {dict_container}.")
        self._cached_key_in_dict = output_key
        return output_key

    @property
    def list_container(self):
        if self._cached_list_container is not _NOT_CACHED:
            return self._cached_list_container
        output = None
        if not isinstance(self, list) and self.modeling_obj_container is not None:
            container_attr_value = self._container_attr_value_without_computing()
            if isinstance(container_attr_value, list):
                output = container_attr_value
        self._cached_list_container = output
        return output

    @property
    def indexes_in_list(self):
        if self._cached_indexes_in_list is not None:
            return self._cached_indexes_in_list
        if self.list_container is None:
            raise ValueError(f"{self} is not linked to a ModelingObject through a list attribute.")
        else:
            output_indexes = []
            for index, value in enumerate(self.list_container):
                if id(value) == id(self):
                    output_indexes.append(index)
        self._cached_indexes_in_list = output_indexes
        return output_indexes

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        assert self.modeling_obj_container is not None, f"{self} is not linked to a ModelingObject."
        assert isinstance(new_value, ObjectLinkedToModelingObjBase), (
            f"Trying to replace {self} by {new_value} which is not an instance of "
            f"ObjectLinkedToModelingObjBase.")
        mod_obj_container = self.modeling_obj_container
        attr_name = self.attr_name_in_mod_obj_container
        mod_obj_container.check_input_value(
            attr_name, new_value, replaced_value=self)
        dict_container = self.dict_container
        if dict_container is not None:
            if self.key_in_dict not in dict_container:
                raise KeyError(f"object of id {self.key_in_dict.id} not found as key in {attr_name} attribute of "
                               f"{mod_obj_container.id} when trying to replace {self} by {new_value}. "
                               f"This should not happen.")
            if hasattr(dict_container, "_set_entry_passively"):
                dict_container._set_entry_passively(self.key_in_dict, new_value)
            else:
                self.set_modeling_obj_container(None, None)
                dict.__setitem__(dict_container, self.key_in_dict, new_value)
                new_value.set_modeling_obj_container(mod_obj_container, attr_name)
        elif self.list_container is not None:
            if not self.indexes_in_list:
                raise ValueError(f"object of id {self.id} not found in {attr_name} attribute of {mod_obj_container.id} "
                                 f"when trying to replace \n\n{self}\nby\n\n{new_value}.\n\nThis should not happen.")
            for index in self.indexes_in_list:
                self.list_container._set_entry_passively(index, new_value)
        else:
            self.set_modeling_obj_container(None, None)
            mod_obj_container.__dict__[attr_name] = new_value
            new_value.set_modeling_obj_container(mod_obj_container, attr_name)


class ObjectLinkedToModelingObj(ObjectLinkedToModelingObjBase):
    """Slotted version of ObjectLinkedToModelingObjBase for memory optimization.

    Use this as base class for ExplainableObject and other classes that don't
    need multiple inheritance with dict/list. Uses __slots__ to reduce memory
    footprint and fragmentation.
    """
    __slots__ = _OBJECT_LINKED_SLOTS
