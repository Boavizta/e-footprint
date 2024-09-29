from typing import Type
import json

from efootprint.abstract_modeling_classes.explainable_objects import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ListLinkedToModelingObj(ObjectLinkedToModelingObj, list):
    def __init__(self, values=None):
        super().__init__()
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None
        self.previous_values = None
        if values is not None:
            self.extend([value for value in values])
    
    @staticmethod
    def check_value_type(value):
        if not isinstance(value, ModelingObject):
            raise ValueError(
                f"ListLinkedToModelingObjs only accept ModelingObjects as values, received {type(value)}")

    def set_modeling_obj_container(self, new_parent_modeling_object: Type["ModelingObject"], attr_name: str):
        if self.modeling_obj_container is not None and new_parent_modeling_object.id != self.modeling_obj_container.id:
            raise ValueError(
                f"A ListLinkedToModelingObj can’t be attributed to more than one ModelingObject. Here "
                f"{self.label} is trying to be linked to {new_parent_modeling_object.name} but is already linked to "
                f"{self.modeling_obj_container.name}.")
        self.modeling_obj_container = new_parent_modeling_object
        self.attr_name_in_mod_obj_container = attr_name

        for value in self:
            value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)

    def register_previous_values(self):
        self.previous_values = [value for value in self]

    def __setitem__(self, index: int, value: ModelingObject):
        self.check_value_type(value)
        super().__setitem__(index, value)
        value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)

    def append(self, value: ModelingObject):
        self.check_value_type(value)
        super().append(value)
        value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)

    def to_json(self, with_calculated_attributes_data=False):
        output_list = []

        for item in self:
            output_list.append(item.to_json(with_calculated_attributes_data))

        return output_list

    def __repr__(self):
        return json.dumps(self.to_json())

    def __str__(self):
        return_str = "[\n"

        for item in self:
            return_str += f"{item}, \n"

        return_str = return_str + "]"

        return return_str

    def insert(self, index: int, value: ModelingObject):
        self.check_value_type(value)
        super().insert(index, value)
        value.add_obj_to_modeling_obj_containers(new_obj=self.modeling_obj_container)

    def extend(self, values) -> None:
        for value in values:
            self.append(value)

    def pop(self, index: int = -1):
        value = super().pop(index)
        value.set_modeling_obj_container(None, None)

        return value

    def remove(self, value: ModelingObject):
        super().remove(value)
        value.set_modeling_obj_container(None, None)

    def clear(self):
        for item in self:
            item.set_modeling_obj_container(None, None)
        super().clear()

    def __delitem__(self, index: int):
        value = self[index]
        value.set_modeling_obj_container(None, None)
        super().__delitem__(index)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n: int):
        for _ in range(n - 1):
            self.extend(self.copy())  # This creates n duplicates of the list
        return self

    def __copy__(self):
        return ListLinkedToModelingObj([value for value in self])
