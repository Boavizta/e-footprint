from copy import copy
from datetime import datetime
from typing import List, Tuple

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_attr_updates_chain, ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableHourlyQuantities, EmptyExplainableObject
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.abstract_modeling_classes.recomputation_utils import launch_update_function_chain
from efootprint.logger import logger


def compute_attr_updates_chain_from_mod_objs_computation_chain(mod_objs_computation_chain: List[ModelingObject]):
    attr_updates_chain = []
    for mod_obj in mod_objs_computation_chain:
        for calculated_attribute in mod_obj.calculated_attributes:
            attr_updates_chain.append(getattr(mod_obj, calculated_attribute))

    return attr_updates_chain


class ModelingUpdate:
    def __init__(
            self, 
            changes_list: List[Tuple[ObjectLinkedToModelingObj, ObjectLinkedToModelingObj | list | dict]],
            simulation_date: datetime = None):
        first_changed_val = changes_list[0][0]
        if isinstance(first_changed_val, ObjectLinkedToModelingObj):
            self.system = first_changed_val.modeling_obj_container.systems[0]
        else:
            raise ValueError(
                f"First changed value {first_changed_val} is not an ObjectLinkedToModelingObj")
        self.changes_list = changes_list

        self.simulation_date = simulation_date
        self.simulation_date_as_hourly_freq = None
        if simulation_date is not None:
            self.system.simulation = self
            self.simulation_date_as_hourly_freq = pd.Timestamp(simulation_date).to_period(freq="h")

        self.old_sourcevalues = []
        self.new_sourcevalues = []
        self.old_mod_obj_links = []
        self.new_mod_obj_links = []
        self.old_mod_obj_list_links = []
        self.new_mod_obj_list_links = []
        self.old_mod_obj_dicts = []
        self.new_mod_obj_dicts = []
        self.compute_new_and_old_lists()
        
        self.mod_objs_computation_chain = self.compute_mod_objs_computation_chain()
        self.attr_updates_chain_from_mod_objs_computation_chains = (
            compute_attr_updates_chain_from_mod_objs_computation_chain(self.mod_objs_computation_chain))

        self.update_links()
        self.change_input_values()

        if self.simulation_date is not None:
            self.ancestors_not_in_computation_chain = []
            self.hourly_quantities_to_filter = []
            self.filtered_hourly_quantities = []
            self.ancestors_to_replace_by_copies = []
            self.replaced_ancestors_copies = []
            self.make_simulation_specific_operations()

        self.values_to_recompute = []
        self.recomputed_values = []
        self.recompute_attributes()
        
        if simulation_date is not None:
            self.reset_pre_simulation_values()

    def compute_new_and_old_lists(self):
        for old_value, new_value in self.changes_list:
            assert isinstance(old_value, ObjectLinkedToModelingObj)
            if new_value is None:
                assert isinstance(old_value, ExplainableObject)
                new_value = EmptyExplainableObject()

            if id(old_value) == id(new_value):
                logger.warning(
                    f"{old_value.name} is updated to itself. "
                    f"This is surprising, you might want to double check your action. "
                    f"The link update logic will be skipped.")
            else:
                if isinstance(old_value, ExplainableObject):
                    self.old_sourcevalues.append(old_value)
                    self.new_sourcevalues.append(new_value)
                elif isinstance(new_value, ModelingObject):
                    self.old_mod_obj_links.append(old_value)
                    self.new_mod_obj_links.append(new_value)
                elif isinstance(new_value, list):
                    self.old_mod_obj_list_links.append(old_value)
                    self.new_mod_obj_list_links.append(new_value)
                elif isinstance(new_value, dict):
                    self.old_mod_obj_dicts.append(old_value)
                    self.new_mod_obj_dicts.append(new_value)
                else:
                    raise ValueError(
                        f"New e-footprint attributes should be ExplainableObjects, weighted dicts of ModelingObject "
                        f"or ModelingObjects, got {old_value} of type {type(old_value)} trying to be set to an object "
                        f"of type {type(new_value)}")
            
    def compute_mod_objs_computation_chain(self):
        mod_objs_computation_chain = []
        for old_value, new_value in zip(self.old_mod_obj_links, self.new_mod_obj_links):
            mod_objs_computation_chain += (
                old_value.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs(
                    old_value, new_value))
        for old_value, new_value in zip(self.old_mod_obj_list_links, self.new_mod_obj_list_links):
            mod_objs_computation_chain += (
                old_value.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists(
                    old_value, new_value))
        for old_dict, new_dict in zip(self.old_mod_obj_dicts, self.new_mod_obj_dicts):
            mod_objs_computation_chain += (
                old_dict.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists(
                    old_dict.keys(), new_dict.keys()))

        optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)

        return optimized_chain

    def update_links(self):
        for old_value, new_value in zip(self.old_mod_obj_links, self.new_mod_obj_links):
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)
        for old_value, new_value in zip(self.old_mod_obj_list_links, self.new_mod_obj_list_links):
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)
        for old_dict, new_dict in zip(self.old_mod_obj_dicts, self.new_mod_obj_dicts):
            old_dict.replace_in_mod_obj_container_without_recomputation(new_dict)

    def make_simulation_specific_operations(self):
        self.ancestors_not_in_computation_chain = self.compute_ancestors_not_in_computation_chain()
        self.hourly_quantities_to_filter = self.compute_hourly_quantities_to_filter()
        self.filter_hourly_quantities_to_filter()
        if self.old_mod_obj_links or self.old_mod_obj_dicts:
            # The simulation will change the calculation graph, so we need to replace all ancestors not in
            # computation chain by their copies to keep the original calculation graph unchanged
            self.ancestors_to_replace_by_copies = [
                ancestor for ancestor in self.ancestors_not_in_computation_chain
                if ancestor.id not in [value.id for value in self.hourly_quantities_to_filter]]
            self.replaced_ancestors_copies = self.replace_ancestors_not_in_computation_chain_by_copies()

    def recompute_attributes(self):
        self.values_to_recompute = self.generate_optimized_attr_updates_chain()
        launch_update_function_chain([value.update_function for value in self.values_to_recompute])
        self.save_recomputed_values()

    def generate_optimized_attr_updates_chain(self):
        attr_updates_chain_from_attributes_updates = sum(
            [old_value.attr_updates_chain for old_value in self.old_sourcevalues], start=[])

        optimized_chain = optimize_attr_updates_chain(
            self.attr_updates_chain_from_mod_objs_computation_chains + attr_updates_chain_from_attributes_updates)

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
            hourly_quantities.replace_in_mod_obj_container_without_recomputation(new_value)
            self.filtered_hourly_quantities.append(new_value)

    def replace_ancestors_not_in_computation_chain_by_copies(self):
        copies = []
        for ancestor_to_replace_by_copy in self.ancestors_to_replace_by_copies:
            # Replace all ancestors not in computation chain by their copy so that the original calculation graph
            # will remain unchanged when the simulation is over
            ancestor_copy = copy(ancestor_to_replace_by_copy)
            ancestor_to_replace_by_copy.replace_in_mod_obj_container_without_recomputation(ancestor_copy)
            copies.append(ancestor_copy)

        return copies

    def change_input_values(self):
        for old_value, new_value in zip(self.old_sourcevalues, self.new_sourcevalues):
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)

    def save_recomputed_values(self):
        for expl_obj in self.values_to_recompute:
            self.recomputed_values.append(
                getattr(expl_obj.modeling_obj_container, expl_obj.attr_name_in_mod_obj_container))

    def reset_pre_simulation_values(self):
        for previous_value in (
                self.old_sourcevalues + self.values_to_recompute + self.hourly_quantities_to_filter +
                self.ancestors_to_replace_by_copies + self.old_mod_obj_links):
            previous_value.replace_in_mod_obj_container_without_recomputation(previous_value)

    def set_simulation_values(self):
        for new_value in (
                self.new_sourcevalues + self.recomputed_values + self.filtered_hourly_quantities +
                self.replaced_ancestors_copies + self.new_mod_obj_links):
            new_value.replace_in_mod_obj_container_without_recomputation(new_value)
