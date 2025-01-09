from abc import ABC

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate


class ModelingObjectGenerator(ModelingObject, ABC):
    def __init__(self, name):
        super().__init__(name=name)
        self.generated_objects = {}

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["generated_objects"]

    def __getattribute__(self, attr_name):
        attribute = super().__getattribute__(attr_name)
        object_to_return = attribute

        if callable(attribute):
            def wrapper(*args, **kwargs):
                result = attribute(*args, **kwargs)  # Call the original method
                if isinstance(result, ModelingObject):
                    assert attr_name.startswith("generate_"), \
                        f"Method {attr_name} should start with 'generate_' because it returns a ModelingObject"
                    self.generated_objects[result] = [attr_name, args, kwargs]
                    result.generated_by = self

                return result

            object_to_return = wrapper

        return object_to_return

    def __setattr__(self, name, input_value):
        super().__setattr__(name, input_value)
        if name not in self.attributes_that_shouldnt_trigger_update_logic:
            object_correspondances = []
            for old_object in list(self.generated_objects.keys()):
                method_name, args, kwargs = self.generated_objects[old_object]
                new_object = getattr(self, method_name)(*args, **kwargs)
                del self.generated_objects[old_object]
                object_correspondances.append((old_object, new_object))
            changes_list = []
            for old_object, new_object in object_correspondances:
                for contextual_mod_obj_container in old_object.contextual_modeling_obj_containers:
                    if contextual_mod_obj_container.modeling_obj_container:
                        changes_list.append([contextual_mod_obj_container, new_object])
            ModelingUpdate(changes_list)
