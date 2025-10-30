from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney


class EdgeFunction(ModelingObject):
    def __init__(self, name: str, recurrent_edge_device_needs: List[RecurrentEdgeDeviceNeed]):
        super().__init__(name)
        self.recurrent_edge_device_needs = recurrent_edge_device_needs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[RecurrentEdgeDeviceNeed]:
        return self.recurrent_edge_device_needs

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return self.modeling_obj_containers
