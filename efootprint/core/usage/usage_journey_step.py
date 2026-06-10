from functools import cached_property
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.core.usage.job import JobBase

if TYPE_CHECKING:
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.hardware.network import Network


class UsageJourneyStep(ModelingObject):
    """One step within a {class:UsageJourney}, characterised by how long the user spends on it and which {class:Job}s it triggers on the server side."""

    _attributed_footprint_cached_property_names = (
        *ModelingObject._attributed_footprint_cached_property_names,
        "hourly_avg_occurrences_per_usage_pattern",
    )

    param_descriptions = {
        "user_time_spent": (
            "Wall-clock time the user spends on this step (during which her device is powered on)."),
        "jobs": (
            "{class:Job}s triggered on the server side during this step. Multiple jobs can fire per step; the "
            "same {class:Job} can appear in several steps."),
    }

    default_values =  {"user_time_spent": SourceValue(1 * u.min)}

    def __init__(self, name: str, user_time_spent: ExplainableQuantity, jobs: List[JobBase]):
        super().__init__(name)
        self.user_time_spent = user_time_spent
        self.user_time_spent.set_label(f"Time spent by user")
        self.jobs = jobs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["UsageJourney"] | List[JobBase]:
        return self.jobs

    @property
    def usage_journeys(self) -> List["UsageJourney"]:
        return self.modeling_obj_containers

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return list(dict.fromkeys(sum([uj.usage_patterns for uj in self.usage_journeys], start=[])))

    @property
    def networks(self) -> List["Network"]:
        return list(dict.fromkeys([up.network for up in self.usage_patterns]))

    @cached_property
    def hourly_avg_occurrences_per_usage_pattern(self):
        """The step's concurrent occupancy per usage pattern — for each position of the step within the pattern's
        journey, the journeys concurrently inside the step's [delay, delay + user_time_spent] window, computed as
        the difference of journey-parallel counts at the window's end vs start offsets (exact for fractional
        offsets). Consecutive windows telescope, so summing over a journey's steps tiles
        nb_usage_journeys_in_parallel_per_usage_pattern. Attribution-only primitive (the Device occupancy weight),
        lazy by design."""
        occurrences_per_usage_pattern = {}
        for up in self.usage_patterns:
            journey_starts = up.utc_hourly_usage_journey_starts
            occupancy = EmptyExplainableObject()
            delay_between_uj_start_and_step_start = EmptyExplainableObject()
            for journey_step in up.usage_journey.uj_steps:
                delay_at_step_end = delay_between_uj_start_and_step_start + journey_step.user_time_spent
                if journey_step == self:
                    occupancy += (
                        compute_nb_avg_hourly_occurrences(journey_starts, delay_at_step_end)
                        - compute_nb_avg_hourly_occurrences(journey_starts, delay_between_uj_start_and_step_start))
                delay_between_uj_start_and_step_start = delay_at_step_end
            occurrences_per_usage_pattern[up] = occupancy.to(u.concurrent).set_label(
                f"{self.name} hourly occupancy in {up.name}")

        return occurrences_per_usage_pattern
