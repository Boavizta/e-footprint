from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge.edge_function import EdgeFunction

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge.edge_device import EdgeDevice
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, edge_functions: List[EdgeFunction], usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_functions = edge_functions
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

        self.usage_span_validation = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[EdgeFunction]:
        if self.edge_usage_patterns:
            return self.edge_usage_patterns
        return self.edge_functions

    @property
    def calculated_attributes(self) -> List[str]:
        return ["usage_span_validation"]

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()

    def update_usage_span_validation(self):
        result = self.usage_span.copy().set_label(f"{self.name} usage span validation")
        for edge_device in self.edge_devices:
            if self.usage_span > edge_device.lifespan:
                raise InsufficientCapacityError(edge_device, "lifespan", edge_device.lifespan, self.usage_span)
            result = result.generate_explainable_object_with_logical_dependency(edge_device.lifespan)
        self.usage_span_validation = result

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        return list(set(sum([ef.recurrent_edge_device_needs for ef in self.edge_functions], start=[])))

    @property
    def edge_devices(self) -> List["EdgeDevice"]:
        return list(set([edge_need.edge_device for edge_need in self.recurrent_edge_device_needs]))
