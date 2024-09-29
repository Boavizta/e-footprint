from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ObjectLinkedToModelingObj, ExplainableObject)

from typing import Type
import json

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject


class DictLinkedToModelingObj(ObjectLinkedToModelingObj, dict):
    def __init__(self):
        super().__init__()
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None

    def set_modeling_obj_container(self, new_parent_modeling_object: Type["ModelingObject"], attr_name: str):
        if self.modeling_obj_container is not None and new_parent_modeling_object.id != self.modeling_obj_container.id:
            raise ValueError(
                f"A DictLinkedToModelingObj can’t be attributed to more than one ModelingObject. Here "
                f"{self.label} is trying to be linked to {new_parent_modeling_object.name} but is already linked to "
                f"{self.modeling_obj_container.name}.")
        self.modeling_obj_container = new_parent_modeling_object
        self.attr_name_in_mod_obj_container = attr_name

    def __setitem__(self, key, value: ExplainableObject):
        if not isinstance(value, ExplainableObject) and not isinstance(value, EmptyExplainableObject):
            raise ValueError(
                f"DictLinkedToModelingObjs only accept ExplainableObjects or EmptyExplainableObject as values, "
                f"received {type(value)}")
        super().__setitem__(key, value)
        value.set_modeling_obj_container(
                new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {}

        for key, value in self.items():
            output_dict[key.id] = value.to_json(with_calculated_attributes_data)

        return output_dict

    def __repr__(self):
        return json.dumps(self.to_json())

    def __str__(self):
        return_str = "{\n"

        for key, value in self.items():
            return_str += f"{key.id}: {value}, \n"

        return_str = return_str + "}"

        return return_str
