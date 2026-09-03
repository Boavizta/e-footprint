from typing import List

from efootprint.core.country import Country
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.job import Job
from efootprint.core.hardware.network import Network
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    PositiveWeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute


class UsagePattern(ModelingObject):
    """A population of users that performs weighted {class:UsageJourney}s in one shared context."""

    disambiguation = (
        "Use {class:UsagePattern} for traffic where each {class:UsageJourney} start is independent. Use "
        "{class:EdgeUsagePattern} for edge devices that run continuously and trigger periodic loads. See "
        "{doc:web_vs_edge}.")

    param_descriptions = {
        "usage_journeys": (
            "Non-empty mapping from each {class:UsageJourney} to its average number of executions per pattern "
            "occurrence. Weights must be strictly positive and do not need to sum to one."),
        "devices": (
            "Devices that users perform the journey on. Fabrication and energy footprints of each device are "
            "weighted by the time the journey occupies on it."),
        "network": (
            "{class:Network} carrying traffic between the user's device and the servers."),
        "country": (
            "{class:Country} where the users are located. Drives device-side electricity carbon intensity and "
            "the timezone of {param:UsagePattern.hourly_occurrences}."),
        "hourly_occurrences": (
            "Hourly timeseries giving the number of pattern occurrences in each hour of the modeling period, "
            "expressed in the country's local timezone."),
    }

    weight_labels = {"usage_journeys": "Journeys per pattern occurrence"}

    def __init__(self, name: str, usage_journeys: PositiveWeightedExplainableObjectDict[UsageJourney],
                 devices: List[Device],
                 network: Network, country: Country, hourly_occurrences: ExplainableHourlyQuantities):
        super().__init__(name)
        self.hourly_occurrences = hourly_occurrences.to(u.occurrence).set_label("Hourly nb of pattern occurrences")
        normalized_journeys = PositiveWeightedExplainableObjectDict(to_weighted_explainable_object_dict(
            usage_journeys, weight_label=self.weight_labels["usage_journeys"]))
        self.usage_journeys = normalized_journeys
        self._validate_has_usage_journey()
        self.devices = devices
        self.network = network
        self.country = country

    def _validate_has_usage_journey(self):
        if not self.usage_journeys:
            raise ValueError(f"UsagePattern '{self.name}' requires at least one usage journey")

    @property
    def jobs(self) -> List[Job]:
        return list(dict.fromkeys(job for journey in self.usage_journeys for job in journey.jobs))

    @computed_attribute(guard=True)
    def usage_journeys_validation(self):
        """Validates that the pattern always contains at least one journey."""
        self._validate_has_usage_journey()
        return EmptyExplainableObject()

    @computed_attribute
    def utc_hourly_occurrences(self):
        """Hourly pattern occurrences converted from the country's local timezone to UTC."""
        return self.hourly_occurrences.convert_to_utc(local_timezone=self.country.timezone).set_label(
            "Hourly nb of pattern occurrences (UTC)")
