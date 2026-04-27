from typing import TYPE_CHECKING, List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeFunction(ModelingObject):
    """A coherent feature of an edge deployment, grouping the recurring resource consumption it imposes on edge devices and the recurring server-side jobs it triggers."""

    param_descriptions = {
        "recurrent_edge_device_needs": (
            "Recurring resource needs running on edge hardware: CPU, RAM, storage, or whole-device workloads "
            "(see {class:RecurrentEdgeDeviceNeed} subclasses)."),
        "recurrent_server_needs": (
            "Recurring batches of server-side jobs triggered by this function (see {class:RecurrentServerNeed})."),
    }

    def __init__(self, name: str, recurrent_edge_device_needs: List[RecurrentEdgeDeviceNeed],
                 recurrent_server_needs: List[RecurrentServerNeed]):
        super().__init__(name)
        self.recurrent_edge_device_needs = recurrent_edge_device_needs
        self.recurrent_server_needs = recurrent_server_needs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[RecurrentEdgeDeviceNeed]:
        return self.recurrent_edge_device_needs + self.recurrent_server_needs

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))
