from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeWorkloadComponent(EdgeComponent):
    compatible_root_units = [u.concurrent]
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan, idle_power)
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_workload_per_usage_pattern"] + super().calculated_attributes

    def update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_workload = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_edge_component_needs if usage_pattern in need.edge_usage_patterns],
            start=EmptyExplainableObject())

        self.unitary_hourly_workload_per_usage_pattern[usage_pattern] = unitary_hourly_workload.set_label(
            f"{self.name} hourly workload for {usage_pattern.name}")

    def update_unitary_hourly_workload_per_usage_pattern(self):
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        if usage_pattern in self.unitary_hourly_workload_per_usage_pattern:
            workload = self.unitary_hourly_workload_per_usage_pattern[usage_pattern]
        else:
            workload = EmptyExplainableObject()

        if isinstance(workload, EmptyExplainableObject):
            unitary_power = self.idle_power
        else:
            unitary_power = self.idle_power + (self.power - self.idle_power) * workload

        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)
