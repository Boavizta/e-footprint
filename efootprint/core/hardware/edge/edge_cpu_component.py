from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeCPUComponent(EdgeComponent):
    compatible_root_units = [u.cpu_core]
    default_values = {
        "carbon_footprint_fabrication_per_unit": SourceValue(20 * u.kg),
        "power_per_unit": SourceValue(15 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power_per_unit": SourceValue(3 * u.W),
        "nb_of_units": SourceValue(1 * u.dimensionless),
        "compute_per_unit": SourceValue(4 * u.cpu_core),
        "base_compute_consumption": SourceValue(0 * u.cpu_core),
    }

    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity,
                 power_per_unit: ExplainableQuantity, lifespan: ExplainableQuantity,
                 idle_power_per_unit: ExplainableQuantity, compute_per_unit: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(
            name, carbon_footprint_fabrication_per_unit, power_per_unit, lifespan, idle_power_per_unit,
            nb_of_units=nb_of_units)
        self.compute_per_unit = compute_per_unit.set_label(f"Compute per unit")
        self.compute = EmptyExplainableObject()
        self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption")

        self.available_compute_per_instance = EmptyExplainableObject()
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return (["compute", "available_compute_per_instance", "unitary_hourly_compute_need_per_usage_pattern"]
                + super().calculated_attributes)

    def update_compute(self):
        self.compute = (self.compute_per_unit * self.nb_of_units).set_label(f"Compute")

    def update_available_compute_per_instance(self):
        available_compute_per_instance = (self.compute - self.base_compute_consumption)

        if available_compute_per_instance < SourceValue(0 * u.cpu_core):
            raise InsufficientCapacityError(self, "compute", self.compute, self.base_compute_consumption)

        self.available_compute_per_instance = available_compute_per_instance.set_label(
            f"Available compute per {self.name} instance")

    def update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_compute_need = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_edge_component_needs if usage_pattern in need.edge_usage_patterns],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_compute_need, EmptyExplainableObject):
            max_compute_need = unitary_hourly_compute_need.max().to(u.cpu_core)
            if max_compute_need > self.available_compute_per_instance:
                raise InsufficientCapacityError(self, "compute", self.available_compute_per_instance, max_compute_need)

        self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern] = unitary_hourly_compute_need.to(
            u.cpu_core).set_label(f"{self.name} hourly compute need for {usage_pattern.name}").generate_explainable_object_with_logical_dependency(
            self.available_compute_per_instance)

    def update_unitary_hourly_compute_need_per_usage_pattern(self):
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        if usage_pattern in self.unitary_hourly_compute_need_per_usage_pattern:
            compute_need = self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern]
        else:
            compute_need = EmptyExplainableObject()

        if isinstance(compute_need, EmptyExplainableObject):
            unitary_power = self.idle_power
        else:
            unitary_compute_workload = (compute_need + self.base_compute_consumption) / self.compute
            unitary_power = self.idle_power + (self.power - self.idle_power) * unitary_compute_workload

        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)
