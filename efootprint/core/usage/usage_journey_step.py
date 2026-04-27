from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.job import JobBase

if TYPE_CHECKING:
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.hardware.network import Network


class UsageJourneyStep(ModelingObject):
    """One step within a {class:UsageJourney}, characterised by how long the user spends on it and which {class:Job}s it triggers on the server side."""

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
