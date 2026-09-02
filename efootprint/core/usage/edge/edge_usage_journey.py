from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.usage.edge.edge_function import EdgeFunction

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge.edge_device import EdgeDevice
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.job import JobBase


class EdgeUsageJourney(ModelingObject):
    """A reusable functionality bundle composed of {class:EdgeFunction}s and applied by an {class:EdgeUsagePattern}."""

    disambiguation = (
        "Use {class:EdgeUsageJourney} for hardware that runs continuously, like a sensor that captures data "
        "every minute or an industrial controller. Use {class:UsageJourney} for user-driven, request-style "
        "interactions in a web context. See {doc:web_vs_edge}.")

    param_descriptions = {
        "edge_functions": (
            "{class:EdgeFunction}s active in this bundle, each describing what runs on devices and what is sent "
            "to servers."),
    }

    default_values = {}

    def __init__(self, name: str, edge_functions: List[EdgeFunction]):
        super().__init__(name)
        self.edge_functions = edge_functions



    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        return list(dict.fromkeys(sum([ef.recurrent_edge_device_needs for ef in self.edge_functions], start=[])))

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        return list(dict.fromkeys(sum([ef.recurrent_server_needs for ef in self.edge_functions], start=[])))

    @property
    def jobs(self) -> List["JobBase"]:
        return list(dict.fromkeys(sum([list(rsn.jobs) for rsn in self.recurrent_server_needs], start=[])))

    @property
    def edge_devices(self) -> List["EdgeDevice"]:
        return list(dict.fromkeys([edge_need.edge_device for edge_need in self.recurrent_edge_device_needs]))
