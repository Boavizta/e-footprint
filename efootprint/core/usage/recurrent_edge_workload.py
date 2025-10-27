from typing import TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.usage.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class WorkloadOutOfBoundsError(Exception):
    def __init__(self, workload_name: str, min_value: float, max_value: float):
        message = (
            f"Workload '{workload_name}' has values outside the valid range [0, 1]. "
            f"Found values between {min_value:.3f} and {max_value:.3f}. "
            f"Workload values must represent a percentage between 0 and 1 (0% to 100%).")
        super().__init__(message)


class RecurrentEdgeWorkload(RecurrentEdgeDeviceNeed):
    default_values = {
        "recurrent_workload": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.concurrent)),
    }

    def __init__(self, name: str, edge_device: EdgeAppliance, recurrent_workload: ExplainableRecurrentQuantities):
        self.assert_recurrent_workload_is_between_0_and_1(recurrent_workload, name)

        workload_need = RecurrentEdgeComponentNeed(
            name=f"{name} workload need",
            edge_component=edge_device.appliance_component,
            recurrent_need=recurrent_workload)

        super().__init__(
            name=name,
            edge_device=edge_device,
            recurrent_edge_component_needs=[workload_need])

        self._workload_need = workload_need

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
    def unitary_hourly_workload_per_usage_pattern(self):
        return self._workload_need.unitary_hourly_need_per_usage_pattern
