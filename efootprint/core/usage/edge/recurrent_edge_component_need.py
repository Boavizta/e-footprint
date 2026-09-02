from typing import TYPE_CHECKING, List, Optional

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute, computed_dict

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge.edge_device import EdgeDevice


class InvalidComponentNeedUnitError(Exception):
    def __init__(self, component_name: str, need_unit, expected_units: List):
        message = (
            f"RecurrentEdgeComponentNeed linked to {component_name} has incompatible unit '{need_unit}'. "
            f"Expected one of: {[str(unit) for unit in expected_units]}")
        super().__init__(message)


class WorkloadOutOfBoundsError(Exception):
    def __init__(self, workload_name: str, min_value: float, max_value: float):
        message = (
            f"Workload '{workload_name}' has values outside the valid range [0, 1]. "
            f"Found values between {min_value:.3f} and {max_value:.3f}. "
            f"Workload values must represent a percentage between 0 and 1 (0% to 100%).")
        super().__init__(message)


class RecurrentEdgeComponentNeed(ModelingObject):
    """A repeating week-long resource demand placed on one {class:EdgeComponent} (RAM, CPU, storage, or whole-device workload). The need pattern is replayed for the lifetime of every {class:EdgeUsageJourney} that includes it."""

    param_descriptions = {
        "edge_component": (
            "{class:EdgeComponent} on which the recurring need is placed. The need's unit must match what "
            "the component provides (RAM, compute, storage, or workload)."),
        "recurrent_need": (
            "Hourly resource consumption pattern over a typical week, starting Monday at midnight. The 168-hour "
            "pattern is repeated to cover the modeling period."),
    }

    # recurrent_need is None (and not stored) for subclasses that compute it from other inputs (the
    # RecurrentEdgeProcess and RecurrentEdgeWorkload need builders) — assigning a computed name raises.
    def __init__(self, name: str, edge_component: EdgeComponent,
                 recurrent_need: ExplainableRecurrentQuantities = None):
        super().__init__(name)
        self.edge_component = edge_component
        if recurrent_need is not None:
            self.recurrent_need = recurrent_need.set_label("Recurrent need")



    @property
    def recurrent_edge_device_needs(self):
        return self.modeling_obj_containers

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        if not self.recurrent_edge_device_needs:
            return None
        return self.recurrent_edge_device_needs[0].edge_device

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return list(dict.fromkeys(sum([need.edge_functions for need in self.recurrent_edge_device_needs], start=[])))

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(dict.fromkeys(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    @staticmethod
    def assert_recurrent_workload_is_between_0_and_1(
            recurrent_workload: ExplainableRecurrentQuantities, workload_name: str):
        # Convert to concurrent (or dimensionless-like unit) to get raw magnitude
        workload_magnitude = recurrent_workload.value.to(u.concurrent).magnitude
        min_value = float(workload_magnitude.min())
        max_value = float(workload_magnitude.max())

        if min_value < 0 or max_value > 1:
            raise WorkloadOutOfBoundsError(workload_name, min_value, max_value)

    @computed_attribute(guard=True)
    def recurrent_need_validation(self):
        """Validates that the recurrent need uses a unit compatible with its target component, and (for workload-style needs) that values stay between 0 and 1."""
        root_need_unit = self.recurrent_need.value.to_root_units().units
        expected_units = self.edge_component.compatible_root_units

        if not root_need_unit in expected_units:
            raise InvalidComponentNeedUnitError(self.edge_component.name, root_need_unit, expected_units)

        if expected_units == ["concurrent"]:
            # For dimensionless needs (like workload), ensure values are between 0 and 1
            self.assert_recurrent_workload_is_between_0_and_1(self.recurrent_need, self.name)

        return self.recurrent_need.copy().set_label(
            f"Validated recurrent need")

    @computed_dict(keys="edge_usage_patterns")
    def unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly resource demand for one edge device, generated by replaying the typical-week pattern across the modeling period in the country's timezone, and scaled by how often the need appears in the journey."""
        unitary_hourly_need = self.recurrent_need.generate_hourly_quantities_over_timespan(
            usage_pattern.nb_deployments_in_parallel,
            usage_pattern.country.timezone)
        nb_of_occurrences_of_self_within_usage_pattern = sum(
            path.nb_occurrences for path in usage_pattern.containment_inventory.component_need_paths
            if path.recurrent_edge_component_need == self)

        unitary_hourly_need *= ExplainableQuantity(nb_of_occurrences_of_self_within_usage_pattern * u.dimensionless,
                                                   label=f"Occurrences within {usage_pattern.name}")

        return unitary_hourly_need.set_label(
            f"Unitary hourly need for {usage_pattern.name}")

    @computed_attribute
    def total_hourly_need_across_usage_patterns(self):
        """Total hourly demand on the component, summed across every {class:EdgeUsagePattern} after multiplying by the hourly count of edge devices in deployment."""
        return sum(
            [self.unitary_hourly_need_per_usage_pattern[usage_pattern]
             * usage_pattern.nb_deployments_in_parallel
             for usage_pattern in self.edge_usage_patterns],
            start=EmptyExplainableObject(),
        ).set_label("Total hourly need across usage patterns")
