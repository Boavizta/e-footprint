from typing import TYPE_CHECKING, List, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
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


class RecurrentEdgeComponentNeed(ModelingObject):
    def __init__(self, name: str, edge_component: EdgeComponent, recurrent_need: ExplainableRecurrentQuantities):
        super().__init__(name)
        self.edge_component = edge_component
        self.recurrent_need = recurrent_need.set_label(f"{self.name} recurrent need")
        self.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()

        self._validate_need_unit()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[EdgeComponent]:
        return [self.edge_component]

    def _validate_need_unit(self):
        """Validate that the recurrent_need unit is compatible with the edge_component."""
        need_unit = self.recurrent_need.value.units
        expected_units = self.edge_component.expected_need_units()

        if not any(need_unit.is_compatible_with(expected_unit) for expected_unit in expected_units):
            raise InvalidComponentNeedUnitError(self.edge_component.name, need_unit, expected_units)

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_need_per_usage_pattern"]

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

    def update_dict_element_in_unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_need = self.recurrent_need.generate_hourly_quantities_over_timespan(
            usage_pattern.nb_edge_usage_journeys_in_parallel, usage_pattern.country.timezone)
        self.unitary_hourly_need_per_usage_pattern[usage_pattern] = unitary_hourly_need.set_label(
            f"{self.name} unitary hourly need for {usage_pattern.name}")

    def update_unitary_hourly_need_per_usage_pattern(self):
        self.unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_need_per_usage_pattern(usage_pattern)

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)
        if name == "recurrent_need" and hasattr(self, "edge_component"):
            self._validate_need_unit()
