from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.edge_function import EdgeFunction


class RecurrentEdgeDeviceNeed(ModelingObject):
    @classmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, edge_device: EdgeDevice,
                 recurrent_edge_component_needs: List[RecurrentEdgeComponentNeed]):
        super().__init__(name)
        self.edge_device = edge_device
        self.recurrent_edge_component_needs = recurrent_edge_component_needs

        self.component_needs_edge_device_validation = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[RecurrentEdgeComponentNeed]:
        # edge_device is automatically included through components' modeling_objects_whose_attributes_depend_directly_on_me
        return self.recurrent_edge_component_needs

    @property
    def calculated_attributes(self) -> List[str]:
        return ["component_needs_edge_device_validation"]

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    def update_component_needs_edge_device_validation(self):
        """Validate that all component needs point to components of this edge_device."""
        for component_need in self.recurrent_edge_component_needs:
            component_device = component_need.edge_component.edge_device
            if component_device is not None and component_device != self.edge_device:
                raise ValueError(
                    f"RecurrentEdgeComponentNeed '{component_need.name}' points to component "
                    f"'{component_need.edge_component.name}' belonging to EdgeDevice '{component_device.name}', "
                    f"but RecurrentEdgeDeviceNeed '{self.name}' is linked to EdgeDevice '{self.edge_device.name}'. "
                    f"All component needs must belong to the same edge device.")

        self.component_needs_edge_device_validation = EmptyExplainableObject()