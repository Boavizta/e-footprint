from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, retrieve_update_function_from_mod_obj_and_attr_name)
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject


class ExplainableObjectDict(ObjectLinkedToModelingObj, dict):
    def __init__(self):
        super().__init__()

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)
        for value in self.values():
            value.set_modeling_obj_container(new_parent_modeling_object, attr_name)

    @property
    def all_ancestors_with_id(self):
        all_ancestors_with_id = []

        for value in self.values():
            all_ancestor_ids = [ancestor.id for ancestor in all_ancestors_with_id]
            for ancestor in value.all_ancestors_with_id:
                if ancestor.id not in all_ancestor_ids:
                    all_ancestors_with_id.append(ancestor)

        return all_ancestors_with_id

    @property
    def update_function(self):
        if self.modeling_obj_container is None:
            raise ValueError(
                f"{self} doesn’t have a modeling_obj_container, hence it makes no sense "
                f"to look for its update function")
        update_func = retrieve_update_function_from_mod_obj_and_attr_name(
            self.modeling_obj_container, self.attr_name_in_mod_obj_container)

        return update_func

    def __setitem__(self, key, value: ExplainableObject):
        if not isinstance(value, ExplainableObject) and not isinstance(value, EmptyExplainableObject):
            raise ValueError(
                f"ExplainableObjectDicts only accept ExplainableObjects or EmptyExplainableObject as values, "
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
        return str(self.to_json())

    def __str__(self):
        return_str = "{\n"

        for key, value in self.items():
            return_str += f"{key.id}: {value}, \n"

        return_str = return_str + "}"

        return return_str
