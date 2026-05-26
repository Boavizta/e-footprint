from functools import cached_property
from typing import List, TYPE_CHECKING

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import divide_or_fallback
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.hardware.device import Device


class UsageJourney(ModelingObject):
    """An ordered sequence of {class:UsageJourneyStep}s describing one end-to-end interaction a user has with the digital service."""

    _attributed_footprint_cached_property_names = (
        *ModelingObject._attributed_footprint_cached_property_names,
        "attributed_energy_footprint_per_usage_pattern",
    )

    param_descriptions = {
        "uj_steps": (
            "Ordered list of {class:UsageJourneyStep}s that make up the journey. The journey duration is the "
            "sum of step durations."),
    }

    def __init__(self, name: str, uj_steps: List[UsageJourneyStep]):
        super().__init__(name)
        self.uj_steps = uj_steps

        self.duration = EmptyExplainableObject()
        self.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["Device"] | List[UsageJourneyStep]:
        return self.devices + self.uj_steps

    @property
    def servers(self) -> List[Server]:
        servers = set()
        for job in self.jobs:
            if hasattr(job, "server"):
                servers = servers | {job.server}

        return list(servers)

    @property
    def storages(self) -> List[Storage]:
        return list(dict.fromkeys([server.storage for server in self.servers]))

    @property
    def usage_patterns(self):
        return self.modeling_obj_containers

    @property
    def devices(self) -> List["Device"]:
        return list(dict.fromkeys(sum([up.devices for up in self.usage_patterns], [])))

    @property
    def jobs(self) -> List[Job]:
        output_list = []
        for uj_step in self.uj_steps:
            output_list += uj_step.jobs

        return output_list

    @property
    def usage_impact_repartition_weights(self) -> ExplainableObjectDict:
        return self.fabrication_impact_repartition_weights

    calculated_attributes = (
        ["duration", "nb_usage_journeys_in_parallel_per_usage_pattern"]
        + [attr for attr in ModelingObject.calculated_attributes
           if attr not in ("usage_impact_repartition_weights",
                           "usage_impact_repartition_weight_sum",
                           "usage_impact_repartition")])

    def update_duration(self):
        """Total wall-clock time of one journey, equal to the sum of {param:UsageJourneyStep.user_time_spent} across all steps."""
        user_time_spent_sum = sum(
            [uj_step.user_time_spent for uj_step in self.uj_steps], start=EmptyExplainableObject())

        self.duration = user_time_spent_sum.set_label(f"Duration")

    def update_dict_element_in_nb_usage_journeys_in_parallel_per_usage_pattern(self, usage_pattern: "UsagePattern"):
        nb_of_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            usage_pattern.utc_hourly_usage_journey_starts, self.duration)

        self.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern] = nb_of_usage_journeys_in_parallel.to(
            u.concurrent).set_label(f"{usage_pattern.name} hourly nb of user journeys in parallel")

    def update_nb_usage_journeys_in_parallel_per_usage_pattern(self):
        """Hourly count of journeys that are concurrently in progress in each usage pattern, derived from journey starts and journey duration. Used to size devices that are occupied for the full journey duration."""
        self.nb_usage_journeys_in_parallel_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_nb_usage_journeys_in_parallel_per_usage_pattern(usage_pattern)

    def _usage_pattern_base_weight(self, usage_pattern: "UsagePattern"):
        return (
            self.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
            * self.nb_of_occurrences_per_container[usage_pattern]
        )

    def update_dict_element_in_fabrication_impact_repartition_weights(self, usage_pattern: "UsagePattern"):
        self.fabrication_impact_repartition_weights[usage_pattern] = self._usage_pattern_base_weight(
            usage_pattern
        ).set_label(f"{usage_pattern.name} fabrication weight in impact repartition")

    def update_fabrication_impact_repartition_weights(self):
        """Per-usage-pattern weight used to attribute device-side fabrication emissions back to each pattern, proportional to concurrent journeys times journey occurrences."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_fabrication_impact_repartition_weights(usage_pattern)

    @cached_property
    def attributed_energy_footprint_per_usage_pattern(self) -> ExplainableObjectDict:
        country_dependent_per_up = {
            up: up.country_dependent_usage_footprint for up in self.usage_patterns}
        country_dependent_total = sum(
            country_dependent_per_up.values(), start=EmptyExplainableObject()
        ).to(u.kg).set_label("Country-dependent usage footprint")
        neutral_total = (
            self.attributed_energy_footprint - country_dependent_total
        ).to(u.kg).set_label("Neutral usage footprint")
        # attributed_energy_footprint and country_dependent_total are computed along
        # structurally different paths; when they should be equal they can disagree by ULP-scale
        # float noise. Raise only on a real shortfall, not on that noise.
        neutral_mag = np.asarray(getattr(neutral_total, "magnitude", 0))
        attributed_mag = np.asarray(getattr(self.attributed_energy_footprint, "magnitude", 0))
        peak = float(np.abs(attributed_mag).max()) if attributed_mag.size else 0.0
        tolerance = max(1e-6, 1e-6 * peak)
        if np.any(neutral_mag < -tolerance):
            raise ValueError(
                f"{self.name}: attributed_energy_footprint must be >= the sum of patterns' "
                f"country_dependent_usage_footprint at every hour, but the neutral remainder is negative.")

        activity_per_up = {up: up.usage_activity_weight for up in self.usage_patterns}
        activity_total = sum(activity_per_up.values(), start=EmptyExplainableObject()).set_label(
            "Usage journey activity weight sum")

        attributed = ExplainableObjectDict()
        for up in self.usage_patterns:
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
