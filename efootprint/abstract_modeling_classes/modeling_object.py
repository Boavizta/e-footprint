import uuid
from abc import ABCMeta, abstractmethod
from inspect import signature
from typing import List, Type, get_origin, get_args
import os
import re

from IPython.display import HTML

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.logger import logger
from efootprint.abstract_modeling_classes.explainable_object_base_class import (
    retrieve_update_function_from_mod_obj_and_attr_name, ExplainableObject)
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.utils.graph_tools import WIDTH, HEIGHT, add_unique_id_to_mynetwork
from efootprint.utils.object_relationships_graphs import build_object_relationships_graph, \
    USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE


def get_instance_attributes(obj, target_class):
    return {attr_name: attr_value for attr_name, attr_value in obj.__dict__.items()
            if isinstance(attr_value, target_class)}


def check_type_homogeneity_within_list_or_set(input_list_or_set):
    type_set = [type(value) for value in input_list_or_set]
    base_type = type(type_set[0])

    if not all(isinstance(item, base_type) for item in type_set):
        raise ValueError(
            f"There shouldn't be objects of different types within the same list, found {type_set}")
    else:
        return type_set.pop()


class AfterInitMeta(type):
    def __call__(cls, *args, **kwargs):
        instance = super(AfterInitMeta, cls).__call__(*args, **kwargs)
        instance.after_init()

        return instance


class ABCAfterInitMeta(AfterInitMeta, ABCMeta):
    def __instancecheck__(cls, instance):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute
        # Allow an instance of ContextualModelingObjectAttribute to be considered as an instance of ModelingObject
        if isinstance(instance, ContextualModelingObjectAttribute):
            return AfterInitMeta.__instancecheck__(cls, instance._value)

        return AfterInitMeta.__instancecheck__(cls, instance)


def css_escape(input_string):
    """
    Escape a string to be used as a CSS identifier.
    """
    def escape_char(c):
        if re.match(r'[a-zA-Z0-9_-]', c):
            return c
        elif c == ' ':
            return '-'
        else:
            return f'{ord(c):x}'

    return ''.join(escape_char(c) for c in input_string)


def optimize_mod_objs_computation_chain(mod_objs_computation_chain):
    from efootprint.core.all_classes_in_order import CANONICAL_COMPUTATION_ORDER
    initial_chain_len = len(mod_objs_computation_chain)
    # Keep only last occurrence of each mod_obj
    optimized_chain = []

    for index in range(len(mod_objs_computation_chain)):
        mod_obj = mod_objs_computation_chain[index]

        if mod_obj not in mod_objs_computation_chain[index + 1:]:
            optimized_chain.append(mod_obj)

    optimized_chain_len = len(optimized_chain)

    if optimized_chain_len != initial_chain_len:
        logger.info(f"Optimized modeling object computation chain from {initial_chain_len} to {optimized_chain_len}"
                    f" modeling object calculated attributes recomputations.")

    ordered_chain = []
    for efootprint_class in CANONICAL_COMPUTATION_ORDER:
        for mod_obj in optimized_chain:
            if issubclass(mod_obj.efootprint_class, efootprint_class):
                ordered_chain.append(mod_obj)

    ordered_chain_ids = [elt.id for elt in ordered_chain]
    optimized_chain_ids = [elt.id for elt in optimized_chain]

    if len(optimized_chain) != len(ordered_chain):
        in_ordered_not_in_optimized = [elt_id for elt_id in ordered_chain_ids if elt_id not in optimized_chain_ids]
        in_optimized_not_in_ordered = [elt_id for elt_id in optimized_chain_ids if elt_id not in ordered_chain_ids]
        raise AssertionError(
            f"Ordered modeling object computation chain \n{ordered_chain_ids} doesn’t have the same length as "
            f"\n{optimized_chain_ids}. This should never happen.\n"
            f"In ordered not in optimized: {in_ordered_not_in_optimized}\n"
            f"In optimized not in ordered: {in_optimized_not_in_ordered}")

    if ordered_chain_ids != optimized_chain_ids:
        logger.debug(f"Reordered modeling object computation chain from \n{ordered_chain_ids} to "
                    f"\n{optimized_chain_ids}")

    for mod_obj in ordered_chain:
        if mod_obj.systems:
            ordered_chain.append(mod_obj.systems[0])
            logger.debug("Added system to optimized chain")
            break

    return ordered_chain


