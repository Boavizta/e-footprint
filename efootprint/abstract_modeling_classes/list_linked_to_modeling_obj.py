from typing import Type

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate


class ListLinkedToModelingObj(ObjectLinkedToModelingObj, list, metaclass=ABCAfterInitMeta):
    def __init__(self, values=None):
        super().__init__()
        self.trigger_modeling_updates = False
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None
        self.previous_values = None
        if values is not None:
            self.extend([value for value in values])

    def after_init(self):
        self.trigger_modeling_updates = True
    
    @staticmethod
    def check_value_type(value):
        if not isinstance(value, ModelingObject):
            raise ValueError(
                f"ListLinkedToModelingObjs only accept ModelingObjects as values, received {type(value)}")

    def set_modeling_obj_container(self, new_parent_modeling_object: Type["ModelingObject"], attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)

        for value in self:
            value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        value_to_set = new_value
        if not isinstance(value_to_set, ListLinkedToModelingObj):
            value_to_set = ListLinkedToModelingObj(value_to_set)
        super().replace_in_mod_obj_container_without_recomputation(value_to_set)

    def __setitem__(self, index: int, value: ModelingObject):
        self.check_value_type(value)
        if not self.trigger_modeling_updates:
            super().__setitem__(index, value)
            value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)
        else:
            copied_list = list(self)
            copied_list[index] = value
            ModelingUpdate([(self, copied_list)])

    def append(self, value: ModelingObject):
        self.check_value_type(value)
        if not self.trigger_modeling_updates:
            super().append(value)
            value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)
        else:
            copied_list = list(self)
            copied_list.append(value)
            ModelingUpdate([(self, copied_list)])

    def to_json(self, with_calculated_attributes_data=False):
        output_list = []

        for item in self:
            output_list.append(item.to_json(with_calculated_attributes_data))

        return output_list

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
        if not self.trigger_modeling_updates:
            super().insert(index, value)
            value.add_obj_to_modeling_obj_containers(self.modeling_obj_container)
        else:
            copied_list = list(self)
            copied_list.insert(index, value)
            ModelingUpdate([(self, copied_list)])

    def extend(self, values) -> None:
        if not self.trigger_modeling_updates:
            for value in values:
                self.append(value)
        else:
            copied_list = list(self)
            copied_list.extend(values)
            ModelingUpdate([(self, copied_list)])

    def pop(self, index: int = -1):
        if not self.trigger_modeling_updates:
            value = super().pop(index)
            value.set_modeling_obj_container(None, None)
        else:
            copied_list = list(self)
            value = copied_list.pop(index)
            ModelingUpdate([(self, copied_list)])

        return value

    def remove(self, value: ContextualModelingObjectAttribute):
        if not self.trigger_modeling_updates:
            super().remove(value)
            value.set_modeling_obj_container(None, None)
        else:
            copied_list = list(self)
            copied_list.remove(value)
            ModelingUpdate([(self, copied_list)])

    def clear(self):
        if not self.trigger_modeling_updates:
            for item in self:
                item.set_modeling_obj_container(None, None)
            super().clear()
        else:
            ModelingUpdate([(self, [])])

    def __delitem__(self, index: int):
        if not self.trigger_modeling_updates:
            value = self[index]
            value.set_modeling_obj_container(None, None)
            super().__delitem__(index)
        else:
            copied_list = list(self)
            del copied_list[index]
            ModelingUpdate([(self, copied_list)])

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n: int):
        if not self.trigger_modeling_updates:
            for _ in range(n - 1):
                self.extend(self.copy())
        else:
            copied_list = list(self)
            copied_list *= n
            ModelingUpdate([(self, copied_list)])

        return self

    def __copy__(self):
        return ListLinkedToModelingObj([value for value in self])
