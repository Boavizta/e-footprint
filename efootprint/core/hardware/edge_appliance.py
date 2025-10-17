from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device_base import EdgeDeviceBase
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload


class EdgeAppliance(EdgeDeviceBase):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity,
                 idle_power: ExplainableQuantity):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_workload_per_usage_pattern"] + super().calculated_attributes

    @property
    def edge_workloads(self) -> List["RecurrentEdgeWorkload"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([ew.edge_usage_patterns for ew in self.edge_workloads], start=[])))

    def update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_workload = sum(
            [edge_workload.unitary_hourly_workload_per_usage_pattern[usage_pattern]
             for edge_workload in self.edge_workloads if usage_pattern in edge_workload.edge_usage_patterns],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_workload, EmptyExplainableObject):
            max_workload = unitary_hourly_workload.max().to(u.dimensionless)
            if max_workload > ExplainableQuantity(1 * u.dimensionless, "100% workload"):
                raise InsufficientCapacityError(
                    self, "workload capacity", ExplainableQuantity(1 * u.dimensionless, "100% workload"), max_workload)

        self.unitary_hourly_workload_per_usage_pattern[usage_pattern] = unitary_hourly_workload.set_label(
            f"{self.name} hourly workload for {usage_pattern.name}")

    def update_unitary_hourly_workload_per_usage_pattern(self):
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        workload = self.unitary_hourly_workload_per_usage_pattern[usage_pattern]
        unitary_power = self.idle_power + (self.power - self.idle_power) * workload
        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)