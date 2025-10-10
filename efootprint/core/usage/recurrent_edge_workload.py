from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeeded


class RecurrentEdgeWorkload(RecurrentEdgeResourceNeeded):
    def __init__(self, name: str, edge_hardware: EdgeHardware, recurrent_workload: ExplainableRecurrentQuantities):
        super().__init__(name, edge_hardware)
        self.recurrent_workload = recurrent_workload

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_workload_per_usage_pattern"]
    
    # TODO: implement update_unitary_hourly_workload_per_usage_pattern logic just like update_unitary_hourly_compute_need_per_usage_pattern is implemented in RecurrentEdgeProcess class. 