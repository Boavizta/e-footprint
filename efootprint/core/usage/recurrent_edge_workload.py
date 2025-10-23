from typing import TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class WorkloadOutOfBoundsError(Exception):
    def __init__(self, workload_name: str, min_value: float, max_value: float):
        message = (
            f"Workload '{workload_name}' has values outside the valid range [0, 1]. "
            f"Found values between {min_value:.3f} and {max_value:.3f}. "
            f"Workload values must represent a percentage between 0 and 1 (0% to 100%).")
        super().__init__(message)


class RecurrentEdgeWorkload(RecurrentEdgeResourceNeed):
    default_values = {
        "recurrent_workload": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.concurrent)),
    }

    def __init__(self, name: str, edge_device: EdgeAppliance, recurrent_workload: ExplainableRecurrentQuantities):
        super().__init__(name, edge_device)
        self.assert_recurrent_workload_is_between_0_and_1(recurrent_workload, name)
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()
        self.recurrent_workload = recurrent_workload.set_label(f"{self.name} recurrent workload")

    @staticmethod
    def assert_recurrent_workload_is_between_0_and_1(
            recurrent_workload: ExplainableRecurrentQuantities, workload_name: str):
        # Convert to concurrent (or dimensionless-like unit) to get raw magnitude
        workload_magnitude = recurrent_workload.value.to(u.concurrent).magnitude
        min_value = float(workload_magnitude.min())
        max_value = float(workload_magnitude.max())

        if min_value < 0 or max_value > 1:
            raise WorkloadOutOfBoundsError(workload_name, min_value, max_value)

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_workload_per_usage_pattern"]

    def update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_workload = self.recurrent_workload.generate_hourly_quantities_over_timespan(
            usage_pattern.nb_edge_usage_journeys_in_parallel, usage_pattern.country.timezone)
        self.unitary_hourly_workload_per_usage_pattern[usage_pattern] = unitary_hourly_workload.set_label(
            f"{self.name} unitary hourly workload for {usage_pattern.name}")

    def update_unitary_hourly_workload_per_usage_pattern(self):
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(usage_pattern)

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "recurrent_workload":
            self.assert_recurrent_workload_is_between_0_and_1(input_value, self.name)
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)
