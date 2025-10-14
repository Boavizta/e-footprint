from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeeded

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney


class EdgeFunction(ModelingObject):
    def __init__(self, name: str, edge_needs: List[RecurrentEdgeResourceNeeded]):
        super().__init__(name)
        self.edge_needs = edge_needs

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return self.modeling_obj_containers

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["RecurrentEdgeResourceNeeded"]:
        return self.edge_needs