class ModelingObject(metaclass=ABCAfterInitMeta):
    @classmethod
    def from_json_dict(cls, object_json_dict: dict, flat_obj_dict: dict, set_trigger_modeling_updates_to_true=False,
                       is_loaded_from_system_with_calculated_attributes=False):
        new_obj = cls.__new__(cls)
        new_obj.__dict__["contextual_modeling_obj_containers"] = []
        new_obj.trigger_modeling_updates = False
        explainable_object_dicts_to_create_after_objects_creation = {}
        for attr_key, attr_value in object_json_dict.items():
            if isinstance(attr_value, dict) and "label" in attr_value:
                new_value = ExplainableObject.from_json_dict(attr_value)
                new_obj.__setattr__(attr_key, new_value, check_input_validity=False)
                # Calculus graph data is added after setting as new_obj attribute to not interfere
                # with set_modeling_obj_container logic
                new_value.initialize_calculus_graph_data_from_json(attr_value, flat_obj_dict)
            elif isinstance(attr_value, dict) and "label" not in attr_value:
                explainable_object_dicts_to_create_after_objects_creation[(new_obj, attr_key)] = attr_value
            elif isinstance(attr_value, str) and attr_key != "id" and attr_value in flat_obj_dict:
                new_obj.__setattr__(attr_key, flat_obj_dict[attr_value], check_input_validity=False)
            elif isinstance(attr_value, list):
                new_obj.__setattr__(
                    attr_key, [flat_obj_dict[elt] for elt in attr_value], check_input_validity=False)
            else:
                new_obj.__setattr__(attr_key, attr_value)

        if not is_loaded_from_system_with_calculated_attributes:
            for calculated_attribute_name in new_obj.calculated_attributes:
                if getattr(new_obj, calculated_attribute_name, None) is None:
                    new_obj.__setattr__(
                        calculated_attribute_name, EmptyExplainableObject(), check_input_validity=False)

        if set_trigger_modeling_updates_to_true:
            new_obj.trigger_modeling_updates = True

        return new_obj, explainable_object_dicts_to_create_after_objects_creation

    @classmethod
    def default_values(cls):
        return {}

    @classmethod
    def list_values(cls):
        return {}

    @classmethod
    def conditional_list_values(cls):
        return {}

    @classmethod
    def attributes_with_depending_values(cls):
        output_dict = {}
        for dependent_attribute, dependent_attribute_dependencies in cls.conditional_list_values().items():
            if dependent_attribute not in output_dict:
                output_dict[dependent_attribute_dependencies["depends_on"]] = [dependent_attribute]
            else:
                output_dict[dependent_attribute_dependencies["depends_on"]].append(dependent_attribute)

        return output_dict

    @classmethod
    def from_defaults(cls, name, **kwargs):
        output_kwargs = cls.default_values()
        output_kwargs.update(kwargs)

        return cls(name, **output_kwargs)

    @classmethod
    def archetypes(cls):
        return []

    @classmethod
    def attributes_that_can_have_negative_values(cls):
        return []

    def __init__(self, name):
        self.trigger_modeling_updates = False
        self.name = name
        self.id = f"id-{str(uuid.uuid4())[:6]}-{css_escape(self.name)}"
        self.contextual_modeling_obj_containers = []

    @property
    def efootprint_class(self):
        return type(self)

    def check_input_value_type_positivity_and_unit(self, name, input_value, default_values):
        init_sig_params = signature(self.__init__).parameters
        if name in init_sig_params:
            annotation = init_sig_params[name].annotation
            if get_origin(annotation):
                if get_origin(annotation) in (list, List):
                    inner_type = get_args(annotation)[0]
                    if not all(isinstance(item, inner_type) for item in input_value):
                        raise TypeError(f"All elements in '{name}' must be instances of {inner_type.__name__}, "
                                         f"got {[type(item) for item in input_value]}")
            elif not isinstance(input_value, annotation) and not isinstance(input_value, EmptyExplainableObject):
                raise TypeError(f"In {self.name}, attribute {name} should be of type {annotation} "
                                      f"but is of type {type(input_value)}")
            elif issubclass(annotation, ExplainableQuantity):
                default_value = default_values[name]
                if (not isinstance(input_value, EmptyExplainableObject)
                        and input_value.value.dimensionality != default_value.value.dimensionality):
                    raise ValueError(
                        f"Value {input_value} for attribute {name} is not homogeneous to "
                        f"{default_value.value.units} ({default_value.value.dimensionality})")
                if input_value.magnitude < 0 and name not in self.attributes_that_can_have_negative_values():
                    raise ValueError(
                        f"Value {input_value} for attribute {name} should be positive but is negative")

    def check_belonging_to_authorized_values(
            self, name, input_value, list_values, conditional_list_values, attributes_with_depending_values):
        if name in list_values:
            if input_value not in list_values[name]:
                raise ValueError(
                    f"Value {input_value} for attribute {name} is not in the list of possible values: "
                    f"{[elt.value for elt in list_values[name]]}")

        if name in conditional_list_values:
            conditional_attr_name = conditional_list_values[name]['depends_on']
            conditional_value = getattr(self, conditional_list_values[name]["depends_on"])
            if conditional_value is None:
                raise ValueError(f"Value for attribute {conditional_attr_name} is not set but required for checking "
                                 f"validity of {name}")
            if (conditional_value in conditional_list_values[name]["conditional_list_values"]
                    and input_value not in
                    conditional_list_values[name]["conditional_list_values"][conditional_value]):
                raise ValueError(
                    f"Value {input_value} for attribute {name} is not in the list of possible values for "
                    f"{conditional_attr_name} {conditional_value}: "
                    f"{conditional_list_values[name]['conditional_list_values'][conditional_value]}")

        if name in attributes_with_depending_values:
            for dependent_attribute in attributes_with_depending_values[name]:
                dependent_attribute_value = getattr(self, dependent_attribute, None)
                if (dependent_attribute_value is not None
                        and input_value
                        in conditional_list_values[dependent_attribute]["conditional_list_values"]
                        and dependent_attribute_value not in
                        conditional_list_values[dependent_attribute]["conditional_list_values"][input_value]):
                    raise ValueError(
                        f"Setting {name} as {input_value} is not possible because {dependent_attribute_value}"
                        f" is not in the list of possible values for {dependent_attribute} "
                        f"when {name} is {input_value}: "
                        f"{conditional_list_values[dependent_attribute]['conditional_list_values'][input_value]}"
                    )

    @property
    def modeling_obj_containers(self):
        return list(set(
            [contextual_mod_obj_container.modeling_obj_container
             for contextual_mod_obj_container in self.contextual_modeling_obj_containers
             if contextual_mod_obj_container.modeling_obj_container is not None]))

    def add_to_contextual_modeling_obj_containers(self, contextual_mod_obj_container):
        self.contextual_modeling_obj_containers.append(contextual_mod_obj_container)

    @property
    @abstractmethod
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[Type["ModelingObject"]]:
        pass

    @property
    def calculated_attributes(self) -> List[str]:
        return []

    @property
    @abstractmethod
    def systems(self) -> List:
        pass

    def compute_calculated_attributes(self):
        logger.info(f"Computing calculated attributes for {type(self).__name__} {self.name}")
        for attr_name in self.calculated_attributes:
            update_func = retrieve_update_function_from_mod_obj_and_attr_name(self, attr_name)
            update_func()

    @property
    def mod_objs_computation_chain(self) -> List[Type["ModelingObject"]]:
        mod_objs_computation_chain = [self]

        mod_objs_with_attributes_to_compute = self.modeling_objects_whose_attributes_depend_directly_on_me

        while len(mod_objs_with_attributes_to_compute) > 0:
            current_mod_obj_to_update = mod_objs_with_attributes_to_compute[0]
            mod_objs_computation_chain.append(current_mod_obj_to_update)
            mod_objs_with_attributes_to_compute = mod_objs_with_attributes_to_compute[1:]

            for mod_obj in current_mod_obj_to_update.modeling_objects_whose_attributes_depend_directly_on_me:
                if mod_obj not in mod_objs_with_attributes_to_compute:
                    mod_objs_with_attributes_to_compute.append(mod_obj)

        return mod_objs_computation_chain

    @staticmethod
    def launch_mod_objs_computation_chain(mod_objs_computation_chain):
        for mod_obj in mod_objs_computation_chain:
            mod_obj.compute_calculated_attributes()

    def after_init(self):
        self.trigger_modeling_updates = True

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
            ContextualModelingObjectAttribute

        if isinstance(other, ContextualModelingObjectAttribute):
            return self.id == other._value.id
        elif isinstance(other, ModelingObject):
            return self.id == other.id

        return False

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return ["name", "id", "trigger_modeling_updates", "contextual_modeling_obj_containers"]

    def __setattr__(self, name, input_value, check_input_validity=True):
        current_attr = getattr(self, name, None)
        if name in self.attributes_that_shouldnt_trigger_update_logic:
            super().__setattr__(name, input_value)
        elif name in self.calculated_attributes or not self.trigger_modeling_updates:
            if check_input_validity and name not in self.calculated_attributes:
                self.check_input_value_type_positivity_and_unit(name, input_value, self.default_values())
                self.check_belonging_to_authorized_values(
                    name, input_value, self.list_values(), self.conditional_list_values(),
                    self.attributes_with_depending_values())
            value_to_set = input_value
            if isinstance(value_to_set, ModelingObject):
                from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import \
                    ContextualModelingObjectAttribute
                value_to_set = ContextualModelingObjectAttribute(value_to_set, self, name)
            elif type(value_to_set) == list:
                from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
                value_to_set = ListLinkedToModelingObj(value_to_set)
            elif type(value_to_set) == dict:
                value_to_set = current_attr.__class__(value_to_set)
            assert isinstance(value_to_set, ObjectLinkedToModelingObj) or value_to_set is None, \
                    f"input {name} of value {value_to_set} should be an ObjectLinkedToModelingObj or None but is of type {type(value_to_set)}"
            if isinstance(current_attr, ObjectLinkedToModelingObj):
                current_attr.set_modeling_obj_container(None, None)
            if isinstance(value_to_set, ObjectLinkedToModelingObj):
                value_to_set.set_modeling_obj_container(self, name)
            # attribute setting must be done after setting modeling_obj_container because if system has been loaded
            # with calculated attributes from json, the calculation graph must be loaded before the attribute setting.
            super().__setattr__(name, value_to_set)
        else:
            from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
            logger.debug(f"Updating {name} in {self.name}")
            ModelingUpdate([[current_attr, input_value]])

    def compute_mod_objs_computation_chain_from_old_and_new_modeling_objs(
            self, old_value: Type["ModelingObject"], input_value: Type["ModelingObject"], optimize_chain=True)\
            -> List[Type["ModelingObject"]]:
        if (self in old_value.modeling_objects_whose_attributes_depend_directly_on_me and
                old_value in self.modeling_objects_whose_attributes_depend_directly_on_me):
            raise AssertionError(
                f"There is a circular recalculation dependency between {self.id} and {old_value.id}")

        mod_objs_computation_chain = input_value.mod_objs_computation_chain + old_value.mod_objs_computation_chain

        if optimize_chain:
            optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)
            return optimized_chain
        else:
            return mod_objs_computation_chain

    def compute_mod_objs_computation_chain_from_old_and_new_lists(
            self, old_value: List[Type["ModelingObject"]], input_value: List[Type["ModelingObject"]],
            optimize_chain=True) -> List[Type["ModelingObject"]]:
        removed_objs = [obj for obj in old_value if obj not in input_value]
        added_objs = [obj for obj in input_value if obj not in old_value]

        mod_objs_computation_chain = []

        for obj in removed_objs + added_objs:
            if self not in obj.modeling_objects_whose_attributes_depend_directly_on_me:
                mod_objs_computation_chain += obj.mod_objs_computation_chain

        mod_objs_computation_chain += self.mod_objs_computation_chain

        if optimize_chain:
            optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)
            return optimized_chain
        else:
            return mod_objs_computation_chain

    @property
    def mod_obj_attributes(self) -> List[Type["ContextualModelingObjectAttribute"]]:
        from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
        output_list = []
        for attr_name, attr_value in get_instance_attributes(self, ModelingObject).items():
            output_list.append(attr_value)
        for attr_value in get_instance_attributes(self, ListLinkedToModelingObj).values():
            output_list += list(attr_value)

        return output_list

    def object_relationship_graph_to_file(
            self, filename=None, classes_to_ignore=USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE, width=WIDTH, height=HEIGHT,
            notebook=False):
        object_relationships_graph = build_object_relationships_graph(
            self, classes_to_ignore=classes_to_ignore, width=width, height=height, notebook=notebook)

        if filename is None:
            filename = os.path.join(".", f"{self.name} object relationship graph.html")
        object_relationships_graph.show(filename, notebook=notebook)

        add_unique_id_to_mynetwork(filename)

        if notebook:
            return HTML(filename)

    def self_delete(self):
        logger.warning(
            f"Deleting {self.name}, removing backward links pointing to it in "
            f"{','.join([mod_obj.name for mod_obj in self.mod_obj_attributes])}")
        if self.modeling_obj_containers:
            raise PermissionError(
                f"You can’t delete {self.name} because "
                f"{','.join([mod_obj.name for mod_obj in self.modeling_obj_containers])} have it as attribute.")

        for attr in self.mod_obj_attributes:
            attr.set_modeling_obj_container(None, None)

        if self.trigger_modeling_updates:
            mod_objs_computation_chain = sum(
                [attr.mod_objs_computation_chain for attr in self.mod_obj_attributes], start=[])
            optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)

            self.launch_mod_objs_computation_chain(optimized_chain)

        del self

    def to_json(self, save_calculated_attributes=False) -> dict:
        from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
        output_dict = {}

        for key, value in self.__dict__.items():
            if key in ["name", "id", "short_name", "impact_url"]:
                output_dict[key] = value
            if (
                    (key in self.calculated_attributes and not save_calculated_attributes)
                    or key in self.attributes_that_shouldnt_trigger_update_logic
            ):
                continue
            elif value is None or isinstance(value, str):
                output_dict[key] = value
            elif isinstance(value, ModelingObject):
                output_dict[key] = value.id
            elif isinstance(value, ModelingUpdate):
                continue
            elif getattr(value, "to_json", None) is not None:
                output_dict[key] = value.to_json(save_calculated_attributes)
            else:
                raise ValueError(f"Attribute {key} of {self.name} {type(value)}) is not handled in to_json")

        return output_dict

    @property
    def class_as_simple_str(self):
        return type(self).__name__

    def __repr__(self):
        return str(self)

    def __str__(self):
        output_str = ""

        def key_value_to_str(input_key, input_value):
            key_value_str = ""

            if type(input_value) in (str, int) or input_value is None:
                key_value_str = f"{input_key}: {input_value}\n"
            elif isinstance(input_value, list):
                if len(input_value) == 0:
                    key_value_str = f"{input_key}: {input_value}\n"
                else:
                    if type(input_value[0]) == str:
                        key_value_str = f"{input_key}: {input_value}"
                    elif isinstance(input_value[0], ModelingObject):
                        str_value = "[" + ", ".join([elt.id for elt in input_value]) + "]"
                        key_value_str = f"{input_key}: {str_value}\n"
            elif isinstance(input_value, ModelingObject):
                key_value_str = f"{input_key}: {input_value.id}\n"
            elif isinstance(input_value, ObjectLinkedToModelingObj):
                key_value_str = f"{input_key}: {input_value}\n"

            return key_value_str

        output_str += f"{self.class_as_simple_str} {self.id}\n \nname: {self.name}\n"

        for key, attr_value in self.__dict__.items():
            if key in self.attributes_that_shouldnt_trigger_update_logic or key in self.calculated_attributes:
                continue
            output_str += key_value_to_str(key, attr_value)

        if len(self.calculated_attributes) > 0:
            output_str += " \ncalculated_attributes:\n"
            for key in self.calculated_attributes:
                output_str += "  " + key_value_to_str(key, getattr(self, key))

        return output_str
