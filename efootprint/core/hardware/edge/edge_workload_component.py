from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.abstract_modeling_classes.reactive_core import computed_dict

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeWorkloadComponent(EdgeComponent):
    """A whole-device opaque resource described only by a 0..1 utilisation level (an "appliance-style" component). Used when individual CPU/RAM specs are not modeled or don’t apply, only how loaded the device is."""

    disambiguation = (
        "Use {class:EdgeWorkloadComponent} for appliance-style devices where the internal hardware is opaque. "
        "Use {class:EdgeRAMComponent}, {class:EdgeCPUComponent}, and {class:EdgeStorage} when compute and memory "
        "components need to be modeled separately.")

    param_descriptions = {**EdgeComponent.param_descriptions}

    compatible_root_units = [u.concurrent]
    default_values = {
        "carbon_footprint_fabrication_per_unit": SourceValue(100 * u.kg),
        "power_per_unit": SourceValue(50 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power_per_unit": SourceValue(5 * u.W),
        "nb_of_units": SourceValue(1 * u.dimensionless),
    }

    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity = None,
                 power_per_unit: ExplainableQuantity = None, lifespan: ExplainableQuantity = None,
                 idle_power_per_unit: ExplainableQuantity = None,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(
            name, carbon_footprint_fabrication_per_unit, power_per_unit, lifespan, idle_power_per_unit,
            nb_of_units=nb_of_units)


    @computed_dict(keys="edge_usage_patterns")
    def unitary_hourly_workload_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly workload (between 0 and 1) on one component, broken down by usage pattern. Raises error if aggregated workload exceeds 1."""
        unitary_hourly_workload = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_needs_in_usage_pattern(usage_pattern)],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_workload, EmptyExplainableObject):
            RecurrentEdgeComponentNeed.assert_recurrent_workload_is_between_0_and_1(
                unitary_hourly_workload, f"Aggregated workload for {usage_pattern.name}")

        return unitary_hourly_workload.set_label(
            f"Hourly workload for {usage_pattern.name}")

    @property
    def unitary_power_at_zero_recurrent_need(self) -> ExplainableQuantity:
        return self.idle_power

    @computed_dict(keys="edge_usage_patterns")
    def unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly power profile of the component for one device, linearly interpolated between idle and full power based on the workload."""
        if usage_pattern in self.unitary_hourly_workload_per_usage_pattern:
            workload = self.unitary_hourly_workload_per_usage_pattern[usage_pattern]
        else:
            workload = EmptyExplainableObject()

        if isinstance(workload, EmptyExplainableObject):
            unitary_power = self.idle_power.copy()
        else:
            unitary_power = self.idle_power + (self.power - self.idle_power) * workload

        return unitary_power.set_label(
            f"Unitary power for {usage_pattern.name}")
