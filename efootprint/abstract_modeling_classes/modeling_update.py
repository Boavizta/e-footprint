from time import perf_counter
from typing import List

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_attr_updates_chain
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import (
    ObjectLinkedToModelingObj, ObjectLinkedToModelingObjBase)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import (
    ModelingObject, flush_cached_properties_system_wide, optimize_mod_objs_computation_chain)
from efootprint.logger import logger


def compute_attr_updates_chain_from_mod_objs_computation_chain(mod_objs_computation_chain: List[ModelingObject]):
    attr_updates_chain = []
    for mod_obj in mod_objs_computation_chain:
        for calculated_attribute in mod_obj.calculated_attributes:
            attr_updates_chain.append(getattr(mod_obj, calculated_attribute))

    return attr_updates_chain


class ModelingUpdate:
    def __init__(self, changes_list: List[List[ObjectLinkedToModelingObj | list | dict]]):
        start = perf_counter()
        self.system = None
        for change in changes_list:
            changed_val = change[0]
            if isinstance(changed_val, ObjectLinkedToModelingObjBase) and changed_val.modeling_obj_container.systems:
                self.system = changed_val.modeling_obj_container.systems[0]
                break
        self.changes_list = changes_list
        self.parse_changes_list()

        self.mod_objs_computation_chain = self.compute_mod_objs_computation_chain()
        if self.mod_objs_computation_chain:
            logger.info(f"{len(self.mod_objs_computation_chain)} recomputed objects: "
                        f"{[mod_obj.name for mod_obj in self.mod_objs_computation_chain]}")
        self.apply_within_class_sort_logics()
        self.attr_updates_chain_from_mod_objs_computation_chains = (
            compute_attr_updates_chain_from_mod_objs_computation_chain(self.mod_objs_computation_chain))
        self.values_to_recompute = self.generate_optimized_attr_updates_chain()

        self.recomputed_values = []
        self.apply_changes()
        try:
            for new_sourcevalue in self.new_sourcevalues:
                mod_obj_container = new_sourcevalue.modeling_obj_container
                mod_obj_container.check_belonging_to_authorized_values(
                    new_sourcevalue.attr_name_in_mod_obj_container, new_sourcevalue,
                    mod_obj_container.attributes_with_depending_values())

            self.recompute_attributes()
        except Exception as e:
            logger.error("An error occurred during attribute recomputation. Resetting to previous values.")
            self.reset_values()
            e.args = (f"Error occurred while computing changes. All changes have been reset."
                      f"\nOriginal error:\n {e}",) + e.args[1:]
            raise e

        flush_cached_properties_system_wide(
            self.mod_objs_computation_chain + ([self.system] if self.system is not None else []))
        compute_time_ms = round(1000 * (perf_counter() - start), 1)
        avg_compute_time_per_value = round(compute_time_ms / len(self.values_to_recompute), 2)\
            if self.values_to_recompute else 0
        logger.info(f"{len(self.changes_list)} changes lead to {len(self.values_to_recompute)} update computations "
                    f"done in {compute_time_ms} ms (avg {avg_compute_time_per_value} ms per computation).")

    @property
    def previous_and_new_objects_organized_in_sections(self):
        return [
            ["direct changes", [change[0] for change in self.changes_list], [change[1] for change in self.changes_list]],
            ["recomputed values", self.values_to_recompute, self.recomputed_values]
        ]

    def parse_changes_list(self):
        indexes_to_skip = []
        index = 0
        while index < len(self.changes_list):
            old_value, new_value = self.changes_list[index]
            assert isinstance(old_value, ObjectLinkedToModelingObjBase), \
                              f"{old_value} should be an ObjectLinkedToModelingObjBase but is of type {type(old_value)}"
            if new_value is None:
                assert isinstance(old_value, ExplainableObject)
                self.changes_list[index][1] = EmptyExplainableObject()
            else:
                mod_obj_container = old_value.modeling_obj_container
                if old_value.dict_container is None:
                    mod_obj_container.check_input_value_type_positivity_and_unit(
                        old_value.attr_name_in_mod_obj_container, new_value)

            if isinstance(new_value, list):
                from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
                self.changes_list[index][1] = ListLinkedToModelingObj(new_value)
            if isinstance(new_value, dict):
                from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict as EOD
                if not isinstance(new_value, EOD):
                    dict_class = type(old_value) if isinstance(old_value, EOD) else EOD
                    self.changes_list[index][1] = dict_class(new_value)
            if isinstance(new_value, ModelingObject):
                self.changes_list[index][1] = ContextualModelingObjectAttribute(new_value)
                if old_value.attr_name_in_mod_obj_container in mod_obj_container.attribute_update_entanglements:
                    changes_to_add = mod_obj_container.attribute_update_entanglements[
                        old_value.attr_name_in_mod_obj_container]([old_value, new_value])
                    self.changes_list += changes_to_add

            if not isinstance(self.changes_list[index][1], ObjectLinkedToModelingObjBase):
                raise ValueError(
                    f"New e-footprint attributes should be ObjectLinkedToModelingObjBase,"
                    f" got {old_value} of type {type(old_value)} trying to be set to an object "
                    f"of type {type(new_value)}")

            values_are_equal = old_value == new_value
            if values_are_equal and isinstance(old_value, dict) and isinstance(new_value, dict):
                # dict equality ignores key order, but order is meaningful for ExplainableObjectDicts
                # (e.g. usage journey step order), so a pure reorder is a real change, not a no-op.
                values_are_equal = list(old_value.keys()) == list(new_value.keys())
            if values_are_equal:
                if old_value is new_value:
                    logger.warning(
                        f"{old_value.id} is updated to itself. "
                        f"It happens when using my_mod_obj.list_attribute += other list syntax. "
                        f"Otherwise this is surprising, you might want to double check your action. "
                        f"The update will be skipped.")
                else:
                    logger.warning(
                        f"{old_value.id} is updated to a value equal to its current one. "
                        f"The update will be skipped.")
                indexes_to_skip.append(index)
            index += 1

        for index in sorted(indexes_to_skip, reverse=True):
            del self.changes_list[index]

    def compute_mod_objs_computation_chain(self):
        from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
            elif isinstance(old_value, ExplainableObjectDict):
                mod_objs_computation_chain += (
                    old_value.modeling_obj_container.compute_mod_objs_computation_chain_from_old_and_new_dicts(
                        old_value, new_value, optimize_chain=False))

        optimized_chain = optimize_mod_objs_computation_chain(mod_objs_computation_chain)

        return optimized_chain

    def apply_changes(self):
        for old_value, new_value in self.changes_list:
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)
        self.updated_values_set = True

    def revert_changes(self):
        for old_value, new_value in self.changes_list:
            new_value.replace_in_mod_obj_container_without_recomputation(old_value)
        self.updated_values_set = False

    def apply_within_class_sort_logics(self):
        self.apply_changes()
        result = []
        i = 0
        chain = self.mod_objs_computation_chain
        while i < len(chain):
            canonical_cls = chain[i].efootprint_class
            j = i + 1
            while j < len(chain) and chain[j].efootprint_class == canonical_cls:
                j += 1
            result.extend(canonical_cls.sort_within_computation_chain(chain[i:j]))
            i = j
        self.mod_objs_computation_chain = result
        self.revert_changes()

    def recompute_attributes(self):
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
            self.recomputed_values.append(recomputed_value)

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
        return optimize_attr_updates_chain(
            attr_updates_chain_from_attributes_updates + self.attr_updates_chain_from_mod_objs_computation_chains)

    def reset_values(self):
        if self.updated_values_set:
            for section_name, previous_values, new_values in self.previous_and_new_objects_organized_in_sections:
                logger.info(f"Resetting {section_name} from {len(new_values)} updated values")
                for new_value, previous_value in zip(new_values, previous_values):
                    new_value.replace_in_mod_obj_container_without_recomputation(previous_value)
                self.updated_values_set = False
