from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.edge_hardware import EdgeHardware

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge_function import EdgeFunction


class RecurrentEdgeResourceNeeded(ModelingObject):
    def __init__(self, name: str, edge_hardware: EdgeHardware):
        super().__init__(name)
        self.edge_hardware = edge_hardware

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return self.modeling_obj_containers
    
    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeHardware"]:
        return [self.edge_hardware]
        
    