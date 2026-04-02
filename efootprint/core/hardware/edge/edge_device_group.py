from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.hardware.edge.edge_device import EdgeDevice


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
        self.sub_group_counts = sub_group_counts
        self.edge_device_counts = edge_device_counts
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
        parent_groups = []
        for dict_container in self.explainable_object_dicts_containers:
            container = dict_container.modeling_obj_container
            if isinstance(container, EdgeDeviceGroup):
                if self not in dict_container:
                    raise ValueError(
                        f"Stale explainable_object_dicts_container: "
                        f"{container.name}.{dict_container.attr_name_in_mod_obj_container} "
                        f"references {self.name} but doesn't contain it as a key")
                if container not in parent_groups:
                    parent_groups.append(container)
        return parent_groups

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
            # Sum contributions from all parents
            effective_nb = sum(
                [parent.sub_group_counts[self] * parent.effective_nb_of_units_within_root
                 for parent in parent_groups],
                start=EmptyExplainableObject())
            self.effective_nb_of_units_within_root = effective_nb.set_label(
                f"Effective nb of {self.name} within root group")
