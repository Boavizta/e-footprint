from time import perf_counter
from typing import List

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import (
    ObjectLinkedToModelingObj, ObjectLinkedToModelingObjBase)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import (
    ModelingObject, get_instance_attributes, pull_guard_slots, pull_invalidated_slots)
from efootprint.abstract_modeling_classes.reactive_core import (
    collect_invalidated_slots, computed_slots, invalidate, prune_stale_computed_dict_keys, slot_of_attached_value)
from efootprint.logger import logger


class ModelingUpdate:
    """Transactional model update: apply the changes, invalidate the slots they touch (the deletion
    wave voids every dependent), then eagerly pull the configured outputs so computation errors
    surface now — and on error, restore the inputs, re-invalidate, and recompute the restored state.

    ``eager_outputs`` configures what recomputes at update time, as (modeling object, attribute name)
    pairs. The default (None) reads the affected system's total footprint — the whole footprint cone
    of the change recomputes and anything outside it stays void until read. Tight loops pass an empty
    collection to skip eager recomputation entirely (values compute on the next read). Validation
    slots the change invalidated always recompute, whatever the eager set."""

    def __init__(self, changes_list: List[List[ObjectLinkedToModelingObj | list | dict]],
                 eager_outputs: list | tuple | None = None):
        start = perf_counter()
        self.system = None
        for change in changes_list:
            changed_val = change[0]
            if isinstance(changed_val, ObjectLinkedToModelingObjBase) and changed_val.modeling_obj_container.systems:
                self.system = changed_val.modeling_obj_container.systems[0]
                break
        self.eager_outputs = eager_outputs
        self.changes_list = changes_list
        self.parse_changes_list()
        self.newly_linked_mod_objs = self.collect_newly_linked_mod_objs()

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

        compute_time_ms = round(1000 * (perf_counter() - start), 1)
        logger.info("%s changes invalidated %s slots, recomputed in %s ms.",
                    len(self.changes_list), recomputed_slots_count, compute_time_ms)

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

    def collect_newly_linked_mod_objs(self) -> list:
        """The ModelingObjects the changes link into the model — a replaced single link, added list
        members, added dict keys — expanded with everything they point to, since a newly attached
        object can bring a whole subtree whose slots have never been computed."""
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict

        def unwrap(value):
            return value._value if isinstance(value, ContextualModelingObjectAttribute) else value

        directly_added = []
        for old_value, new_value in self.changes_list:
            if isinstance(new_value, ContextualModelingObjectAttribute):
                directly_added.append(unwrap(new_value))
            elif isinstance(new_value, list):
                old_ids = {elt.id for elt in old_value} if isinstance(old_value, list) else set()
                directly_added += [unwrap(elt) for elt in new_value if elt.id not in old_ids]
            elif isinstance(new_value, ExplainableObjectDict):
                old_ids = {key.id for key in dict.keys(old_value)
                           if isinstance(key, ModelingObject)} if isinstance(old_value, dict) else set()
                directly_added += [unwrap(key) for key in dict.keys(new_value)
                                   if isinstance(key, ModelingObject) and key.id not in old_ids]

        collected = {}
        objects_to_visit = directly_added
        while objects_to_visit:
            mod_obj = objects_to_visit.pop()
            if mod_obj.id in collected:
                continue
            collected[mod_obj.id] = mod_obj
            objects_to_visit += [unwrap(linked_obj) for linked_obj in mod_obj.mod_obj_attributes]
            for dict_attr in get_instance_attributes(mod_obj, ExplainableObjectDict).values():
                objects_to_visit += [unwrap(key) for key in dict.keys(dict_attr) if isinstance(key, ModelingObject)]
        return list(collected.values())

    def pull_guard_slots_of_newly_linked_objects(self):
        """Guard slots exist to reject invalid states, but a newly linked object's guards have never
        been computed: they have no dependency edges yet, so no invalidation wave can reach them and
        neither the wave-visited guard pull nor the footprint cone would run them. Pull them all
        explicitly (already-cached ones return instantly), so an invalid new link fails at update
        time exactly like an invalid input edit."""
        for mod_obj in self.newly_linked_mod_objs:
            for name, descriptor in computed_slots(mod_obj.efootprint_class).items():
                if descriptor.guard or name.endswith("_validation"):
                    getattr(mod_obj, name)

    def pull_eagerly(self, visited_slots) -> int:
        """Recompute the invalidated validation slots (plus every guard slot of newly linked
        objects), then the eager outputs: the configured (object, attribute) pairs, or by default
        the affected system's total footprint. A change on objects linked to no system falls back to
        recomputing the whole invalidated cone — there is no footprint to pull errors through, and
        detached subgraphs are small. Returns the number of slots voided by the wave."""
        prune_stale_computed_dict_keys(visited_slots)
        pull_guard_slots(visited_slots)
        self.pull_guard_slots_of_newly_linked_objects()
        if self.eager_outputs is not None:
            for mod_obj, attr_name in self.eager_outputs:
                getattr(mod_obj, attr_name)
        elif self.system is not None:
            self.system.total_footprint
        else:
            pull_invalidated_slots(visited_slots)
        return len(visited_slots)

    def rollback(self):
        """Restore the inputs and relationships, invalidate again, and recompute the restored state so
        the model stays fully cached and consistent after a rejected update."""
        # The rejected links are undone: their objects are detached again, so re-pulling their guard
        # slots would re-raise the very error being rolled back.
        self.newly_linked_mod_objs = []
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
