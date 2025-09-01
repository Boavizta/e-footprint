from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.hardware.edge_device import EdgeDevice

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.system import System


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, edge_processes: List[RecurrentEdgeProcess], edge_device: EdgeDevice,
                 usage_span: ExplainableQuantity):
        super().__init__(name)
        self.assert_usage_span_is_inferior_to_edge_device_lifespan(usage_span, edge_device)
        self.edge_processes = edge_processes
        self.edge_device = edge_device
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

    @staticmethod
    def assert_usage_span_is_inferior_to_edge_device_lifespan(usage_span: ExplainableQuantity, edge_device: EdgeDevice):
        if usage_span > edge_device.lifespan:
            raise InsufficientCapacityError(edge_device, "lifespan", edge_device.lifespan, usage_span)

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def systems(self) -> List["System"]:
        if self.modeling_obj_containers:
            return list(set(sum([eup.systems for eup in self.edge_usage_patterns], start=[])))
        return []

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[RecurrentEdgeProcess]:
        if self.edge_usage_patterns:
            return self.edge_usage_patterns
        return self.edge_processes + [self.edge_device]

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "usage_span":
            self.assert_usage_span_is_inferior_to_edge_device_lifespan(input_value, self.edge_device)
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)
