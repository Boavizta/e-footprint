from typing import Type, Optional
from dataclasses import dataclass
import os

from IPython.display import HTML

from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.constants.units import u
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.graph_tools import add_unique_id_to_mynetwork


@dataclass
class Source:
    name: str
    link: Optional[str]


def retrieve_update_function_from_mod_obj_and_attr_name(mod_obj, attr_name):
    update_func_name = f"update_{attr_name}"
    update_func = getattr(mod_obj, update_func_name, None)

    if update_func is None:
        raise AttributeError(f"No update function associated to {attr_name} in {mod_obj.id}, please create it.")

    return update_func


def optimize_attr_updates_chain(attr_updates_chain):
    initial_chain_len = len(attr_updates_chain)
    attr_to_update_ids = [attr.id for attr in attr_updates_chain]
    optimized_chain = []

    for index in range(len(attr_updates_chain)):
        attr_to_update = attr_updates_chain[index]

        if attr_to_update.id not in attr_to_update_ids[index + 1:]:
            # Keep only last occurrence of each update function
            optimized_chain.append(attr_to_update)

    optimized_chain_len = len(optimized_chain)

    if optimized_chain_len != initial_chain_len:
        logger.info(f"Optimized update function chain from {initial_chain_len} to {optimized_chain_len} calculations")

    return optimized_chain


