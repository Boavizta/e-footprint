from time import perf_counter
from typing import List

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import (
    ObjectLinkedToModelingObj, ObjectLinkedToModelingObjBase)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import (
    ModelingObject, flush_cached_properties_system_wide, pull_invalidated_slots, pull_slots_system_wide)
from efootprint.abstract_modeling_classes.reactive_core import (
    collect_invalidated_slots, invalidate, slot_of_attached_value)
from efootprint.logger import logger


class ModelingUpdate:
    """Transactional model update: apply the changes, invalidate the slots they touch (the deletion
    wave voids every dependent), then eagerly pull every slot back to cached so computation errors
    surface now — and on error, restore the inputs, re-invalidate, and recompute the restored state."""

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

        self.changed_slots = [slot_of_attached_value(old_value) for old_value, new_value in self.changes_list]

        with collect_invalidated_slots() as visited_slots:
            self.apply_changes()
            invalidate(*self.changed_slots)

        try:
            for new_sourcevalue in self.new_sourcevalues:
                mod_obj_container = new_sourcevalue.modeling_obj_container
                mod_obj_container.check_belonging_to_authorized_values(
                    new_sourcevalue.attr_name_in_mod_obj_container, new_sourcevalue,
                    mod_obj_container.attributes_with_depending_values())

            recomputed_slots_count = self.pull_eagerly(visited_slots)
        except Exception as e:
            logger.error("An error occurred during attribute recomputation. Resetting to previous values.")
            self.rollback()
            e.args = (f"Error occurred while computing changes. All changes have been reset."
                      f"\nOriginal error:\n {e}",) + e.args[1:]
            raise e

        flush_cached_properties_system_wide(
            [old_value.modeling_obj_container for old_value, new_value in self.changes_list
             if old_value.modeling_obj_container is not None] + ([self.system] if self.system is not None else []))
        compute_time_ms = round(1000 * (perf_counter() - start), 1)
        logger.info(f"{len(self.changes_list)} changes invalidated {recomputed_slots_count} slots, "
                    f"recomputed in {compute_time_ms} ms.")

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

    def apply_changes(self):
        for old_value, new_value in self.changes_list:
            old_value.replace_in_mod_obj_container_without_recomputation(new_value)

    def pull_eagerly(self, visited_slots) -> int:
        """Recompute the invalidated cone: pull every slot of the system when one is involved (the
        transitional every-slot-cached eager set), plus every slot the wave visited — objects the
        change detached from the system keep consistent values and bookkeeping, exactly as the eager
        engine recomputed them. Returns the number of slots voided by the wave."""
        if self.system is not None:
            pull_slots_system_wide([self.system])
        pull_invalidated_slots(visited_slots)
        return len(visited_slots)

    def rollback(self):
        """Restore the inputs and relationships, invalidate again, and recompute the restored state so
        the model stays fully cached and consistent after a rejected update."""
        with collect_invalidated_slots() as visited_slots:
            for old_value, new_value in self.changes_list:
                new_value.replace_in_mod_obj_container_without_recomputation(old_value)
            invalidate(*self.changed_slots)
        self.pull_eagerly(visited_slots)

    @property
    def old_sourcevalues(self):
        return [old_value for old_value, new_value in self.changes_list if isinstance(old_value, ExplainableObject)]

    @property
    def new_sourcevalues(self):
        return [new_value for old_value, new_value in self.changes_list if isinstance(old_value, ExplainableObject)]
