from functools import cached_property
from typing import List, TYPE_CHECKING

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import divide_or_fallback
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
    """A long-running activity of an edge fleet, composed of {class:EdgeFunction}s that run for the {param:EdgeUsageJourney.usage_span} of the deployment and can span several device types."""

    disambiguation = (
        "Use {class:EdgeUsageJourney} for hardware that runs continuously, like a sensor that captures data "
        "every minute or an industrial controller. Use {class:UsageJourney} for user-driven, request-style "
        "interactions in a web context. See {doc:web_vs_edge}.")

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
    def usage_impact_repartition_weights(self) -> ExplainableObjectDict:
        return self.fabrication_impact_repartition_weights

    calculated_attributes: List[str] = (
        ["nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern"]
        + [attr for attr in ModelingObject.calculated_attributes
           if attr not in ("usage_impact_repartition_weights",
                           "usage_impact_repartition_weight_sum",
                           "usage_impact_repartition")])

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

    @cached_property
    def attributed_energy_footprint_per_usage_pattern(self) -> ExplainableObjectDict:
        country_dependent_per_up = {
            up: up.country_dependent_usage_footprint for up in self.edge_usage_patterns}
        country_dependent_total = sum(
            country_dependent_per_up.values(), start=EmptyExplainableObject()
        ).to(u.kg).set_label("Country-dependent edge usage footprint")
        neutral_total = (
            self.attributed_energy_footprint - country_dependent_total
        ).to(u.kg).set_label("Neutral edge usage footprint")
        if np.any(np.asarray(getattr(neutral_total, "magnitude", 0)) < 0):
            raise ValueError(
                f"{self.name}: attributed_energy_footprint must be >= the sum of patterns' "
                f"country_dependent_usage_footprint at every hour, but the neutral remainder is negative.")

        activity_per_up = {up: up.usage_activity_weight for up in self.edge_usage_patterns}
        activity_total = sum(activity_per_up.values(), start=EmptyExplainableObject()).set_label(
            "Edge usage journey activity weight sum")

        attributed = ExplainableObjectDict()
        for up in self.edge_usage_patterns:
            neutral_share = self._neutral_activity_share(activity_per_up[up], activity_total, up.name)
            attributed[up] = (
                country_dependent_per_up[up] + neutral_total * neutral_share
            ).to(u.kg).set_label(f"{up.name} attributed energy footprint")

        return attributed

    @staticmethod
    def _neutral_activity_share(activity_for_pattern, activity_total, pattern_name: str):
        if isinstance(activity_total, EmptyExplainableObject):
            return EmptyExplainableObject()
        if isinstance(activity_total, ExplainableQuantity) and activity_total.magnitude == 0:
            return EmptyExplainableObject()
        # Hours with zero total activity have zero neutral footprint by construction (the upstream attribution
        # chain is itself activity-weighted), so the hourly 0/0 → share = 0 fallback is the correct semantic.
        share = divide_or_fallback(activity_for_pattern, activity_total, fallback=0)
        return share.to(u.concurrent).set_label(f"{pattern_name} neutral usage activity share")