class ExplainableObject(ObjectLinkedToModelingObj):
    def __init__(
            self, value: object, label: str = None, left_parent: Type["ExplainableObject"] = None,
            right_parent: Type["ExplainableObject"] = None, operator: str = None, source: Source = None):
        super().__init__()
        self.simulation_twin = None
        self.baseline_twin = None
        self.simulation = None
        self.initial_modeling_obj_container = None
        self.value = value
        if not label and (left_parent is None and right_parent is None):
            raise ValueError(f"ExplainableObject without parent should have a label")
        self.source = source
        self.label = None
        self.set_label(label)
        self.left_parent = left_parent
        self.right_parent = right_parent
        self.operator = operator
        self.direct_ancestors_with_id = []
        self.direct_children_with_id = []

        for parent in (self.left_parent, self.right_parent):
            if parent is not None:
                self.direct_ancestors_with_id += [
                    ancestor_with_id for ancestor_with_id in parent.return_direct_ancestors_with_id_to_child()
                    if ancestor_with_id.id not in self.direct_ancestor_ids]

    def __copy__(self):
        cls = self.__class__
        new_instance = cls.__new__(cls)
        new_instance.__init__(value=self.value, label=self.label, source=getattr(self, "source", None))

        return new_instance

    def set_label(self, new_label):
        if self.source is not None and f"from {self.source.name}" not in new_label:
            self.label = f"{new_label} from {self.source.name}"
        else:
            self.label = new_label

        return self

    @property
    def has_parent(self):
        return self.left_parent is not None or self.right_parent is not None

    @property
    def direct_ancestor_ids(self):
        return [attr.id for attr in self.direct_ancestors_with_id]

    @property
    def direct_child_ids(self):
        return [attr.id for attr in self.direct_children_with_id]

    def replace_in_mod_obj_container_without_recomputation(self, new_value):
        value_to_set = new_value
        if isinstance(value_to_set, float) and self.dict_container is not None:
            from efootprint.abstract_modeling_classes.source_objects import SourceValue
            value_to_set = SourceValue(value_to_set * u.dimensionless)

        super().replace_in_mod_obj_container_without_recomputation(value_to_set)

    def set_modeling_obj_container(
            self, new_modeling_obj_container: Type["ModelingObject"] | None, attr_name: str | None):
        if not self.label:
            raise PermissionError(
                f"ExplainableObjects that are attributes of a ModelingObject should always have a label.")
        elif self.modeling_obj_container is not None and new_modeling_obj_container is not None\
                and self.modeling_obj_container != new_modeling_obj_container:
            raise PermissionError(
                f"{self} is already linked to {self.modeling_obj_container.id} and is trying to be linked to "
                f"{new_modeling_obj_container.id}.")

        if self.modeling_obj_container is not None:
            for direct_ancestor_with_id in self.direct_ancestors_with_id:
                direct_ancestor_with_id.remove_child_from_direct_children_with_id(direct_child=self)

        super().set_modeling_obj_container(new_modeling_obj_container, attr_name)

        if new_modeling_obj_container is not None:
            if self.initial_modeling_obj_container is None:
                self.initial_modeling_obj_container = new_modeling_obj_container
            for direct_ancestor_with_id in self.direct_ancestors_with_id:
                direct_ancestor_with_id.add_child_to_direct_children_with_id(direct_child=self)

    def return_direct_ancestors_with_id_to_child(self):
        if self.modeling_obj_container is not None:
            return [self]
        else:
            return [ancestor for ancestor in self.direct_ancestors_with_id
                    if ancestor.modeling_obj_container is not None]

    def add_child_to_direct_children_with_id(self, direct_child):
        if direct_child.id not in self.direct_child_ids:
            self.direct_children_with_id.append(direct_child)

    def remove_child_from_direct_children_with_id(self, direct_child):
        self.direct_children_with_id = [
            child for child in self.direct_children_with_id if child.id != direct_child.id]

    @property
    def all_descendants_with_id(self):
        all_descendants = []

        def retrieve_descendants(expl_obj: ExplainableObject, descendants_list):
            for child in expl_obj.direct_children_with_id:
                if child.id not in [elt.id for elt in descendants_list]:
                    descendants_list.append(child)
                retrieve_descendants(child, descendants_list)

        retrieve_descendants(self, all_descendants)

        return all_descendants

    @property
    def all_ancestors_with_id(self):
        all_ancestors = []

        def retrieve_ancestors(expl_obj: ExplainableObject, ancestors_list):
            for parent in expl_obj.direct_ancestors_with_id:
                if parent.id not in [elt.id for elt in ancestors_list]:
                    ancestors_list.append(parent)
                retrieve_ancestors(parent, ancestors_list)

        retrieve_ancestors(self, all_ancestors)

        return all_ancestors

    @property
    def attr_updates_chain(self):
        attr_updates_chain = []
        descendants = self.all_descendants_with_id
        has_been_added_to_chain_dict = {descendant.id: False for descendant in descendants if descendant.id != self.id}

        added_parents_with_children_to_add = [self]

        while len(added_parents_with_children_to_add) > 0:
            for added_parent in added_parents_with_children_to_add:
                drop_added_parent_from_list = True
                for child in added_parent.direct_children_with_id:
                    if not has_been_added_to_chain_dict[child.id]:
                        ancestors_that_belong_to_self_descendants = [
                            ancestor for ancestor in child.direct_ancestors_with_id
                            if ancestor.id in [ancestor.id for ancestor in descendants]]
                        if all([has_been_added_to_chain_dict[ancestor.id]
                                for ancestor in ancestors_that_belong_to_self_descendants]):
                            if not child.dict_container:
                                attr_updates_chain.append(child)
                            else:
                                attr_updates_chain.append(child.dict_container)
                            has_been_added_to_chain_dict[child.id] = True
                            if len(child.direct_children_with_id) > 0:
                                added_parents_with_children_to_add.append(child)
                        else:
                            # Wait for next iteration
                            drop_added_parent_from_list = False
                if drop_added_parent_from_list:
                    added_parents_with_children_to_add = [
                        child for child in added_parents_with_children_to_add
                        if child.id != added_parent.id]

        optimized_chain = optimize_attr_updates_chain(attr_updates_chain)

        return optimized_chain

    @property
    def update_function(self):
        if self.modeling_obj_container is None:
            raise ValueError(
                f"{self} doesn’t have a modeling_obj_container, hence it makes no sense "
                f"to look for its update function")
        update_func = retrieve_update_function_from_mod_obj_and_attr_name(
            self.modeling_obj_container, self.attr_name_in_mod_obj_container)

        return update_func

    @property
    def update_function_chain(self):
        return [attribute.update_function for attribute in self.attr_updates_chain]
    
    def generate_explainable_object_with_logical_dependency(
            self, explainable_condition: Type["ExplainableObject"]):
        return self.__class__(value=self.value, label=self.label, left_parent=self, right_parent=explainable_condition,
                              operator="logically dependent on")

    def explain(self, pretty_print=True):
        element_value_to_print = str(self)

        if self.left_parent is None and self.right_parent is None:
            return f"{self.label} = {element_value_to_print}"
        explain_tuples = self.compute_explain_nested_tuples()

        if pretty_print:
            return self.pretty_print_calculation(
                f"{self.label} = {self.print_tuple_element(explain_tuples, print_values_instead_of_labels=False)}"
                f" = {self.print_tuple_element(explain_tuples, print_values_instead_of_labels=True)}"
                f" = {element_value_to_print}")
        else:
            return f"{self.label} = {self.print_tuple_element(explain_tuples, print_values_instead_of_labels=False)}" \
                f" = {self.print_tuple_element(explain_tuples, print_values_instead_of_labels=True)}" \
                f" = {element_value_to_print}"

    def compute_explain_nested_tuples(self, return_label_if_self_has_one=False):
        if return_label_if_self_has_one and self.label:
            return self

        left_explanation = None
        right_explanation = None

        if self.left_parent:
            left_explanation = self.left_parent.compute_explain_nested_tuples(return_label_if_self_has_one=True)
        if self.right_parent:
            right_explanation = self.right_parent.compute_explain_nested_tuples(return_label_if_self_has_one=True)

        if left_explanation is None and right_explanation is None:
            raise ValueError("Object to explain should have at least one child")

        return left_explanation, self.operator, right_explanation

    def print_tuple_element(self, tuple_element: object, print_values_instead_of_labels: bool):
        if isinstance(tuple_element, ExplainableObject):
            if print_values_instead_of_labels:
                return str(tuple_element)
            else:
                return f"{tuple_element.label}"
        elif type(tuple_element) == str:
            return tuple_element
        elif type(tuple_element) == tuple:
            if tuple_element[1] is None:
                return f"{self.print_tuple_element(tuple_element[0], print_values_instead_of_labels)}"
            if tuple_element[2] is None:
                return f"{tuple_element[1]}" \
                       f" of ({self.print_tuple_element(tuple_element[0], print_values_instead_of_labels)})"

            left_parenthesis = False
            right_parenthesis = False

            if tuple_element[1] == "/":
                if type(tuple_element[2]) == tuple:
                    right_parenthesis = True
                if type(tuple_element[0]) == tuple and tuple_element[0][1] != "*":
                    left_parenthesis = True
            elif tuple_element[1] == "*":
                if type(tuple_element[0]) == tuple and tuple_element[0][1] != "*":
                    left_parenthesis = True
                if type(tuple_element[2]) == tuple and tuple_element[2][1] != "*":
                    right_parenthesis = True
            elif tuple_element[1] == "-":
                if type(tuple_element[2]) == tuple and tuple_element[2][1] in ["+", "-"]:
                    right_parenthesis = True
            elif tuple_element[1] == "+":
                pass

            lp_open = ""
            lp_close = ""
            rp_open = ""
            rp_close = ""

            if left_parenthesis:
                lp_open = "("
                lp_close = ")"
            if right_parenthesis:
                rp_open = "("
                rp_close = ")"

            return f"{lp_open}{self.print_tuple_element(tuple_element[0], print_values_instead_of_labels)}{lp_close}" \
                   f" {tuple_element[1]}" \
                   f" {rp_open}{self.print_tuple_element(tuple_element[2], print_values_instead_of_labels)}{rp_close}"

    @staticmethod
    def pretty_print_calculation(calc_str):
        return calc_str.replace(" = ", "\n=\n")

    def calculus_graph_to_file(
            self, filename=None, colors_dict=None, x_multiplier=150, y_multiplier=150, width="1800px", height="900px",
            notebook=False, max_depth=100):
        if colors_dict is None:
            colors_dict = {"user data": "gold", "default": "darkred"}
        calculus_graph = build_calculus_graph(
            self, colors_dict, x_multiplier, y_multiplier, width, height, notebook, max_depth=max_depth)

        if filename is None:
            filename = os.path.join(".", f"{self.label} calculus graph.html")

        calculus_graph.show(filename, notebook=notebook)

        add_unique_id_to_mynetwork(filename)

        if notebook:
            return HTML(filename)

    def to_json(self, with_calculated_attributes_data=False):
        output_dict = {"label": self.label}

        if isinstance(self.value, str):  # Case of technology in WebApplication
            output_dict["value"] = self.value
        elif getattr(self.value, "zone", None) is not None:  # Case of timezone in Country class
            output_dict["zone"] = self.value.zone

        if self.source is not None:
            output_dict["source"] = {"name": self.source.name, "link": self.source.link}

        if with_calculated_attributes_data:
            output_dict["id"] = self.id
            output_dict["direct_ancestors_with_id"] = [elt.id for elt in self.direct_ancestors_with_id]
            output_dict["direct_children_with_id"] = [elt.id for elt in self.direct_children_with_id]

        return output_dict

    def __repr__(self):
        return str(self)

    def __str__(self):
        self_as_str = str(self.value)
        if len(self_as_str) > 60:
            self_as_str = self_as_str[:60] + "..."

        return self_as_str

    def __eq__(self, other):
        if isinstance(other, ExplainableObject):
            return self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash(self.value)
