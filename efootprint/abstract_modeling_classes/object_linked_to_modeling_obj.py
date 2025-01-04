from typing import Type


class ObjectLinkedToModelingObj:
    def __init__(self):
        self.modeling_obj_container = None
        self.attr_name_in_mod_obj_container = None

    def set_modeling_obj_container(
            self, new_parent_modeling_object: Type["ModelingObject"] | None, attr_name: str | None):
        if new_parent_modeling_object is None or attr_name is None:
            assert new_parent_modeling_object == attr_name, (
                f"Both new_parent_modeling_object and attr_name should be None or not None. "
                f"Here new_parent_modeling_object is {new_parent_modeling_object} and attr_name is {attr_name}.")
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

    @property
    def dict_container(self):
        output = None
        if (
                self.modeling_obj_container is not None
                and isinstance(getattr(self.modeling_obj_container, self.attr_name_in_mod_obj_container), dict)
                and id(getattr(self.modeling_obj_container, self.attr_name_in_mod_obj_container)) != id(self)
        ):
            output = getattr(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

        return output

    @property
    def key_in_dict(self):
        if self.dict_container is None:
            raise ValueError(f"{self} is not linked to a ModelingObject through a dictionary attribute.")
        else:
            output_key = None
            for key, value in self.dict_container.items():
                if id(value) == id(self):
                    if output_key is None:
                        output_key = key
                    else:
                        raise ValueError(f"Multiple keys found for {self} in {self.dict_container}.")

        return output_key

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        assert self.modeling_obj_container is not None, f"{self} is not linked to a ModelingObject."
        assert isinstance(new_value, ObjectLinkedToModelingObj), (
            f"Trying to replace {self} by {new_value} which is not an instance of "
            f"ObjectLinkedToModelingObj.")
        from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject

        if not isinstance(new_value, EmptyExplainableObject) and not isinstance(self, EmptyExplainableObject):
            assert isinstance(new_value, self.__class__) or isinstance(self, new_value.__class__), \
                f"Trying to replace {self} by {new_value} which is of different type."
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
        self.set_modeling_obj_container(None, None)
        new_value.set_modeling_obj_container(mod_obj_container, attr_name)
