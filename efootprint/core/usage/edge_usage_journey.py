from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge_device import EdgeDevice
    from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeeded


class EdgeUsageJourney(ModelingObject):
    default_values = {
        "usage_span": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, edge_functions: List[EdgeFunction], usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_functions = edge_functions
        self.assert_usage_span_is_inferior_to_edge_devices_lifespan(usage_span, self.edge_devices)
        self.usage_span = usage_span.set_label(f"Usage span of {self.name}")

    @staticmethod
    def assert_usage_span_is_inferior_to_edge_devices_lifespan(usage_span: ExplainableQuantity, edge_devices: List["EdgeDevice"]):
        # TODO: adapt check to all edge devices
        if usage_span > edge_device.lifespan:
            raise InsufficientCapacityError(edge_device, "lifespan", edge_device.lifespan, usage_span)

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def edge_needs(self) -> List["RecurrentEdgeResourceNeeded"]:
        # TODO: Get list of unique edge needs from edge_functions
        pass

    @property
    def edge_hardwares(self) -> List["EdgeDevice"]:
        # TODO: Get list of unique edge hardwares from edge_needs
        pass

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[RecurrentEdgeProcess]:
        if self.edge_usage_patterns:
            return self.edge_usage_patterns
        return self.edge_functions

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "usage_span":
            self.assert_usage_span_is_inferior_to_edge_devices_lifespan(input_value, self.edge_devices)
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)
