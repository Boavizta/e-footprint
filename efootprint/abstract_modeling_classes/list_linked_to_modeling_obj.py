from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, AfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.reactive_core import record_read_of_node


class ListLinkedToModelingObj(ObjectLinkedToModelingObjBase, list, metaclass=AfterInitMeta):
    """List that can be linked to a ModelingObject. Uses ObjectLinkedToModelingObjBase (not slotted)."""

    def __init__(self, values=None):
        super().__init__()
        self.trigger_modeling_updates = False
        if values is not None:
            self.extend(values)

    def after_init(self):
        self.trigger_modeling_updates = True

    @staticmethod
    def check_value_type(value):
        if not isinstance(value, ModelingObject):
            raise ValueError(
                f"ListLinkedToModelingObjs only accept ModelingObjects as values, received {type(value)}")

    def _record_read(self):
        if self.modeling_obj_container is not None:
            record_read_of_node(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def __iter__(self):
        self._record_read()
        return super().__iter__()

    def __getitem__(self, index):
        self._record_read()
        return super().__getitem__(index)

    def __len__(self):
        self._record_read()
        return super().__len__()

    def __contains__(self, value):
        self._record_read()
        return super().__contains__(value)

    def count(self, value):
        self._record_read()
        return super().count(value)

    def index(self, *args):
        self._record_read()
        return super().index(*args)

    # Concatenation happens at C level on list subclasses (e.g. sum(list_of_lists, start=[])) and
    # would bypass the read hooks; both orientations return plain lists, as before.
    def __add__(self, other):
        self._record_read()
        return list(self) + list(other)

    def __radd__(self, other):
        self._record_read()
        return list(other) + list(self)

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)
        for value in list.__iter__(self):
            value.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    @staticmethod
    def _wrapped_value(value):
        ListLinkedToModelingObj.check_value_type(value)
        return ContextualModelingObjectAttribute(value)

    def _set_entry_passively(self, index: int | slice, value):
        """Replace stored relationships with complete link bookkeeping and no ModelingUpdate."""
        if isinstance(index, slice):
            values = list(value)
            previous_values = list.__getitem__(self, index)
            if index.step not in (None, 1) and len(values) != len(previous_values):
                raise ValueError(
                    f"attempt to assign sequence of size {len(values)} to extended slice of size "
                    f"{len(previous_values)}")
            for item in values:
                self.check_value_type(item)
            values_to_set = [ContextualModelingObjectAttribute(item) for item in values]
            for previous_value in previous_values:
                previous_value.set_modeling_obj_container(None, None)
            list.__setitem__(self, index, values_to_set)
            for value_to_set in values_to_set:
                value_to_set.set_modeling_obj_container(
                    self.modeling_obj_container, self.attr_name_in_mod_obj_container)
            return

        value_to_set = self._wrapped_value(value)
        list.__getitem__(self, index).set_modeling_obj_container(None, None)
        list.__setitem__(self, index, value_to_set)
        value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def _insert_passively(self, index: int, value: ModelingObject):
        """Insert one stored relationship with complete link bookkeeping and no ModelingUpdate."""
        value_to_set = self._wrapped_value(value)
        list.insert(self, index, value_to_set)
        value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def _extend_passively(self, values):
        """Append relationships in order with complete link bookkeeping and no ModelingUpdate."""
        values = list(values)
        for value in values:
            self.check_value_type(value)
        values_to_set = [ContextualModelingObjectAttribute(value) for value in values]
        list.extend(self, values_to_set)
        for value_to_set in values_to_set:
            value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def _drop_entry_passively(self, index: int | slice = -1):
        """Remove stored relationships with complete bookkeeping and no ModelingUpdate."""
        if isinstance(index, slice):
            values = list.__getitem__(self, index)
            for value in values:
                value.set_modeling_obj_container(None, None)
            list.__delitem__(self, index)
            return values
        value = list.pop(self, index)
        value.set_modeling_obj_container(None, None)
        return value

    def _clear_passively(self):
        """Remove every stored relationship with complete bookkeeping and no ModelingUpdate."""
        for value in list.__iter__(self):
            value.set_modeling_obj_container(None, None)
        list.clear(self)

    def __setitem__(self, index: int | slice, value):
        if isinstance(index, slice):
            value = list(value)
            for item in value:
                self.check_value_type(item)
        else:
            self.check_value_type(value)
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            copied_list[index] = value
            ModelingUpdate([[self, copied_list]])
            return

        self._set_entry_passively(index, value)

    def append(self, value: ModelingObject):
        self.check_value_type(value)
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            copied_list.append(value)
            ModelingUpdate([[self, copied_list]])
            return

        self._insert_passively(list.__len__(self), value)

    def to_json(self, with_formula=False):
        return [elt.id for elt in self]

    def __repr__(self):
        return str(self.to_json())

    def __str__(self):
        return_str = "[\n"

        for item in self:
            return_str += f"{item}, \n"

        return_str = return_str + "]"

        return return_str

    def insert(self, index: int, value: ModelingObject):
        self.check_value_type(value)
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            copied_list.insert(index, value)
            ModelingUpdate([[self, copied_list]])
            return

        self._insert_passively(index, value)

    def extend(self, values) -> None:
        values = list(values)
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            copied_list.extend(values)
            ModelingUpdate([[self, copied_list]])
            return

        self._extend_passively(values)

    def pop(self, index: int = -1):
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            value = copied_list.pop(index)
            ModelingUpdate([[self, copied_list]])
            return value

        return self._drop_entry_passively(index)

    def remove(self, value: ContextualModelingObjectAttribute):
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            copied_list.remove(value)
            ModelingUpdate([[self, copied_list]])
            return

        self._drop_entry_passively(list.index(self, value))

    def clear(self):
        if self.trigger_modeling_updates:
            ModelingUpdate([[self, []]])
            return

        self._clear_passively()

    def reverse(self):
        reversed_values = list(reversed(list(list.__iter__(self))))
        if self.trigger_modeling_updates:
            ModelingUpdate([[self, reversed_values]])
            return
        list.__setitem__(self, slice(None), reversed_values)

    def sort(self, *args, **kwargs):
        sorted_values = list(list.__iter__(self))
        sorted_values.sort(*args, **kwargs)
        if self.trigger_modeling_updates:
            ModelingUpdate([[self, sorted_values]])
            return
        list.__setitem__(self, slice(None), sorted_values)

    def __delitem__(self, index: int):
        if self.trigger_modeling_updates:
            copied_list = list(list.__iter__(self))
            del copied_list[index]
            ModelingUpdate([[self, copied_list]])
            return

        self._drop_entry_passively(index)

    def __iadd__(self, values):
        values = list(values)
        if self.trigger_modeling_updates:
            modeling_obj_container = self.modeling_obj_container
            attr_name = self.attr_name_in_mod_obj_container
            self.extend(values)
            return modeling_obj_container.__dict__[attr_name]
        self._extend_passively(values)
        return self

    def __imul__(self, n: int):
        if self.trigger_modeling_updates:
            modeling_obj_container = self.modeling_obj_container
            attr_name = self.attr_name_in_mod_obj_container
            copied_list = list(list.__iter__(self))
            copied_list *= n
            ModelingUpdate([[self, copied_list]])
            return modeling_obj_container.__dict__[attr_name]

        if n <= 0:
            self._clear_passively()
        elif n > 1:
            initial_values = list(list.__iter__(self))
            for _ in range(n - 1):
                self._extend_passively(initial_values)

        return self

    def __copy__(self):
        copied_list = type(self)(list(list.__iter__(self)))
        copied_list.trigger_modeling_updates = self.trigger_modeling_updates
        return copied_list
