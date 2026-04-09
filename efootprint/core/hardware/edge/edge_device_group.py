from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.constants.units import u


class EdgeDeviceGroup(ModelingObject):
    default_values = {}
    classes_outside_init_params_needed_for_generating_from_json = []

    def __init__(self, name: str,
                 sub_group_counts: ExplainableObjectDict = None,
                 edge_device_counts: ExplainableObjectDict = None):
        super().__init__(name)
        if sub_group_counts is None:
            sub_group_counts = ExplainableObjectDict()
        if edge_device_counts is None:
            edge_device_counts = ExplainableObjectDict()
        self.sub_group_counts = ExplainableObjectDict(sub_group_counts)
        self.edge_device_counts = ExplainableObjectDict(edge_device_counts)
        self.counts_validation = EmptyExplainableObject()
        self.effective_nb_of_units_within_root = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        # Child groups and edge devices depend on this group's effective_nb_of_units_within_root.
        # When sub-groups are shared across multiple roots, the BFS + dedup-keep-last mechanism
        # in mod_objs_computation_chain / optimize_mod_objs_computation_chain guarantees
        # topological ordering (parents computed before children). This relies on:
        # - BFS re-adding already-processed objects when discovered from a later parent
        # - Dedup keeping the last occurrence, which is after all parents
        # Cycles are structurally impossible (a group cannot be its own ancestor).
        return list(self.sub_group_counts.keys()) + list(self.edge_device_counts.keys())

    @property
    def calculated_attributes(self):
        return ["counts_validation", "effective_nb_of_units_within_root"]

    def _find_parent_groups(self) -> List["EdgeDeviceGroup"]:
        from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import (
            ContextualModelingObjectDictKey)

        return list(dict.fromkeys([
            contextual_container.modeling_obj_container
            for contextual_container in self.contextual_modeling_obj_containers
            if (
                isinstance(contextual_container, ContextualModelingObjectDictKey)
                and isinstance(contextual_container.modeling_obj_container, EdgeDeviceGroup)
            )
        ]))

    def _find_root_groups(self) -> List["EdgeDeviceGroup"]:
        parent_groups = self._find_parent_groups()
        if not parent_groups:
            return [self]  # I am a root group
        root_groups = []
        for parent in parent_groups:
            root_groups += parent._find_root_groups()
        return list(dict.fromkeys(root_groups))

    def _find_all_ancestor_groups(self) -> List["EdgeDeviceGroup"]:
        """Collect all ancestor groups (parents, grandparents, etc.) of this group."""
        ancestors = []
        for parent in self._find_parent_groups():
            if parent not in ancestors:
                ancestors.append(parent)
            for ancestor in parent._find_all_ancestor_groups():
                if ancestor not in ancestors:
                    ancestors.append(ancestor)
        return ancestors

    def update_counts_validation(self):
        for key, count in list(self.sub_group_counts.items()) + list(self.edge_device_counts.items()):
            if not count.value.check("[]"):
                raise ValueError(
                    f"Count for {key.name} in {self.name} should be dimensionless "
                    f"but has units {count.value.units}")
            if count.value.magnitude < 0:
                raise ValueError(
                    f"Count for {key.name} in {self.name} should be positive "
                    f"but is {count.value.magnitude}")
        self.counts_validation = EmptyExplainableObject()

    def update_effective_nb_of_units_within_root(self):
        parent_groups = self._find_parent_groups()
        if not parent_groups:
            # Root group: effective count is 1
            self.effective_nb_of_units_within_root = ExplainableQuantity(
                1 * u.dimensionless, f"{self.name} is a root group")
        else:
            # Sum contributions from all parents. When a group appears in multiple
            # parent hierarchies, its effective count is the sum of contributions from
            # each parent, allowing shared sub-groups to be counted proportionally
            # across the full hierarchy.
            effective_nb = sum(
                [parent.sub_group_counts[self] * parent.effective_nb_of_units_within_root
                 for parent in parent_groups],
                start=EmptyExplainableObject())
            self.effective_nb_of_units_within_root = effective_nb.set_label(
                f"Effective nb of {self.name} within root group")

    def self_delete(self):
        parent_groups = self._find_parent_groups()
        if parent_groups:
            raise PermissionError(
                f"You can’t delete {self.name} because it is referenced in sub_group_counts of "
                f"{','.join(parent.name for parent in parent_groups)}.")

        if self.sub_group_counts or self.edge_device_counts:
            new_sub_group_counts = ExplainableObjectDict()
            new_sub_group_counts.trigger_modeling_updates = self.sub_group_counts.trigger_modeling_updates
            new_edge_device_counts = ExplainableObjectDict()
            new_edge_device_counts.trigger_modeling_updates = self.edge_device_counts.trigger_modeling_updates

            if self.trigger_modeling_updates:
                ModelingUpdate([
                    [self.sub_group_counts, new_sub_group_counts],
                    [self.edge_device_counts, new_edge_device_counts],
                ])
            else:
                self.sub_group_counts = new_sub_group_counts
                self.edge_device_counts = new_edge_device_counts

        super().self_delete()
