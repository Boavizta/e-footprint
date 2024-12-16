from copy import copy
from datetime import datetime
from typing import List, Tuple

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_attr_updates_chain, ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities, EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.recomputation_utils import launch_update_function_chain
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues


def compute_attr_updates_chain_from_mod_obj_computation_chain(mod_objs_computation_chain: List[ModelingObject]):
    attr_updates_chain = []
    for mod_obj in mod_objs_computation_chain:
        for calculated_attribute in mod_obj.calculated_attributes:
            attr_updates_chain.append(getattr(mod_obj, calculated_attribute))

    return attr_updates_chain


class Simulation:
    def __init__(
            self, simulation_date: datetime,
            changes_list: List[Tuple[SourceValue | SourceHourlyValues | ModelingObject | ListLinkedToModelingObj,
            SourceValue | SourceHourlyValues | ModelingObject | ListLinkedToModelingObj]]):
        first_changed_val = changes_list[0][0]
        if isinstance(first_changed_val, ModelingObject):
            self.system = first_changed_val.systems[0]
        elif isinstance(first_changed_val, ObjectLinkedToModelingObj):
            self.system = first_changed_val.modeling_obj_container.systems[0]
        else:
            raise ValueError(
                f"First changed value {first_changed_val} is neither a ModelingObject nor ObjectLinkedToModelingObj")
        self.system.simulation = self
        self.simulation_date = simulation_date
        self.simulation_date_as_hourly_freq = pd.Timestamp(simulation_date).to_period(freq="h")
        self.changes_list = changes_list
        self.old_sourcevalues = []
        self.new_sourcevalues = []
        self.old_mod_obj_links = []
        self.new_mod_obj_links = []

        self.compute_new_and_old_source_values_and_mod_obj_link_lists()

        self.attr_updates_chain_from_mod_obj_links_updates = []
        self.compute_attr_updates_chain_from_mod_obj_links_updates()
        self.create_new_mod_obj_links()

        self.values_to_recompute = []
        self.recomputed_values = []
        self.ancestors_not_in_computation_chain = []
        self.hourly_quantities_to_filter = []
        self.filtered_hourly_quantities = []
        self.ancestors_to_replace_by_copies = []
        self.replaced_ancestors_copies = []
        self.recompute_attributes()

        self.reset_pre_simulation_values()

    def compute_new_and_old_source_values_and_mod_obj_link_lists(self):
        for old_value, new_value in self.changes_list:
            if isinstance(new_value, list):
                new_value = ListLinkedToModelingObj(new_value)
            if type(old_value) != type(new_value):
                raise ValueError(f"In simulations old and new values should have same type, got "
                                 f"{type(old_value)} and {type(new_value)}")
            if isinstance(old_value, ExplainableObject):
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

    def compute_attr_updates_chain_from_mod_obj_links_updates(self):
        for old_value, new_value in zip(self.old_mod_obj_links, self.new_mod_obj_links):
            mod_obj_container = old_value.modeling_obj_container
            if isinstance(old_value, ModelingObject):
                attr_updates_chain = compute_attr_updates_chain_from_mod_obj_computation_chain(
                    mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs(
                        old_value, new_value))
            elif isinstance(old_value, ListLinkedToModelingObj):
                attr_updates_chain = compute_attr_updates_chain_from_mod_obj_computation_chain(
                    mod_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists(
                        old_value, new_value))

            self.attr_updates_chain_from_mod_obj_links_updates.append(attr_updates_chain)

    def create_new_mod_obj_links(self):
        for old_value, new_value in zip(self.old_mod_obj_links, self.new_mod_obj_links):
            mod_obj_container = old_value.modeling_obj_container
            attr_name_in_mod_obj_container = old_value.attr_name_in_mod_obj_container
            if isinstance(old_value, ModelingObject):
                new_value.add_obj_to_modeling_obj_containers(mod_obj_container)
            elif isinstance(old_value, ListLinkedToModelingObj):
                new_value.set_modeling_obj_container(mod_obj_container, attr_name_in_mod_obj_container)
                new_value.register_previous_values()

            mod_obj_container.__dict__[attr_name_in_mod_obj_container] = new_value
                
    def recompute_attributes(self):
        self.values_to_recompute = self.generate_optimized_attr_updates_chain()
        self.ancestors_not_in_computation_chain = self.compute_ancestors_not_in_computation_chain()
        self.hourly_quantities_to_filter = self.compute_hourly_quantities_to_filter()
        self.filter_hourly_quantities_to_filter()
        if self.old_mod_obj_links:
            # The simulation will change the calculation graph, so we need to replace all ancestors not in computation
            # chain by their copies to keep the original calculation graph unchanged
            self.ancestors_to_replace_by_copies = [
                ancestor for ancestor in self.ancestors_not_in_computation_chain
                if ancestor.id not in [value.id for value in self.hourly_quantities_to_filter]]
            self.replaced_ancestors_copies = self.replace_ancestors_not_in_computation_chain_by_copies()
        self.change_input_values()
        launch_update_function_chain([value.update_function for value in self.values_to_recompute])
        self.save_recomputed_values()

    def generate_optimized_attr_updates_chain(self):
        attr_updates_chain_from_mod_obj_links_updates = sum(
            self.attr_updates_chain_from_mod_obj_links_updates, start=[])

        attr_updates_chain_from_attributes_updates = sum(
            [old_value.attr_updates_chain for old_value in self.old_sourcevalues], start=[])

        optimized_chain = optimize_attr_updates_chain(
            attr_updates_chain_from_mod_obj_links_updates + attr_updates_chain_from_attributes_updates)

        return optimized_chain

    def compute_ancestors_not_in_computation_chain(self):
        all_ancestors_of_values_to_recompute = sum(
            [value.all_ancestors_with_id for value in self.values_to_recompute], start=[])
        deduplicated_all_ancestors_of_values_to_recompute = []
        for ancestor in all_ancestors_of_values_to_recompute:
            if ancestor.id not in [elt.id for elt in deduplicated_all_ancestors_of_values_to_recompute]:
                deduplicated_all_ancestors_of_values_to_recompute.append(ancestor)
        values_to_recompute_ids = [elt.id for elt in self.values_to_recompute]
        ancestors_not_in_computation_chain = [
            ancestor for ancestor in deduplicated_all_ancestors_of_values_to_recompute
            if ancestor.id not in values_to_recompute_ids]

        return ancestors_not_in_computation_chain

    def compute_hourly_quantities_to_filter(self):
        hourly_quantities_ancestors_not_in_computation_chain = [
            ancestor for ancestor in self.ancestors_not_in_computation_chain
            if isinstance(ancestor, ExplainableHourlyQuantities)]
        hourly_quantities_to_filter = []

        global_min_date = None
        global_max_date = None

        for ancestor in hourly_quantities_ancestors_not_in_computation_chain:
            min_date = ancestor.value.index.min()
            max_date = ancestor.value.index.max()
            if global_min_date is None:
                global_min_date = min_date
            if global_max_date is None:
                global_max_date = max_date
            global_min_date = min(min_date, global_min_date)
            global_max_date = max(max_date, global_max_date)
            if self.simulation_date_as_hourly_freq <= max_date:
                hourly_quantities_to_filter.append(ancestor)

        if not (global_min_date <= self.simulation_date_as_hourly_freq <= global_max_date):
            raise ValueError(
                f"Can’t start a simulation on the {self.simulation_date_as_hourly_freq} because "
                f"{self.simulation_date_as_hourly_freq}doesn’t belong to the existing modeling period "
                f"{global_min_date} to {global_max_date}")

        return hourly_quantities_to_filter

    def filter_hourly_quantities_to_filter(self):
        for hourly_quantities in self.hourly_quantities_to_filter:

            new_value = ExplainableHourlyQuantities(
                hourly_quantities.value[hourly_quantities.value.index >= self.simulation_date_as_hourly_freq],
                hourly_quantities.label, hourly_quantities.left_parent, hourly_quantities.right_parent,
                hourly_quantities.operator, hourly_quantities.source
            )
            if len(new_value) == 0:
                new_value = EmptyExplainableObject()
            hourly_quantities.replace_by_new_value_in_mod_obj_container(new_value)
            self.filtered_hourly_quantities.append(new_value)

    def replace_ancestors_not_in_computation_chain_by_copies(self):
        copies = []
        for ancestor_to_replace_by_copy in self.ancestors_to_replace_by_copies:
            # Replace all ancestors not in computation chain by their copy so that the original calculation graph
            # will remain unchanged when the simulation is over
            ancestor_copy = copy(ancestor_to_replace_by_copy)
            ancestor_to_replace_by_copy.replace_by_new_value_in_mod_obj_container(ancestor_copy)
            copies.append(ancestor_copy)

        return copies

    def change_input_values(self):
        for old_value, new_value in zip(self.old_sourcevalues, self.new_sourcevalues):
            old_value.replace_by_new_value_in_mod_obj_container(new_value)

    def save_recomputed_values(self):
        for expl_obj in self.values_to_recompute:
            self.recomputed_values.append(
                getattr(expl_obj.modeling_obj_container, expl_obj.attr_name_in_mod_obj_container))

    def reset_pre_simulation_values(self):
        for previous_value in (
                self.old_sourcevalues + self.values_to_recompute + self.hourly_quantities_to_filter +
                self.ancestors_to_replace_by_copies + self.old_mod_obj_links):
            previous_value.replace_by_new_value_in_mod_obj_container(previous_value)

    def set_simulation_values(self):
        for new_value in (
                self.new_sourcevalues + self.recomputed_values + self.filtered_hourly_quantities +
                self.replaced_ancestors_copies + self.new_mod_obj_links):
            new_value.replace_by_new_value_in_mod_obj_container(new_value)
