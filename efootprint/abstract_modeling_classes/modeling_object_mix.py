from typing import Dict

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class ModelingObjectMix(ObjectLinkedToModelingObj, dict, metaclass=ABCAfterInitMeta):
    def __init__(self, modeling_object_mix: Dict[ModelingObject, float | SourceValue]):
        super().__init__()
        self.allow_updates = True
        self.object_type = None
        for key, value in modeling_object_mix.items():
            self[key] = value

        if abs(sum(list(self.values())).value.to(u.dimensionless).magnitude - 1) > 1e-6:
            raise PermissionError(
                f"The sum of the weights should be equal to 1, computed sum: {sum(list(self.values()))}")

    def after_init(self):
        self.allow_updates = False

    def compute_weighted_attr_sum(self, attr_name: str):
        weighted_sum = EmptyExplainableObject()
        for modeling_obj, modeling_obj_weight in self.items():
            weighted_sum += getattr(modeling_obj, attr_name) * modeling_obj_weight

        return weighted_sum.set_label(
            f"Weighted sum of {attr_name} over {[modeling_obj.id for modeling_obj in self.keys()]}")

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)

        for key, value in self.items():
            key.set_modeling_obj_container(new_parent_modeling_object, attr_name)
            value.set_modeling_obj_container(new_parent_modeling_object, attr_name)

    def __setitem__(self, key, value: SourceValue):
        if self.allow_updates:
            assert isinstance(key, ModelingObject)
            if self.object_type is not None:
                assert key.class_as_simple_str == self.object_type
            else:
                self.object_type = key.class_as_simple_str
            contextual_modeling_object_attribute_key = ContextualModelingObjectAttribute(
                key, self.modeling_obj_container, self.attr_name_in_mod_obj_container)

            assert isinstance(value, float) or isinstance(value, int) or isinstance(value, ExplainableObject)
            value_to_set = value
            if isinstance(value, ExplainableObject):
                assert value.value.check("[]")
            else:
                value_to_set = SourceValue(value * u.dimensionless)

            super().__setitem__(contextual_modeling_object_attribute_key, value_to_set)
            value_to_set.set_modeling_obj_container(
                new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)
        else:
            raise PermissionError("ModelingObjectMix is not allowed to be updated")
                
    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {}

        for key, value in self.items():
            output_dict[key.id] = value.to_json(with_calculated_attributes_data)

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        return_str = "{\n"

        for key, value in self.items():
            return_str += f"{key.id}: {value}, \n"

        return_str = return_str + "}"

        return return_str

    def __delitem__(self, key):
        raise PermissionError("ModelingObjectMix is not allowed to be updated")

    def pop(self, key):
        raise PermissionError("ModelingObjectMix is not allowed to be updated")

    def popitem(self):
        raise PermissionError("ModelingObjectMix is not allowed to be updated")

    def clear(self):
        raise PermissionError("ModelingObjectMix is not allowed to be updated")
        
    def update(self, __m, **kwargs):
        raise PermissionError("ModelingObjectMix is not allowed to be updated")

    def copy(self):
        raise NotImplementedError("ModelingObjectMix cannot be copied")

    def __eq__(self, other):
        return id(self) == id(other)
