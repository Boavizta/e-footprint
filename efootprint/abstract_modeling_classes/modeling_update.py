from copy import copy
from datetime import datetime
from typing import List

import numpy as np

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_attr_updates_chain
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, optimize_mod_objs_computation_chain
from efootprint.logger import logger


def compute_attr_updates_chain_from_mod_objs_computation_chain(mod_objs_computation_chain: List[ModelingObject]):
    attr_updates_chain = []
    for mod_obj in mod_objs_computation_chain:
        for calculated_attribute in mod_obj.calculated_attributes:
            attr_updates_chain.append(getattr(mod_obj, calculated_attribute))

    return attr_updates_chain


class ModelingUpdate:
    def __init__(
            self, changes_list: List[List[ObjectLinkedToModelingObj | list | dict]], simulation_date: datetime = None):
        self.updated_values_set = False
        self.system = None
        for change in changes_list:
            changed_val = change[0]
            if isinstance(changed_val, ObjectLinkedToModelingObj) and changed_val.modeling_obj_container.systems:
                self.system = changed_val.modeling_obj_container.systems[0]
                break
        self.changes_list = changes_list
        self.parse_changes_list()
        if self.changes_list and self.system:
            self.system.previous_total_energy_footprints_sum_over_period = (
                self.system.total_energy_footprint_sum_over_period)
            self.system.previous_total_fabrication_footprints_sum_over_period = \
                self.system.total_fabrication_footprint_sum_over_period
            self.system.previous_change = changes_list
            self.system.all_changes += changes_list

        self.simulation_date = simulation_date
        if simulation_date is not None:
            assert self.system is not None
            if simulation_date.tzinfo is None:
                raise ValueError(
                    f"Simulation date {simulation_date} should be timezone aware. "
                    f"Please use a timezone aware datetime object by setting its tzinfo attribute.")
            self.system.simulation = self

        self.mod_objs_computation_chain = self.compute_mod_objs_computation_chain()
        if self.mod_objs_computation_chain:
            logger.info(f"{len(self.mod_objs_computation_chain)} recomputed objects: "
                        f"{[mod_obj.id for mod_obj in self.mod_objs_computation_chain]}")
        self.attr_updates_chain_from_mod_objs_computation_chains = (
            compute_attr_updates_chain_from_mod_objs_computation_chain(self.mod_objs_computation_chain))
        self.values_to_recompute = self.generate_optimized_attr_updates_chain()

        self.ancestors_not_in_computation_chain = []
        self.hourly_quantities_to_filter = []
        self.filtered_hourly_quantities = []
        self.ancestors_to_replace_by_copies = []
        self.replaced_ancestors_copies = []
        if self.simulation_date is not None:
            self.make_simulation_specific_operations()

        self.apply_changes()
        for new_sourcevalue in self.new_sourcevalues:
            mod_obj_container = new_sourcevalue.modeling_obj_container
            mod_obj_container.check_belonging_to_authorized_values(
                new_sourcevalue.attr_name_in_mod_obj_container, new_sourcevalue, mod_obj_container.list_values(),
                mod_obj_container.conditional_list_values(), mod_obj_container.attributes_with_depending_values())
        self.recomputed_values = self.recompute_attributes()
        self.updated_values_set = True

        if self.simulation_date is not None:
            self.link_simulated_and_baseline_twins()

        self.previous_and_new_objects_organized_in_sections = [
            ["direct changes", [change[0] for change in self.changes_list], [change[1] for change in self.changes_list]],
            ["filtered hourly quantities", self.hourly_quantities_to_filter, self.filtered_hourly_quantities],
            ["replaced ancestors copies", self.ancestors_to_replace_by_copies, self.replaced_ancestors_copies],
            ["recomputed values", self.values_to_recompute, self.recomputed_values]
        ]

        if simulation_date is not None:
            self.reset_values()

    def parse_changes_list(self):
        indexes_to_skip = []
        for index in range(len(self.changes_list)):
            old_value, new_value = self.changes_list[index]
            assert isinstance(old_value, ObjectLinkedToModelingObj), \
                              f"{old_value} should be an ObjectLinkedToModelingObj but is of type {type(old_value)}"
            if new_value is None:
                assert isinstance(old_value, ExplainableObject)
                self.changes_list[index][1] = EmptyExplainableObject()
            else:
                mod_obj_container = old_value.modeling_obj_container
                mod_obj_container.check_input_value_type_positivity_and_unit(
                    old_value.attr_name_in_mod_obj_container, new_value, mod_obj_container.default_values())

            if isinstance(new_value, list):
                from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
                self.changes_list[index][1] = ListLinkedToModelingObj(new_value)
            if isinstance(new_value, ModelingObject):
                self.changes_list[index][1] = ContextualModelingObjectAttribute(new_value)

            if not isinstance(self.changes_list[index][1], ObjectLinkedToModelingObj):
                raise ValueError(
                    f"New e-footprint attributes should be ObjectLinkedToModelingObj,"
                    f" got {old_value} of type {type(old_value)} trying to be set to an object "
                    f"of type {type(new_value)}")

            if old_value == new_value:
                logger.warning(
                    f"{old_value.id} is updated to itself. "
                    f"It happens when using my_mod_obj.list_attribute += other list syntax. "
                    f"Otherwise This is surprising, you might want to double check your action. "
                    f"The link update logic will be skipped.")
                indexes_to_skip.append(index)

        for index in sorted(indexes_to_skip, reverse=True):
            del self.changes_list[index]

    def compute_mod_objs_computation_chain(self):
        from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
        mod_objs_computation_chain = []
        for old_value, new_value in self.changes_list:
            if isinstance(old_value, ContextualModelingObjectAttribute):
                mod_objs_computation_chain += (
                    old_value.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_modeling_objs(
                        old_value, new_value, optimize_chain=False))
            elif isinstance(old_value, ListLinkedToModelingObj):
                mod_objs_computation_chain += (
                    old_value.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_lists(
                        old_value, new_value, optimize_chain=False))

        optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)

        return optimized_chain

    def apply_changes(self):
        for old_value, new_value in self.changes_list:
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)

    def make_simulation_specific_operations(self):
        assert self.simulation_date is not None
        self.ancestors_not_in_computation_chain = self.compute_ancestors_not_in_computation_chain()
        self.hourly_quantities_to_filter = self.compute_hourly_quantities_to_filter()
        if self.mod_objs_computation_chain:
            # The simulation will change the calculation graph, so we need to replace all ancestors not in
            # computation chain by their copies to keep the original calculation graph unchanged
            self.ancestors_to_replace_by_copies = [
                ancestor for ancestor in self.ancestors_not_in_computation_chain
                if ancestor.id not in [value.id for value in self.hourly_quantities_to_filter]]
            self.replaced_ancestors_copies = self.replace_ancestors_not_in_computation_chain_by_copies()
        self.filter_hourly_quantities_to_filter()

    def recompute_attributes(self):
        recomputed_values = []
        for value_to_recompute in self.values_to_recompute:
            attr_name_in_mod_obj_container = value_to_recompute.attr_name_in_mod_obj_container
            modeling_obj_container = value_to_recompute.modeling_obj_container
            key_in_dict = None
            if value_to_recompute.dict_container is not None:
                key_in_dict = value_to_recompute.key_in_dict
            if not key_in_dict:
                logger.debug(f"Recomputing {attr_name_in_mod_obj_container} in {modeling_obj_container.id}")
                value_to_recompute.update_function()
                recomputed_value = getattr(modeling_obj_container, attr_name_in_mod_obj_container)
            else:
                logger.debug(f"Recomputing {attr_name_in_mod_obj_container} in {modeling_obj_container.id} "
                             f"with key {key_in_dict.id}")
                value_to_recompute.update_function(key_in_dict)
                recomputed_value = getattr(modeling_obj_container, attr_name_in_mod_obj_container)[key_in_dict]
            recomputed_values.append(recomputed_value)

        return recomputed_values

    @property
    def old_sourcevalues(self):
        return [old_value for old_value, new_value in self.changes_list if isinstance(old_value, ExplainableObject)]

    @property
    def new_sourcevalues(self):
        return [new_value for old_value, new_value in self.changes_list if isinstance(old_value, ExplainableObject)]

    def generate_optimized_attr_updates_chain(self):
        attr_updates_chain_from_attributes_updates = sum(
            [old_value.attr_updates_chain for old_value in self.old_sourcevalues], start=[])

        # Necessary to do the sum in this order because calculations from modeling objects computation chains must be
        # done after the calculations from input updates.
        optimized_chain = optimize_attr_updates_chain(
            attr_updates_chain_from_attributes_updates + self.attr_updates_chain_from_mod_objs_computation_chains)

        optimized_chain_without_previous_nor_initial_values = [
            attr for attr in optimized_chain if not attr.attr_name_in_mod_obj_container.startswith("previous_")
                                                and not attr.attr_name_in_mod_obj_container.startswith("initial_")]

        return optimized_chain_without_previous_nor_initial_values

    def compute_ancestors_not_in_computation_chain(self):
        all_ancestors_of_values_to_recompute = sum(
            [value.all_ancestors_with_id for value in self.values_to_recompute], start=[])
        deduplicated_all_ancestors_of_values_to_recompute = []
        for ancestor in all_ancestors_of_values_to_recompute:
            if ancestor.id not in [elt.id for elt in deduplicated_all_ancestors_of_values_to_recompute]:
                deduplicated_all_ancestors_of_values_to_recompute.append(ancestor)
        values_to_recompute_attribute_ids = [elt.attribute_id for elt in self.values_to_recompute]
        old_sourcevalues_attribute_ids = [old_value.attribute_id for old_value in self.old_sourcevalues]
        ancestors_not_in_computation_chain = [
            ancestor for ancestor in deduplicated_all_ancestors_of_values_to_recompute
            if ancestor.attribute_id not in values_to_recompute_attribute_ids + old_sourcevalues_attribute_ids]

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
            if min_date.tzinfo is None:
                # Should only be the case for UsagePattern’s hourly_usage_journeys
                min_date = min_date.replace(tzinfo=ancestor.modeling_obj_container.country.timezone.value)
            if max_date.tzinfo is None:
                max_date = max_date.replace(tzinfo=ancestor.modeling_obj_container.country.timezone.value)
            if global_min_date is None:
                global_min_date = min_date
            if global_max_date is None:
                global_max_date = max_date
            global_min_date = min(min_date, global_min_date)
            global_max_date = max(max_date, global_max_date)
            if self.simulation_date <= max_date:
                hourly_quantities_to_filter.append(ancestor)

        if not (global_min_date <= self.simulation_date <= global_max_date):
            raise ValueError(
                f"Can’t start a simulation on the {self.simulation_date} because "
                f"{self.simulation_date}doesn’t belong to the existing modeling period "
                f"{global_min_date} to {global_max_date}")

        return hourly_quantities_to_filter

    def filter_hourly_quantities_to_filter(self):
        for hourly_quantities in self.hourly_quantities_to_filter:
            if hourly_quantities.value.index.tz is None:
                # Should only be the case for UsagePattern’s hourly_usage_journeys
                filtering_index = hourly_quantities.value.index.tz_localize(
                    hourly_quantities.modeling_obj_container.country.timezone.value,
                    nonexistent="shift_forward", ambiguous=np.full(len(hourly_quantities.value), fill_value=True))
            else:
                filtering_index = hourly_quantities.value.index
            new_value = ExplainableHourlyQuantities(
                hourly_quantities.value[filtering_index >= self.simulation_date],
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

    def reset_values(self):
        if self.updated_values_set:
            for section_name, previous_values, new_values in self.previous_and_new_objects_organized_in_sections:
                logger.info(f"Resetting {section_name} from {len(new_values)} updated values")
                for new_value, previous_value in zip(new_values, previous_values):
                    new_value.replace_in_mod_obj_container_without_recomputation(previous_value)
                self.updated_values_set = False

    def set_updated_values(self):
        if not self.updated_values_set:
            for section_name, previous_values, new_values in self.previous_and_new_objects_organized_in_sections:
                logger.info(f"Setting {section_name} from {len(previous_values)} previous values")
                for new_value, previous_value in zip(new_values, previous_values):
                    previous_value.replace_in_mod_obj_container_without_recomputation(new_value)
                self.updated_values_set = True

    def link_simulated_and_baseline_twins(self):
        assert self.simulation_date is not None
        for value_to_recompute, recomputed_value in zip(self.values_to_recompute, self.recomputed_values):
            value_to_recompute.simulation_twin = recomputed_value
            recomputed_value.baseline_twin = value_to_recompute
            value_to_recompute.simulation = self
            recomputed_value.simulation = self
