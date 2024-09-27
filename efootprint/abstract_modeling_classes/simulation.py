from datetime import datetime
from typing import List, Tuple

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_update_computation_chain
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.recomputation_utils import launch_attributes_computation_chain


class Simulation:
    def __init__(
            self, simulation_date: datetime,
            changes_list: List[Tuple[ExplainableObject | ModelingObject | List[ModelingObject],
            ExplainableObject | ModelingObject | List[ModelingObject]]]):
        self.simulation_date = simulation_date
        self.simulation_date_as_hourly_freq = pd.Timestamp(simulation_date).to_period(freq="h")
        self.changes_list = changes_list
        self.old_sourcevalues = []
        self.new_sourcevalues = []
        self.old_mod_obj_links = []
        self.new_mod_obj_links = []

        self.compute_new_and_old_source_values_and_mod_obj_link_lists()

        self.create_new_mod_obj_links()

        self.attributes_computation_chain = []
        self.hourly_quantities_ancestors_not_in_computation_chain = []
        self.hourly_quantities_to_filter = []
        self.recomputed_values = []
        self.recompute_attributes()

        self.mod_obj_computation_chain = []
        self.recompute_modeling_objects()

    def compute_new_and_old_source_values_and_mod_obj_link_lists(self):
        for old_value, new_value in self.changes_list:
            if type(old_value) != type(new_value):
                raise ValueError(f"In simulations old and new values should have same type, got "
                                 f"{type(old_value)} and {type(new_value)}")
            if issubclass(type(old_value), ExplainableObject):
                if new_value.modeling_obj_container is not None:
                    raise ValueError(
                        f"Can’t use {new_value} as simulation input because it already belongs to "
                        f"{new_value.modeling_obj_container.name}")
                self.old_sourcevalues.append(old_value)
                self.new_sourcevalues.append(new_value)
            else:
                if not isinstance(new_value, ListLinkedToModelingObj) or isinstance(new_value, ModelingObject):
                    raise ValueError(
                        f"New e-footprint object attributes should be lists of ModelingObject or ModelingObjects, "
                        f"got {old_value} of type {type(old_value)} trying to be set to an object of type "
                        f"{type(new_value)}")
                self.old_mod_obj_links.append(old_value)
                self.new_mod_obj_links.append(new_value)

    def create_new_mod_obj_links(self):
        raise NotImplementedError
                
    def recompute_attributes(self):
        self.generate_optimized_attributes_computation_chain()
        self.compute_hourly_quantities_ancestors_not_in_computation_chain()
        self.compute_hourly_quantities_to_filter()
        self.filter_hourly_quantities_to_filter()
        launch_attributes_computation_chain(self.attributes_computation_chain)
        self.save_recomputed_values(self.attributes_computation_chain)

    def generate_optimized_attributes_computation_chain(self):
        raise NotImplementedError("Must get attr chain from mod obj chain")
        full_attributes_computation_chain = sum(
            [old_value.update_computation_chain for old_value in self.old_sourcevalues], start=[])

        optimized_chain = optimize_update_computation_chain(full_attributes_computation_chain)

        self.attributes_computation_chain = optimized_chain

    def compute_hourly_quantities_ancestors_not_in_computation_chain(self):
        all_ancestors_of_values_to_recompute = set(sum(
            [value.all_ancestors_with_id for value in self.attributes_computation_chain], start=[]))
        old_value_computation_chain_ids = [elt.id for elt in self.attributes_computation_chain]
        ancestors_not_in_computation_chain = [
            ancestor for ancestor in all_ancestors_of_values_to_recompute
            if ancestor.id not in old_value_computation_chain_ids]

        hourly_quantities_ancestors_not_in_computation_chain = [
            ancestor for ancestor in ancestors_not_in_computation_chain
            if isinstance(ancestor, ExplainableHourlyQuantities)]

        self.hourly_quantities_ancestors_not_in_computation_chain = hourly_quantities_ancestors_not_in_computation_chain

    def compute_hourly_quantities_to_filter(self):
        happens_during_a_simulation_period = False
        hourly_quantities_to_filter = []

        for ancestor in self.hourly_quantities_ancestors_not_in_computation_chain:
            if self.simulation_date_as_hourly_freq in ancestor.value.index:
                hourly_quantities_to_filter.append(ancestor)
                if isinstance(ancestor.modeling_obj_container, UsagePattern):
                    happens_during_a_simulation_period = True

        if not happens_during_a_simulation_period:
            raise ValueError(
                f"Can’t start a simulation on the {self.simulation_date} of {self.old_value.label} changing from "
                f"{self.old_value.value} to {self.new_value.value} because {self.simulation_date} doesn’t belong to an "
                f"existing modeling period")

        self.hourly_quantities_to_filter = hourly_quantities_to_filter

    def filter_hourly_quantities_to_filter(self):
        for hourly_quantities in self.hourly_quantities_to_filter:
            mod_obj_container = hourly_quantities.modeling_obj_container
            attr_name = hourly_quantities.attr_name_in_mod_obj_container
            new_value = ExplainableHourlyQuantities(
                hourly_quantities.value[hourly_quantities.value.index >= self.simulation_date_as_hourly_freq],
                hourly_quantities.label, hourly_quantities.left_parent, hourly_quantities.right_parent,
                hourly_quantities.operator, hourly_quantities.source
            )
            mod_obj_container.__dict__[attr_name] = new_value
            new_value.set_modeling_obj_container(mod_obj_container, attr_name)

    def save_recomputed_values(self, computation_chain):
        for expl_obj in computation_chain:
            self.recomputed_values.append(
                getattr(expl_obj.modeling_obj_container, expl_obj.attr_name_in_mod_obj_container))
