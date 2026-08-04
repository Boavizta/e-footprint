from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    ExplainableObjectDict, WeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.abstract_modeling_classes.reactive_core import ReverseCollection, computed_attribute


class EdgeDeviceGroup(ModelingObject):
    """A composition node grouping {class:EdgeDevice}s and other {class:EdgeDeviceGroup}s with multiplicities. Lets a deployment template (a building, a vehicle, a fleet) describe how many of each device it contains, with arbitrary nesting."""

    pitfalls = (
        "Cycles in the group hierarchy are forbidden — a group cannot contain itself transitively. The model "
        "raises error if a cycle is introduced. Counts in {param:EdgeDeviceGroup.sub_group_counts} and "
        "{param:EdgeDeviceGroup.edge_device_counts} must be dimensionless and non-negative.")

    param_descriptions = {
        "sub_group_counts": (
            "Mapping from child {class:EdgeDeviceGroup} to how many copies of it this group contains."),
        "edge_device_counts": (
            "Mapping from {class:EdgeDevice} to how many of it this group contains."),
    }

    default_values = {}

    weight_labels = {"sub_group_counts": "Count in group", "edge_device_counts": "Count in group"}

    parent_groups = ReverseCollection("EdgeDeviceGroup")

    def __init__(self, name: str,
                 sub_group_counts: WeightedExplainableObjectDict["EdgeDeviceGroup"] = None,
                 edge_device_counts: WeightedExplainableObjectDict["EdgeDevice"] = None):
        super().__init__(name)
        self.sub_group_counts = to_weighted_explainable_object_dict(
            sub_group_counts, weight_label=self.weight_labels["sub_group_counts"])
        self.edge_device_counts = to_weighted_explainable_object_dict(
            edge_device_counts, weight_label=self.weight_labels["edge_device_counts"])



    def _find_root_groups(self) -> List["EdgeDeviceGroup"]:
        parent_groups = self.parent_groups
        if not parent_groups:
            return [self]  # I am a root group
        root_groups = []
        for parent in parent_groups:
            root_groups += parent._find_root_groups()
        return list(dict.fromkeys(root_groups))

    def _find_all_ancestor_groups(self, _visited=None) -> List["EdgeDeviceGroup"]:
        """Collect all ancestor groups (parents, grandparents, etc.) of this group.

        Uses a visited set to handle cycles gracefully instead of infinite recursion.
        """
        if _visited is None:
            _visited = set()
        ancestors = []
        for parent in self.parent_groups:
            if parent in _visited:
                continue
            _visited.add(parent)
            if parent not in ancestors:
                ancestors.append(parent)
            for ancestor in parent._find_all_ancestor_groups(_visited):
                if ancestor not in ancestors:
                    ancestors.append(ancestor)
        return ancestors

    @computed_attribute(guard=True)
    def no_cycle_validation(self):
        """Validates that the group does not contain itself transitively, and that no nested sub-group does either."""
        ancestors = self._find_all_ancestor_groups()
        if self in ancestors:
            raise ValueError(f"Cycle detected: {self.name} is its own ancestor.")
        for sub_group in self.sub_group_counts:
            if sub_group in sub_group._find_all_ancestor_groups():
                raise ValueError(f"Cycle detected: {sub_group.name} is its own ancestor via {self.name}.")
        return EmptyExplainableObject()

    @computed_attribute
    def effective_nb_of_units_within_root(self):
        """How many copies of this group exist when the hierarchy is unrolled from the root group: 1 for a root group, otherwise the sum across each parent of (parent's effective count) times (count of this group within that parent)."""
        parent_groups = self.parent_groups
        if not parent_groups:
            # Root group: effective count is 1
            return ExplainableQuantity(
                1 * u.dimensionless, f"root group count of 1")
        # Sum contributions from all parents. When a group appears in multiple
        # parent hierarchies, its effective count is the sum of contributions from
        # each parent, allowing shared sub-groups to be counted proportionally
        # across the full hierarchy.
        effective_nb = sum(
            [parent.sub_group_counts[self] * parent.effective_nb_of_units_within_root
             for parent in parent_groups],
            start=EmptyExplainableObject())
        return effective_nb.set_label(
            f"Effective nb within root group")

    def self_delete(self):
        parent_groups = self.parent_groups
        if parent_groups:
            raise PermissionError(
                f"You can’t delete {self.name} because it is referenced in sub_group_counts of "
                f"{','.join(parent.name for parent in parent_groups)}.")

        if self.sub_group_counts or self.edge_device_counts:
            new_sub_group_counts = ExplainableObjectDict()
            new_edge_device_counts = ExplainableObjectDict()
            ModelingUpdate([
                [self.sub_group_counts, new_sub_group_counts],
                [self.edge_device_counts, new_edge_device_counts],
            ])

        super().self_delete()
