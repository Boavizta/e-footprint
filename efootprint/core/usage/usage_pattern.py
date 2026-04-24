from typing import List

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.core.country import Country
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.job import Job
from efootprint.core.hardware.network import Network
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


class UsagePattern(ModelingObject):
    def __init__(self, name: str, usage_journey: UsageJourney, devices: List[Device],
                 network: Network, country: Country, hourly_usage_journey_starts: ExplainableHourlyQuantities):
        super().__init__(name)
        self.hourly_usage_journey_starts = hourly_usage_journey_starts.to(u.occurrence).set_label(
            "Hourly nb of visits")
        self.usage_journey = usage_journey
        self.devices = devices
        self.network = network
        self.country = country

        self.utc_hourly_usage_journey_starts = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[UsageJourney]:
        return [self.usage_journey]

    @property
    def calculated_attributes(self):
        return ["utc_hourly_usage_journey_starts"] + super().calculated_attributes

    @property
    def jobs(self) -> List[Job]:
        return self.usage_journey.jobs

    def update_utc_hourly_usage_journey_starts(self):
        utc_hourly_usage_journey_starts = self.hourly_usage_journey_starts.convert_to_utc(
            local_timezone=self.country.timezone)

        self.utc_hourly_usage_journey_starts = utc_hourly_usage_journey_starts.set_label("UTC")

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
