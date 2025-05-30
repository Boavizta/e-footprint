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
        elif self.dict_container is None:
            return f"{self.attr_name_in_mod_obj_container}-in-{self.modeling_obj_container.id}"
        else:
            return f"{self.attr_name_in_mod_obj_container}[{self.key_in_dict.id}]-in-{self.modeling_obj_container.id}"

    @property
    def attribute_id(self):
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
        dict_container = self.dict_container
        if dict_container is None:
            raise ValueError(f"{self} is not linked to a ModelingObject through a dictionary attribute.")
        else:
            output_key = None
            for key, value in dict_container.items():
                if id(value) == id(self):
                    if output_key is None:
                        output_key = key
                    else:
                        raise ValueError(f"Multiple keys found for {self} in {dict_container}.")

        return output_key

    @property
    def list_container(self):
        output = None
        if (
                not isinstance(self, list)
                and self.modeling_obj_container is not None
                and isinstance(getattr(self.modeling_obj_container, self.attr_name_in_mod_obj_container), list)
        ):
            output = getattr(self.modeling_obj_container, self.attr_name_in_mod_obj_container)

        return output

    @property
    def indexes_in_list(self):
        if self.list_container is None:
            raise ValueError(f"{self} is not linked to a ModelingObject through a list attribute.")
        else:
            output_indexes = []
            for index, value in enumerate(self.list_container):
                if id(value) == id(self):
                    output_indexes.append(index)

        return output_indexes

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        assert self.modeling_obj_container is not None, f"{self} is not linked to a ModelingObject."
        assert isinstance(new_value, ObjectLinkedToModelingObj), (
            f"Trying to replace {self} by {new_value} which is not an instance of "
            f"ObjectLinkedToModelingObj.")
        from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject

        if not isinstance(new_value, EmptyExplainableObject) and not isinstance(self, EmptyExplainableObject):
            assert isinstance(new_value, self.__class__) or isinstance(self, new_value.__class__), \
                f"Trying to replace {self} of type {type(self)} by {new_value} which is of type {type(new_value)}."
        mod_obj_container = self.modeling_obj_container
        attr_name = self.attr_name_in_mod_obj_container
        dict_container = self.dict_container
        if dict_container is not None:
            if self.key_in_dict not in dict_container:
                raise KeyError(f"object of id {self.key_in_dict.id} not found as key in {attr_name} attribute of "
                               f"{mod_obj_container.id} when trying to replace {self} by {new_value}. "
                               f"This should not happen.")
            dict_container[self.key_in_dict] = new_value
        elif self.list_container is not None:
            if not self.indexes_in_list:
                raise ValueError(f"object of id {self.id} not found in {attr_name} attribute of {mod_obj_container.id} "
                                 f"when trying to replace \n\n{self}\nby\n\n{new_value}.\n\nThis should not happen.")
            for index in self.indexes_in_list:
                initial_trigger_modeling_updates = self.list_container.trigger_modeling_updates
                self.list_container.trigger_modeling_updates = False
                self.list_container[index] = new_value
                self.list_container.trigger_modeling_updates = initial_trigger_modeling_updates
        else:
            self.set_modeling_obj_container(None, None)
            mod_obj_container.__dict__[attr_name] = new_value
            new_value.set_modeling_obj_container(mod_obj_container, attr_name)
