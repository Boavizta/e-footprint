from typing import Dict

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class WeightedModelingObjectsDict(ObjectLinkedToModelingObj, dict, metaclass=ABCAfterInitMeta):
    def __init__(self, weighted_modeling_objects_dict: Dict[ModelingObject, float | SourceValue]):
        super().__init__()
        self.trigger_modeling_updates = False
        self.object_type = None
        for key, value in weighted_modeling_objects_dict.items():
            self[key] = value

    def after_init(self):
        self.trigger_modeling_updates = True

    def compute_weighted_attr_sum(self, attr_name: str):
        weighted_sum = EmptyExplainableObject()
        for modeling_obj, modeling_obj_weight in self.items():
            weighted_sum += getattr(modeling_obj, attr_name) * modeling_obj_weight

        return weighted_sum.set_label(
            f"Weighted sum of {attr_name} over {[modeling_obj.id for modeling_obj in self]}")

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)

        for key, value in self.items():
            key.set_modeling_obj_container(new_parent_modeling_object, attr_name)
            value.set_modeling_obj_container(new_parent_modeling_object, attr_name)

    def __setitem__(self, key, value: SourceValue):
        assert isinstance(key, ModelingObject)
        if self.object_type is None:
            assert type(key) == self.object_type
        else:
            self.object_type = type(key)
        contextual_modeling_object_attribute_key = ContextualModelingObjectAttribute(
            key, self.modeling_obj_container, self.attr_name_in_mod_obj_container)

        assert isinstance(value, float) or isinstance(value, SourceValue)
        value_to_set = value
        if isinstance(value, SourceValue):
            assert value.value.check("[]")
        else:
            value_to_set = SourceValue(value * u.dimensionless)

        if not self.trigger_modeling_updates:
            super().__setitem__(contextual_modeling_object_attribute_key, value_to_set)
            value_to_set.set_modeling_obj_container(
                new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)
        else:
            if key in self:
                ModelingUpdate([[self[key], value_to_set]])
            else:
                copied_dict = dict(self)
                copied_dict[contextual_modeling_object_attribute_key] = value_to_set
                ModelingUpdate([[self, copied_dict]])
                
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

    def __delitem__(self, key):
        self[key].set_modeling_obj_container(None, None)
        if self.trigger_modeling_updates:
            copied_dict = dict(self)
            copied_dict.__delitem__(key)
            ModelingUpdate([[self, copied_dict]])
        else:
            super().__delitem__(key)

    def pop(self, key):
        if self.trigger_modeling_updates:
            copied_dict = dict(self)
            value = copied_dict.pop(key)
            ModelingUpdate([[self, copied_dict]])
        else:
            value = super().pop(key)

        value.set_modeling_obj_container(None, None)
        
        return value

    def popitem(self):
        if self.trigger_modeling_updates:
            copied_dict = dict(self)
            key, value = copied_dict.popitem()
            ModelingUpdate([[self, copied_dict]])
        else:
            key, value = super().popitem()

        value.set_modeling_obj_container(None, None)
        
        return key, value

    def clear(self):
        for key, value in self.items():
            value.set_modeling_obj_container(None, None)
        
        if self.trigger_modeling_updates:
            ModelingUpdate([[self, {}]])
        else:
            super().clear()
        
    def update(self, __m, **kwargs):
        if self.trigger_modeling_updates:
            copied_dict = dict(self)
            copied_dict.update(__m, **kwargs)
            # TODO: move this to ModelingUpdate
            value_updates = []
            new_dict_part = __m.update(kwargs)
            for key, value in new_dict_part.items():
                if key in self:
                    value_updates.append((self[key], value))
            ModelingUpdate(value_updates + [(self, copied_dict)])
        else:
            super().update(__m, **kwargs)

    def copy(self):
        raise NotImplementedError("WeightedModelingObjectsDict cannot be copied")

    def fromkeys(cls, __iterable, __value = None):
        dict_from_keys = dict.fromkeys(__iterable, __value)

        return WeightedModelingObjectsDict(dict_from_keys)

    def __eq__(self, other):
        raise NotImplementedError("WeightedModelingObjectsDict cannot be compared for equality")
