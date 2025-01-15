from copy import copy

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, AfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate


class ListLinkedToModelingObj(ObjectLinkedToModelingObj, list, metaclass=AfterInitMeta):
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

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)
        for value in self:
            value.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def __setitem__(self, index: int, value: ModelingObject):
        self.check_value_type(value)
        if self.trigger_modeling_updates:
            copied_list = list(self)
            copied_list[index] = value
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        value_to_set = ContextualModelingObjectAttribute(value)
        super().__setitem__(index, value_to_set)
        value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def append(self, value: ModelingObject):
        self.check_value_type(value)
        if self.trigger_modeling_updates:
            copied_list = list(self)
            copied_list.append(value)
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        value_to_set = ContextualModelingObjectAttribute(value)
        super().append(value_to_set)
        value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def to_json(self, with_calculated_attributes_data=False):
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
            copied_list = list(self)
            copied_list.insert(index, value)
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        value_to_set = ContextualModelingObjectAttribute(value)
        super().insert(index, value_to_set)
        value_to_set.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

    def extend(self, values) -> None:
        if self.trigger_modeling_updates:
            copied_list = list(self)
            copied_list.extend(values)
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        initial_trigger_modeling_updates = copy(self.trigger_modeling_updates)
        self.trigger_modeling_updates = False
        for value in values:
            self.append(value)
        self.trigger_modeling_updates = initial_trigger_modeling_updates

    def pop(self, index: int = -1):
        if self.trigger_modeling_updates:
            copied_list = list(self)
            _ = copied_list.pop(index)
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        value = super().pop(index)
        value.set_modeling_obj_container(None, None)

        return value

    def remove(self, value: ContextualModelingObjectAttribute):
        if self.trigger_modeling_updates:
            copied_list = list(self)
            copied_list.remove(value)
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        super().remove(value)
        value.set_modeling_obj_container(None, None)

    def clear(self):
        if self.trigger_modeling_updates:
            ModelingUpdate([[self.return_copy_with_same_attributes(), []]])
            self.set_modeling_obj_container(None, None)

        for value in self:
            value.set_modeling_obj_container(None, None)
        super().clear()

    def __delitem__(self, index: int):
        if self.trigger_modeling_updates:
            copied_list = list(self)
            del copied_list[index]
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        value = self[index]
        value.set_modeling_obj_container(None, None)
        super().__delitem__(index)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n: int):
        if self.trigger_modeling_updates:
            copied_list = list(self)
            copied_list *= n
            ModelingUpdate([[self.return_copy_with_same_attributes(), copied_list]])
            self.set_modeling_obj_container(None, None)

        initial_trigger_modeling_updates = copy(self.trigger_modeling_updates)
        self.trigger_modeling_updates = False
        for _ in range(n - 1):
            self.extend(self.copy())
        self.trigger_modeling_updates = initial_trigger_modeling_updates

        return self

    def __copy__(self):
        return ListLinkedToModelingObj([value for value in self])

    def return_copy_with_same_attributes(self):
        copied_list = ListLinkedToModelingObj(self)
        copied_list.set_modeling_obj_container(self.modeling_obj_container, self.attr_name_in_mod_obj_container)
        copied_list.trigger_modeling_updates = self.trigger_modeling_updates
        
        return copied_list
    