from typing import Type


class ObjectLinkedToModelingObj:
    def __init__(self):
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None
        self.dict_container = None
        self.key_in_dict = None

    def set_modeling_obj_container(self, new_parent_modeling_object: Type["ModelingObject"], attr_name: str):
        if (self.modeling_obj_container is not None and new_parent_modeling_object is not None and
                new_parent_modeling_object.id != self.modeling_obj_container.id):
            raise ValueError(
                f"A {self.__class__.__name__} can’t be attributed to more than one ModelingObject. Here "
                f"{self} is trying to be linked to {new_parent_modeling_object.name} but is already linked to "
                f"{self.modeling_obj_container.name}.")
        self.modeling_obj_container = new_parent_modeling_object
        self.attr_name_in_mod_obj_container = attr_name

    @property
    def id(self):
        if self.modeling_obj_container is None:
            raise ValueError(
                f"{self} doesn’t have a modeling_obj_container, hence it makes no sense "
                f"to look for its ancestors")

        return f"{self.attr_name_in_mod_obj_container}-in-{self.modeling_obj_container.id}"

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        assert type(new_value) == type(self), f"Trying to replace {self} by {new_value} which is of different type."
        mod_obj_container = self.modeling_obj_container
        attr_name = self.attr_name_in_mod_obj_container
        if self.dict_container is None:
            mod_obj_container.__dict__[attr_name] = new_value
        else:
            if self.key_in_dict not in self.dict_container.keys():
                raise KeyError(f"object of id {self.key_in_dict.id} not found as key in {attr_name} attribute of "
                               f"{mod_obj_container.id} when trying to replace {self} by {new_value}. "
                               f"This should not happen.")
            self.dict_container[self.key_in_dict] = new_value
            new_value.dict_container = self.dict_container
            new_value.key_in_dict = self.key_in_dict
        self.set_modeling_obj_container(None, None)
        new_value.set_modeling_obj_container(mod_obj_container, attr_name)
