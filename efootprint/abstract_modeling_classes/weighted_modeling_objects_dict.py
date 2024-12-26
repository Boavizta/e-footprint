from typing import Dict

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ABCAfterInitMeta
from efootprint.abstract_modeling_classes.recomputation_utils import launch_update_function_chain
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class WeightedModelingObjectsDict(ObjectLinkedToModelingObj, dict, metaclass=ABCAfterInitMeta):
    def __init__(self, weighted_modeling_objects_dict: Dict[ModelingObject, float | SourceValue]):
        super().__init__()
        self.handle_recomputations_in_setitem = False
        self.object_type = None
        for key, value in weighted_modeling_objects_dict.items():
            self[key] = value

    def after_init(self):
        self.handle_recomputations_in_setitem = True

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
            value.dict_container = self
            value.key_in_dict = key

    def __setitem__(self, key, value: SourceValue):
        assert isinstance(key, ModelingObject)
        if self.object_type is None:
            assert type(key) == self.object_type
        else:
            self.object_type = type(key)
        contextual_modeling_object_attribute_key = ContextualModelingObjectAttribute(key, None, None)
        assert isinstance(value, float) or isinstance(value, SourceValue)
        value_to_set = value
        if isinstance(value, SourceValue):
            assert value.value.check("[]")
        else:
            value_to_set = SourceValue(value * u.dimensionless)

        old_value = None
        if key in self.keys():
            old_value = self[key]
            old_value.set_modeling_obj_container(None, None)
        old_keys = list(self.keys())
        super().__setitem__(contextual_modeling_object_attribute_key, value_to_set)

        value_to_set.set_modeling_obj_container(
            new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)
        value_to_set.dict_container = self
        value_to_set.key_in_dict = key

        if self.handle_recomputations_in_setitem:
            if old_value is not None:
                assert self.modeling_obj_container is not None
                self.modeling_obj_container.register_footprint_values_in_systems_before_change(
                    f"{self.modeling_obj_container.name}’s {self.attr_name_in_mod_obj_container} had a weight change "
                    f"for {key.id}, from {str(old_value)} to {str(value_to_set)}")
                launch_update_function_chain(old_value.update_function_chain)
            else:
                self.handle_keys_update(old_keys)
                
    def handle_keys_update(self, old_keys):
        added_key_ids = [key.id for key in self.keys() if key not in old_keys]
        removed_key_ids = [key.id for key in old_keys if key not in self.keys()]
        self.modeling_obj_container.register_footprint_values_in_systems_before_change(
            f"{added_key_ids} added and {removed_key_ids} removed in {self.modeling_obj_container.name}’s "
            f"{self.attr_name_in_mod_obj_container}")
        self.modeling_obj_container.handle_object_list_link_update(list(self.keys()), old_keys)
        
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
        super().__delitem__(key)
        key.remove_obj_from_modeling_obj_containers(self.modeling_obj_container)


    def pop(self, key):
        old_keys = list(self.keys())
        value = super().pop(key)
        value.set_modeling_obj_container(None, None)
        key.remove_obj_from_modeling_obj_containers(self.modeling_obj_container)
        self.handle_keys_update(old_keys)
        
        return value

    def popitem(self):
        old_keys = list(self.keys())
        key, value = super().popitem()
        value.set_modeling_obj_container(None, None)
        key.remove_obj_from_modeling_obj_containers(self.modeling_obj_container)
        self.handle_keys_update(old_keys)
        
        return key, value

    def clear(self):
        old_keys = list(self.keys())
        for key, value in self.items():
            value.set_modeling_obj_container(None, None)
            key.remove_obj_from_modeling_obj_containers(self.modeling_obj_container)
        super().clear()
        self.handle_keys_update(old_keys)
        
    def update(self, __m, **kwargs):
        self.handle_recomputations_in_setitem = False
        old_keys = list(self.keys())
        updated_keys = ([key for key in __m.keys() if key in self.keys()] +
                        [key for key in kwargs.keys() if key in self.keys()])
        updated_keys_attr_updates_chain = sum([self[key].attr_updates_chain for key in updated_keys], [])
        # TODO: finish recomputing logic. But maybe better to extend Simulation to do the job ?
        super().update(__m, **kwargs)
        self.handle_recomputations_in_setitem = True


    def copy(self):
        raise NotImplementedError("WeightedModelingObjectsDict cannot be copied")

    def fromkeys(cls, __iterable, __value = None):
        dict_from_keys = dict.fromkeys(__iterable, __value)

        return WeightedModelingObjectsDict(dict_from_keys)

    def __eq__(self, other):
        raise NotImplementedError("WeightedModelingObjectsDict cannot be compared for equality")
