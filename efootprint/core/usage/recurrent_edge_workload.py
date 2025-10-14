from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeeded

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class RecurrentEdgeWorkload(RecurrentEdgeResourceNeeded):
    def __init__(self, name: str, edge_hardware: EdgeHardware, recurrent_workload: ExplainableRecurrentQuantities):
        super().__init__(name, edge_hardware)
        self.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict()
        self.recurrent_workload = recurrent_workload.set_label(f"{self.name} recurrent workload")

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
