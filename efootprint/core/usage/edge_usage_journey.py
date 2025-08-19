from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.usage.edge_process import EdgeProcess
from efootprint.core.hardware.edge_device import EdgeDevice


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(2 * u.year, Sources.HYPOTHESIS)
    }

    def __init__(self, name: str, edge_processes: List[EdgeProcess], edge_device: EdgeDevice, usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_processes = edge_processes
        self.edge_device = edge_device
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

    @property
    def edge_usage_pattern(self):
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"EdgeUsageJourney object can only be associated with one EdgeUsagePattern object but {self.name} is associated "
                    f"with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def systems(self) -> List:
        return self.edge_usage_pattern.systems

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return self.edge_processes + [self.edge_device]

    def validate_resource_consumption(self):
        """
        Validate that the total resource consumption of all edge processes
        doesn't exceed the edge device capacity.
        """
        # TODO: Move to EdgeDevice
        # Check each hour of the week
        for hour in range(168):  # 168 hours in a week
            total_cpu = sum(process.recurrent_cpu_compute[hour] for process in self.edge_processes)
            total_ram = sum(process.recurrent_ram_compute[hour] for process in self.edge_processes)
            
            # Check against available capacity (considering utilization rate and base consumption)
            available_cpu = (self.edge_device.compute.value.magnitude * self.edge_device.server_utilization_rate.value.magnitude 
                           - self.edge_device.base_compute_consumption.value.magnitude)
            available_ram = (self.edge_device.ram.value.to(u.GB).magnitude * self.edge_device.server_utilization_rate.value.magnitude 
                           - self.edge_device.base_ram_consumption.value.to(u.GB).magnitude)
            
            if total_cpu > available_cpu:
                raise ValueError(
                    f"Hour {hour}: Total CPU consumption ({total_cpu}) exceeds available capacity ({available_cpu}) "
                    f"on {self.edge_device.name}")
            
            if total_ram > available_ram:
                raise ValueError(
                    f"Hour {hour}: Total RAM consumption ({total_ram} GB) exceeds available capacity ({available_ram} GB) "
                    f"on {self.edge_device.name}")
