from typing import List, Type

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.constants.units import u
from efootprint.core.usage.job import JobBase


class UsageJourneyStep(ModelingObject):
    @classmethod
    def default_values(cls):
        return {"user_time_spent": SourceValue(1 * u.min)}

    def __init__(self, name: str, user_time_spent: ExplainableQuantity, jobs: List[JobBase]):
        super().__init__(name)
        self.user_time_spent = user_time_spent
        self.user_time_spent.set_label(f"Time spent on step {self.name}")
        self.jobs = ListLinkedToModelingObj(jobs)

    @property
    def usage_journeys(self) -> List[Type["UsageJourney"]]:
        return self.modeling_obj_containers

    @property
    def usage_patterns(self) -> List[Type["UsagePattern"]]:
        return list(set(sum([uj.usage_patterns for uj in self.usage_journeys], start=[])))

    @property
    def systems(self) -> List:
        return list(set(sum([up.systems for up in self.usage_patterns], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[Type["UsageJourney"]]:
        if self.usage_journeys:
            return self.usage_journeys
        else:
            return self.jobs
