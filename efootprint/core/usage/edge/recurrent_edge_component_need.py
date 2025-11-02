from typing import TYPE_CHECKING, List, Optional

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent

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
    def __init__(self, name: str, edge_component: EdgeComponent, recurrent_need: ExplainableRecurrentQuantities):
        super().__init__(name)
        self.edge_component = edge_component
        self.recurrent_need = recurrent_need.set_label(f"{self.name} recurrent need")
        self.validated_recurrent_need = EmptyExplainableObject()
        self.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[EdgeComponent]:
        return [self.edge_component]

    @property
    def calculated_attributes(self):
        return ["validated_recurrent_need", "unitary_hourly_need_per_usage_pattern"]

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
        return list(set(sum([need.edge_functions for need in self.recurrent_edge_device_needs], start=[])))

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    @staticmethod
    def assert_recurrent_workload_is_between_0_and_1(
            recurrent_workload: ExplainableRecurrentQuantities, workload_name: str):
        # Convert to concurrent (or dimensionless-like unit) to get raw magnitude
        workload_magnitude = recurrent_workload.value.to(u.concurrent).magnitude
        min_value = float(workload_magnitude.min())
        max_value = float(workload_magnitude.max())

        if min_value < 0 or max_value > 1:
            raise WorkloadOutOfBoundsError(workload_name, min_value, max_value)

    def update_validated_recurrent_need(self):
        """Validate that the recurrent_need unit is compatible with the edge_component."""
        root_need_unit = self.recurrent_need.value.to_root_units().units
        expected_units = self.edge_component.compatible_root_units

        if not root_need_unit in expected_units:
            raise InvalidComponentNeedUnitError(self.edge_component.name, root_need_unit, expected_units)

        if expected_units == ["concurrent"]:
            # For dimensionless needs (like workload), ensure values are between 0 and 1
            self.assert_recurrent_workload_is_between_0_and_1(self.recurrent_need, self.name)

        self.validated_recurrent_need = self.recurrent_need.copy().set_label(
            f"Validated recurrent need of {self.name}")

    def update_dict_element_in_unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_need = self.recurrent_need.generate_hourly_quantities_over_timespan(
            usage_pattern.nb_edge_usage_journeys_in_parallel, usage_pattern.country.timezone)
        self.unitary_hourly_need_per_usage_pattern[usage_pattern] = unitary_hourly_need.set_label(
            f"{self.name} unitary hourly need for {usage_pattern.name}")

    def update_unitary_hourly_need_per_usage_pattern(self):
        self.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_need_per_usage_pattern(usage_pattern)
