from typing import List, TYPE_CHECKING

from efootprint.core.country import Country
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeed


class EdgeUsagePattern(ModelingObject):
    def __init__(self, name: str, edge_usage_journey: EdgeUsageJourney,
                 country: Country, hourly_edge_usage_journey_starts: ExplainableHourlyQuantities):
        super().__init__(name)
        self.utc_hourly_edge_usage_journey_starts = EmptyExplainableObject()
        self.nb_edge_usage_journeys_in_parallel = EmptyExplainableObject()

        self.hourly_edge_usage_journey_starts = hourly_edge_usage_journey_starts.to(u.occurrence).set_label(
            f"{self.name} hourly nb of edge device starts")
        self.edge_usage_journey = edge_usage_journey
        self.country = country

    @property
    def calculated_attributes(self):
        return ["utc_hourly_edge_usage_journey_starts", "nb_edge_usage_journeys_in_parallel"]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["RecurrentEdgeResourceNeed"]:
        return self.recurrent_edge_resource_needs

    @property
    def recurrent_edge_resource_needs(self) -> List["RecurrentEdgeResourceNeed"]:
        return self.edge_usage_journey.recurrent_edge_resource_needs

    def update_utc_hourly_edge_usage_journey_starts(self):
        utc_hourly_edge_usage_journey_starts = self.hourly_edge_usage_journey_starts.convert_to_utc(
            local_timezone=self.country.timezone)

        self.utc_hourly_edge_usage_journey_starts = utc_hourly_edge_usage_journey_starts.set_label(
            f"{self.name} UTC")

    def update_nb_edge_usage_journeys_in_parallel(self):
        nb_of_edge_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            self.utc_hourly_edge_usage_journey_starts, self.edge_usage_journey.usage_span)

        self.nb_edge_usage_journeys_in_parallel = nb_of_edge_usage_journeys_in_parallel.to(u.concurrent).set_label(
            f"{self.name} hourly nb of edge usage journeys in parallel")
