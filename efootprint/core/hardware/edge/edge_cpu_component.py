from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute, computed_dict

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeCPUComponent(EdgeComponent):
    """A CPU inside an {class:EdgeDevice}. Sized so that aggregated recurrent compute demand never exceeds available cores."""

    param_descriptions = {
        **EdgeComponent.param_descriptions,
        "compute_per_unit": (
            "Number of CPU cores provided by one unit. Total compute is this value times {param:EdgeCPUComponent.nb_of_units}."),
        "base_compute_consumption": (
            "Compute permanently occupied independently of recurring needs."),
    }

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

    # compute_per_unit and base_compute_consumption are None (and not stored) for subclasses that
    # compute them from the parent device (EdgeComputerCPUComponent) — assigning a computed name raises.
    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity = None,
                 power_per_unit: ExplainableQuantity = None, lifespan: ExplainableQuantity = None,
                 idle_power_per_unit: ExplainableQuantity = None, compute_per_unit: ExplainableQuantity = None,
                 base_compute_consumption: ExplainableQuantity = None,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(
            name, carbon_footprint_fabrication_per_unit, power_per_unit, lifespan, idle_power_per_unit,
            nb_of_units=nb_of_units)
        if compute_per_unit is not None:
            self.compute_per_unit = compute_per_unit.set_label(f"Compute per unit")
        if base_compute_consumption is not None:
            self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption")



    @computed_attribute
    def compute(self):
        """Total compute provided by the CPU component, equal to per-unit compute times the number of units."""
        return (self.compute_per_unit * self.nb_of_units).set_label(f"Compute")

    @computed_attribute(guard=True)
    def available_compute_per_instance(self):
        """Compute available for recurring needs after subtracting the base consumption. Raises error if the component is over-subscribed at design time."""
        available_compute_per_instance = (self.compute - self.base_compute_consumption)

        if available_compute_per_instance < SourceValue(0 * u.cpu_core):
            raise InsufficientCapacityError(self, "compute", self.compute, self.base_compute_consumption)

        return available_compute_per_instance.set_label(
            f"Available compute per instance")

    @computed_dict(keys="edge_usage_patterns", guard=True)
    def unitary_hourly_compute_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly compute demand on one component, broken down by usage pattern. Raises error if peak demand exceeds the component's available compute."""
        unitary_hourly_compute_need = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_edge_component_needs if usage_pattern in need.edge_usage_patterns],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_compute_need, EmptyExplainableObject):
            max_compute_need = unitary_hourly_compute_need.max().to(u.cpu_core)
            if max_compute_need > self.available_compute_per_instance:
                raise InsufficientCapacityError(self, "compute", self.available_compute_per_instance, max_compute_need)

        return unitary_hourly_compute_need.to(
            u.cpu_core).set_label(f"Hourly compute need for {usage_pattern.name}").generate_explainable_object_with_logical_dependency(
            self.available_compute_per_instance)

    @property
    def unitary_power_at_zero_recurrent_need(self) -> ExplainableQuantity:
        return (self.idle_power + (self.power - self.idle_power) * self.base_compute_consumption / self.compute
                ).set_label("Idle and base power")

    @computed_dict(keys="edge_usage_patterns")
    def unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly power profile of the component for one device, derived from the compute workload (current need plus base consumption divided by total compute) by linearly interpolating between idle and full power."""
        if usage_pattern in self.unitary_hourly_compute_need_per_usage_pattern:
            compute_need = self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern]
        else:
            compute_need = EmptyExplainableObject()

        if isinstance(compute_need, EmptyExplainableObject):
            unitary_power = self.idle_power.copy()
        else:
            unitary_compute_workload = (compute_need + self.base_compute_consumption) / self.compute
            unitary_power = self.idle_power + (self.power - self.idle_power) * unitary_compute_workload

        return unitary_power.set_label(
            f"Unitary power for {usage_pattern.name}")
