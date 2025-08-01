from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.usage.edge_process import EdgeProcess


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(2 * u.year, Sources.HYPOTHESIS)
    }

    def __init__(self, name: str, edge_processes: List[EdgeProcess], usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_processes = edge_processes
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")
        
        # Will store the duration that processes run during the edge device lifespan
        self.duration = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return ["duration"]

    @property
    def edge_usage_patterns(self):
        # Returns EdgeUsagePattern objects that use this journey
        from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
        return [obj for obj in self.modeling_obj_containers if isinstance(obj, EdgeUsagePattern)]

    @property
    def systems(self) -> List:
        return list(set(sum([eup.systems for eup in self.edge_usage_patterns], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return self.edge_usage_patterns

    @property
    def edge_device(self):
        # Get the edge device from the EdgeUsagePattern
        if self.edge_usage_patterns:
            return self.edge_usage_patterns[0].edge_device
        return None

    def validate_resource_consumption(self):
        """
        Validate that the total resource consumption of all edge processes
        doesn't exceed the edge device capacity.
        """
        edge_device = self.edge_device
        if not edge_device:
            return  # Cannot validate without edge device reference
        
        # Check each hour of the week
        for hour in range(168):  # 168 hours in a week
            total_cpu = sum(process.recurrent_cpu_compute[hour] for process in self.edge_processes)
            total_ram = sum(process.recurrent_ram_compute[hour] for process in self.edge_processes)
            
            # Check against available capacity (considering utilization rate and base consumption)
            available_cpu = (edge_device.compute.value.magnitude * edge_device.server_utilization_rate.value.magnitude 
                           - edge_device.base_compute_consumption.value.magnitude)
            available_ram = (edge_device.ram.value.to(u.GB).magnitude * edge_device.server_utilization_rate.value.magnitude 
                           - edge_device.base_ram_consumption.value.to(u.GB).magnitude)
            
            if total_cpu > available_cpu:
                raise ValueError(
                    f"Hour {hour}: Total CPU consumption ({total_cpu}) exceeds available capacity ({available_cpu}) "
                    f"on {edge_device.name}")
            
            if total_ram > available_ram:
                raise ValueError(
                    f"Hour {hour}: Total RAM consumption ({total_ram} GB) exceeds available capacity ({available_ram} GB) "
                    f"on {edge_device.name}")

    def update_duration(self):
        # The duration is the usage_span - how long the processes run on the edge device
        self.duration = self.usage_span.copy().set_label(f"Duration of {self.name}")

    def after_init(self):
        super().after_init()
        self.validate_resource_consumption()
        self.compute_calculated_attributes()