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


class EdgeRAMComponent(EdgeComponent):
    compatible_root_units = [u.bit_ram]
    default_values = {
        "carbon_footprint_fabrication": SourceValue(20 * u.kg),
        "power": SourceValue(10 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(2 * u.W),
        "ram": SourceValue(8 * u.GB_ram),
        "base_ram_consumption": SourceValue(1 * u.GB_ram),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, base_ram_consumption: ExplainableQuantity):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan, idle_power)
        self.ram = ram.set_label(f"RAM of {self.name}").to(u.GB_ram)
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")

        self.available_ram_per_instance = EmptyExplainableObject()
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ["available_ram_per_instance", "unitary_hourly_ram_need_per_usage_pattern"] + super().calculated_attributes

    def update_available_ram_per_instance(self):
        available_ram_per_instance = (self.ram.to(u.GB_ram) - self.base_ram_consumption.to(u.GB_ram))

        if available_ram_per_instance.value < 0 * u.B_ram:
            raise InsufficientCapacityError(self, "RAM", self.ram, self.base_ram_consumption)

        self.available_ram_per_instance = available_ram_per_instance.set_label(
            f"Available RAM per {self.name} instance")

    def update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_ram_need = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_edge_component_needs if usage_pattern in need.edge_usage_patterns],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_ram_need, EmptyExplainableObject):
            max_ram_need = unitary_hourly_ram_need.max().to(u.GB_ram)
            if max_ram_need > self.available_ram_per_instance:
                raise InsufficientCapacityError(self, "RAM", self.available_ram_per_instance, max_ram_need)

        self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern] = unitary_hourly_ram_need.to(u.GB_ram).set_label(
            f"{self.name} hourly RAM need for {usage_pattern.name}").generate_explainable_object_with_logical_dependency(
            self.available_ram_per_instance)

    def update_unitary_hourly_ram_need_per_usage_pattern(self):
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        if usage_pattern in self.unitary_hourly_ram_need_per_usage_pattern:
            ram_need = self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern]
        else:
            ram_need = EmptyExplainableObject()

        if isinstance(ram_need, EmptyExplainableObject):
            unitary_power = self.idle_power
        else:
            ram_workload = (ram_need + self.base_ram_consumption) / self.ram
            unitary_power = self.idle_power + (self.power - self.idle_power) * ram_workload

        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)
