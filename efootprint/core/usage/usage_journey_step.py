from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import (
    WeightedExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.core.usage.job import JobBase
from efootprint.abstract_modeling_classes.reactive_core import computed_dict

if TYPE_CHECKING:
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.hardware.network import Network


@dataclass(frozen=True)
class UsageJourneyStepCoordinate:
    """Stable key for one step occupancy calculation along an actual pattern-to-journey path."""

    usage_pattern: "UsagePattern"
    usage_journey: "UsageJourney"

    def __str__(self):
        return f"{self.usage_pattern.name} / {self.usage_journey.name}"

    @property
    def id(self):
        return f"{self.usage_pattern.id}/journey/{self.usage_journey.id}"


class UsageJourneyStep(ModelingObject):
    """One step within a {class:UsageJourney}, characterised by how long the user spends on it and which {class:Job}s it triggers on the server side."""

    param_descriptions = {
        "user_time_spent": (
            "Wall-clock time the user spends on this step (during which her device is powered on)."),
        "jobs": (
            "Mapping from {class:Job} to how many times it is triggered on the server side during one occurrence "
            "of this step. The same {class:Job} can appear in several steps, with its own count in each."),
    }

    default_values =  {"user_time_spent": SourceValue(1 * u.min)}

    weight_labels = {"jobs": "Times per step"}

    def __init__(self, name: str, user_time_spent: ExplainableQuantity, jobs: WeightedExplainableObjectDict[JobBase]):
        super().__init__(name)
        self.user_time_spent = user_time_spent
        self.user_time_spent.set_label(f"Time spent by user")
        self.jobs = to_weighted_explainable_object_dict(jobs, weight_label=self.weight_labels["jobs"])


    @property
    def usage_journeys(self) -> List["UsageJourney"]:
        return self.modeling_obj_containers

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return list(dict.fromkeys(sum([uj.usage_patterns for uj in self.usage_journeys], start=[])))

    @property
    def usage_coordinates(self):
        return tuple(
            UsageJourneyStepCoordinate(pattern, journey)
            for journey in self.usage_journeys for pattern in journey.usage_patterns
            if journey in pattern.usage_journeys
        )

    @property
    def networks(self) -> List["Network"]:
        return list(dict.fromkeys([up.network for up in self.usage_patterns]))

    @computed_dict(keys="usage_coordinates")
    def hourly_avg_occurrences_per_usage_coordinate(self, coordinate: UsageJourneyStepCoordinate):
        """The step's concurrent occupancy per usage pattern — the journeys concurrently inside the step's
        [delay, delay + times_per_journey × user_time_spent] window, computed as the difference of
        journey-parallel counts at the window's end vs start offsets (exact for fractional offsets).
        Consecutive windows telescope, so summing over a journey's steps tiles
        nb_usage_journeys_in_parallel_per_usage_pattern. Attribution-only primitive (the Device occupancy weight)."""
        up = coordinate.usage_pattern
        journey = coordinate.usage_journey
        journey_starts = up.utc_hourly_occurrences * up.usage_journeys[journey]
        occupancy = EmptyExplainableObject()
        delay_between_uj_start_and_step_start = EmptyExplainableObject()
        for journey_step, times_per_journey in journey.uj_steps.items():
            delay_at_step_end = (delay_between_uj_start_and_step_start
                                 + times_per_journey * journey_step.user_time_spent)
            if journey_step == self:
                occupancy += (
                    compute_nb_avg_hourly_occurrences(journey_starts, delay_at_step_end)
                    - compute_nb_avg_hourly_occurrences(journey_starts, delay_between_uj_start_and_step_start))
            delay_between_uj_start_and_step_start = delay_at_step_end
        # The difference of two FFT convolutions can leave ~-1e-6 noise at mathematically-zero hours;
        # clip to >= 0 like compute_nb_avg_hourly_occurrences does internally for the single-convolution case.
        occupancy = occupancy.np_compared_with(EmptyExplainableObject(), "max")
        return occupancy.to(u.concurrent).set_label(f"{self.name} hourly occupancy in {up.name}")
