from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.core.usage.edge.edge_function import EdgeFunction

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge.edge_device import EdgeDevice
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.job import JobBase


class EdgeUsageJourney(ModelingObject):
    """A long-running usage of edge hardware that triggers a set of {class:EdgeFunction}s for the whole time the device is in service. The web counterpart is {class:UsageJourney}, but edge journeys are open-ended rather than per-request."""

    disambiguation = (
        "Use {class:EdgeUsageJourney} for hardware that runs continuously, like a sensor that captures data "
        "every minute or an industrial controller. Use {class:UsageJourney} for user-driven, request-style "
        "interactions. See {doc:web_vs_edge}.")

    param_descriptions = {
        "edge_functions": (
            "{class:EdgeFunction}s active during the journey, each describing what runs on devices and what "
            "is sent to servers."),
        "usage_span": (
            "How long one edge device is in use, from deployment to retirement. The fabrication footprint is "
            "amortised over this duration."),
    }

    default_values = {
        "usage_span": SourceValue(6 * u.year)
    }

    def __init__(self, name: str, edge_functions: List[EdgeFunction], usage_span: ExplainableQuantity):
        super().__init__(name)
        self.edge_functions = edge_functions
        self.usage_span = usage_span.set_label(f"Usage span")

        self.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeUsagePattern"] | List[EdgeFunction]:
        return self.edge_functions

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
        return list(dict.fromkeys(sum([rsn.jobs for rsn in self.recurrent_server_needs], start=[])))

    @property
    def edge_devices(self) -> List["EdgeDevice"]:
        return list(dict.fromkeys([edge_need.edge_device for edge_need in self.recurrent_edge_device_needs]))

    @property
    def calculated_attributes(self) -> List[str]:
        return ["nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern"] + super().calculated_attributes

    def update_dict_element_in_nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern(
            self, edge_usage_pattern: "EdgeUsagePattern"):
        nb_of_edge_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            edge_usage_pattern.utc_hourly_edge_usage_journey_starts, self.usage_span)
        self.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[edge_usage_pattern] = (
            nb_of_edge_usage_journeys_in_parallel.to(u.concurrent)
            .set_label("Hourly nb of edge usage journeys in parallel"))

    def update_nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern(self):
        """Hourly count of edge usage journeys that are concurrently active in each pattern, derived from the journey-start timeseries and the journey usage span."""
        self.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = ExplainableObjectDict()
        for edge_usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern(edge_usage_pattern)

    def _edge_usage_pattern_base_weight(self, usage_pattern: "EdgeUsagePattern"):
        return (
            self.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]
            * self.nb_of_occurrences_per_container[usage_pattern]
        ).to(u.concurrent)

    def update_dict_element_in_fabrication_impact_repartition_weights(self, usage_pattern: "EdgeUsagePattern"):
        self.fabrication_impact_repartition_weights[usage_pattern] = self._edge_usage_pattern_base_weight(
            usage_pattern
        ).set_label(f"{usage_pattern.name} fabrication weight in impact repartition")

    def update_fabrication_impact_repartition_weights(self):
        """Per-{class:EdgeUsagePattern} weight used to attribute downstream fabrication-phase emissions back to each pattern, proportional to concurrent edge journeys."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_fabrication_impact_repartition_weights(usage_pattern)

    def update_dict_element_in_usage_impact_repartition_weights(self, usage_pattern: "EdgeUsagePattern"):
        self.usage_impact_repartition_weights[usage_pattern] = (
            self._edge_usage_pattern_base_weight(usage_pattern) * usage_pattern.country.average_carbon_intensity
        ).set_label(f"{usage_pattern.name} usage weight in impact repartition")

    def update_usage_impact_repartition_weights(self):
        """Per-{class:EdgeUsagePattern} weight used to attribute downstream usage-phase emissions, scaled by the country's grid carbon intensity so high-carbon grids draw a larger share."""
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_usage_impact_repartition_weights(usage_pattern)
