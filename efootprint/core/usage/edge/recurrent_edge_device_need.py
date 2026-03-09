from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_function import EdgeFunction


class RecurrentEdgeDeviceNeed(ModelingObject):
    default_values = {}

    def __init__(self, name: str, edge_device: EdgeDevice,
                 recurrent_edge_component_needs: List[RecurrentEdgeComponentNeed]):
        super().__init__(name)
        self.edge_device = edge_device
        self.recurrent_edge_component_needs = recurrent_edge_component_needs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[RecurrentEdgeComponentNeed]:
        # edge_device is automatically included through components' modeling_objects_whose_attributes_depend_directly_on_me
        return self.recurrent_edge_component_needs

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))
