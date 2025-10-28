from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge_function import EdgeFunction


class RecurrentEdgeDeviceNeed(ModelingObject):
    @classmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, edge_device: EdgeDevice,
                 recurrent_edge_component_needs: List[RecurrentEdgeComponentNeed]):
        super().__init__(name)
        self.edge_device = edge_device
        self.recurrent_edge_component_needs = recurrent_edge_component_needs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[RecurrentEdgeComponentNeed]:
        # edge_device is automatically included through components' modeling_objects_whose_attributes_depend_directly_on_me
        return self.recurrent_edge_component_needs

    def _validate_component_needs_edge_device(self, component_needs: List[RecurrentEdgeComponentNeed]):
        """Validate that all component needs point to components of this edge_device."""
        for component_need in component_needs:
            component_device = component_need.edge_component.edge_device
            if component_device is not None and component_device != self.edge_device:
                raise ValueError(
                    f"RecurrentEdgeComponentNeed '{component_need.name}' points to component "
                    f"'{component_need.edge_component.name}' belonging to EdgeDevice '{component_device.name}', "
                    f"but RecurrentEdgeDeviceNeed '{self.name}' is linked to EdgeDevice '{self.edge_device.name}'. "
                    f"All component needs must belong to the same edge device.")

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "recurrent_edge_component_needs" and hasattr(self, "edge_device"):
            # Validate whenever recurrent_edge_component_needs is updated
            self._validate_component_needs_edge_device(input_value)
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))
    