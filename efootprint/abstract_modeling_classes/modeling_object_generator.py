import inspect
from abc import ABC, abstractmethod
from copy import copy

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj


class ModelingObjectGenerator(ModelingObject, ABC):
    _default_values = {}

    @classmethod
    def default_values(cls):
        return {key: copy(value) for key, value in cls._default_values.items()}

    @classmethod
    def default_value(cls, attr_name):
        return copy(cls._default_values[attr_name])

    @classmethod
    @abstractmethod
    def list_values(cls):
        pass

    @classmethod
    @abstractmethod
    def conditional_list_values(cls):
        pass

    def __init__(self, name):
        super().__init__(name=name)
        self.generated_objects = GeneratedObjectDict()

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["generated_objects"]

    def __getattribute__(self, attr_name):
        attribute = super().__getattribute__(attr_name)
        object_to_return = attribute

        if not isinstance(attribute, ObjectLinkedToModelingObj) and callable(attribute):
            def wrapper(*args, **kwargs):
                if attr_name.startswith("generate_"):
                    sig = inspect.signature(attribute)
                    param_names = list(sig.parameters.keys())

                    for i, arg in enumerate(args):
                        param_name = param_names[i] if i < len(param_names) else f"arg_{i}"
                        if isinstance(arg, str):
                            self.check_belonging_to_authorized_values(param_name, arg)
                    for key, value in kwargs.items():
                        if isinstance(value, str):
                            self.check_belonging_to_authorized_values(key, value)

                    result = attribute(*args, **kwargs)  # Call the original method
                    self.generated_objects[result] = [attr_name, args, kwargs]
                    result.generated_by = self
                else:
                    result = attribute(*args, **kwargs)
                    assert not isinstance(result, ModelingObject), \
                        f"Method {attr_name} should start with 'generate_' because it returns a ModelingObject"

                return result

            object_to_return = wrapper

        return object_to_return


class GeneratedObjectDict(dict):
    def to_json(self, save_calculated_attributes=False):
        output_dict = {}
        for generated_object in self.keys():
            output_dict[generated_object.id] = {
                "attr_name": self[generated_object][0],
                "args": [elt.to_json() if not isinstance(elt, str) else elt for elt in self[generated_object][1]],
                "kwargs": {key: value.to_json() for key, value in self[generated_object][2].items()}
            }

        return output_dict
