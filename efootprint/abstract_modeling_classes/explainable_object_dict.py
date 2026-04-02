from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    ExplainableObject, retrieve_update_function_from_mod_obj_and_attr_name)
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


class ExplainableObjectDict(ObjectLinkedToModelingObjBase, dict):
    """Dict that can be linked to a ModelingObject. Uses ObjectLinkedToModelingObjBase (not slotted)."""

    def __init__(self, input_dict=None):
        super().__init__()
        self.trigger_modeling_updates = False
        if input_dict is not None:
            for key, value in input_dict.items():
                self[key] = value

    def set_modeling_obj_container(self, new_parent_modeling_object: ModelingObject, attr_name: str):
        super().set_modeling_obj_container(new_parent_modeling_object, attr_name)
        for value in self.values():
            value.set_modeling_obj_container(new_parent_modeling_object, attr_name)
        if new_parent_modeling_object is None:
            for key in self:
                self._remove_self_from_key_containers(key)
        else:
            for key in self:
                self._add_self_to_key_containers(key)

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

    def update(self, __m=None, **kwargs):
        if __m is not None:
            for key, value in (__m.items() if hasattr(__m, 'items') else __m):
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value: ExplainableObject):
        if not isinstance(value, ExplainableObject) and not isinstance(value, EmptyExplainableObject):
            raise ValueError(
                f"ExplainableObjectDicts only accept ExplainableObjects or EmptyExplainableObject as values, "
                f"received {type(value)}")

        if self.trigger_modeling_updates:
            if key in self:
                # Value update on existing key: old value's attr_updates_chain already traces downstream
                from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
                ModelingUpdate([[self[key], value]])
            else:
                # Structural change: new key — full dict replacement so compute chain can diff keys
                from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
                new_dict = ExplainableObjectDict()
                for k, v in self.items():
                    dict.__setitem__(new_dict, k, v)
                dict.__setitem__(new_dict, key, value)
                new_dict.trigger_modeling_updates = self.trigger_modeling_updates
                ModelingUpdate([[self, new_dict]])
            return

        # Original passive logic (unchanged)
        if key in self and self.modeling_obj_container is not None:
            self[key].set_modeling_obj_container(None, None)
        super().__setitem__(key, value)
        if self.modeling_obj_container is not None:
            value.set_modeling_obj_container(
                new_modeling_obj_container=self.modeling_obj_container, attr_name=self.attr_name_in_mod_obj_container)
        self._add_self_to_key_containers(key)

    def __delitem__(self, key):
        if self.trigger_modeling_updates:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            new_dict = ExplainableObjectDict()
            for k, v in self.items():
                if k != key:
                    dict.__setitem__(new_dict, k, v)
            new_dict.trigger_modeling_updates = self.trigger_modeling_updates
            ModelingUpdate([[self, new_dict]])
            return

        # Original passive logic (unchanged)
        if self.modeling_obj_container is not None:
            self[key].set_modeling_obj_container(None, None)
        super().__delitem__(key)
        self._remove_self_from_key_containers(key)

    def pop(self, key, *args):
        if self.trigger_modeling_updates and key in self:
            value = self[key]
            self.__delitem__(key)
            return value
        if key in self:
            value = self[key]
            self.__delitem__(key)
            return value
        if len(args) > 1:
            raise TypeError(f"pop expected at most 2 arguments, got {len(args) + 1}")
        if args:
            return args[0]
        raise KeyError(key)

    def popitem(self):
        key, value = super().popitem()
        if self.modeling_obj_container is not None:
            value.set_modeling_obj_container(None, None)
        self._remove_self_from_key_containers(key)
        return key, value

    def clear(self):
        for key in list(self.keys()):
            self.__delitem__(key)

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return self[key]

    def _add_self_to_key_containers(self, key):
        if (self.modeling_obj_container is not None and isinstance(key, ModelingObject)
                and id(self) not in [id(elt) for elt in key.explainable_object_dicts_containers]):
            key.explainable_object_dicts_containers.append(self)

    def _remove_self_from_key_containers(self, key):
        if not isinstance(key, ModelingObject):
            return
        key.explainable_object_dicts_containers = [elt for elt in key.explainable_object_dicts_containers
                                                   if id(elt) != id(self)]

    def to_json(self, save_calculated_attributes=False):
        output_dict = {}

        for key, value in self.items():
            if isinstance(key, ModelingObject):
                output_dict[key.id] = value.to_json(save_calculated_attributes)
            elif isinstance(key, str):
                output_dict[key] = value.to_json(save_calculated_attributes)
            else:
                raise ValueError(f"Key {key} is not a ModelingObject or a string")

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        if len(self) == 0:
            return "{}"

        return_str = "{\n"

        for key, value in self.items():
            if isinstance(key, ModelingObject):
                return_str += f"{key.class_as_simple_str} {key.name} ({key.id}): {value}, \n"
            elif isinstance(key, str):
                return_str += f"{key}: {value}, \n"
            else:
                raise ValueError(f"Key {key} is not a ModelingObject or a string")

        return_str = return_str + "}"

        return return_str
