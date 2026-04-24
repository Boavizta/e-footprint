from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.core.country import Country
from efootprint.core.hardware.network import Network
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.job import JobBase


class EdgeUsagePattern(ModelingObject):
    def __init__(self, name: str, edge_usage_journey: EdgeUsageJourney, network: Network,
                 country: Country, hourly_edge_usage_journey_starts: ExplainableHourlyQuantities):
        super().__init__(name)
        self.utc_hourly_edge_usage_journey_starts = EmptyExplainableObject()

        self.hourly_edge_usage_journey_starts = hourly_edge_usage_journey_starts.to(u.occurrence).set_label(
            "Hourly nb of edge device starts")
        self.edge_usage_journey = edge_usage_journey
        self.network = network
        self.country = country

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> (List[EdgeUsageJourney]):
        return [self.edge_usage_journey]

    @property
    def calculated_attributes(self):
        return (["utc_hourly_edge_usage_journey_starts"] + super().calculated_attributes)

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        return self.edge_usage_journey.recurrent_edge_device_needs

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        return self.edge_usage_journey.recurrent_server_needs

    @property
    def jobs(self) -> List["JobBase"]:
        return self.edge_usage_journey.jobs

    def update_utc_hourly_edge_usage_journey_starts(self):
        utc_hourly_edge_usage_journey_starts = self.hourly_edge_usage_journey_starts.convert_to_utc(
            local_timezone=self.country.timezone)

        self.utc_hourly_edge_usage_journey_starts = utc_hourly_edge_usage_journey_starts.set_label(
            f"{self.name} UTC")

    def update_dict_element_in_fabrication_impact_repartition_weights(self, country: "Country"):
        self.fabrication_impact_repartition_weights[country] = ExplainableQuantity(
            1 * u.dimensionless, label="Impact repartition weight")

    def update_fabrication_impact_repartition_weights(self):
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        self.update_dict_element_in_fabrication_impact_repartition_weights(self.country)

    def update_dict_element_in_usage_impact_repartition_weights(self, country: "Country"):
        self.usage_impact_repartition_weights[country] = ExplainableQuantity(
            1 * u.dimensionless, label="Impact repartition weight")

    def update_usage_impact_repartition_weights(self):
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        self.update_dict_element_in_usage_impact_repartition_weights(self.country)
