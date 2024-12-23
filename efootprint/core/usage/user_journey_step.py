from typing import List, Type

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.core.usage.job import Job


class UserJourneyStep(ModelingObject):
    def __init__(self, name: str, user_time_spent: SourceValue, jobs: List[Job]):
        super().__init__(name)

        if not user_time_spent.value.check("[time]"):
            raise ValueError(
                "Variable 'user_time_spent' does not have the appropriate '[time]' dimensionality")
        self.user_time_spent = user_time_spent
        self.user_time_spent.set_label(f"Time spent on step {self.name}")
        self.jobs = ListLinkedToModelingObj(jobs)

    @property
    def user_journeys(self) -> List[Type["UserJourney"]]:
        return self.modeling_obj_containers

    @property
    def usage_patterns(self) -> List[Type["UsagePattern"]]:
        return list(set(sum([uj.usage_patterns for uj in self.user_journeys], start=[])))

    @property
    def systems(self) -> List:
        return list(set(sum([up.systems for up in self.usage_patterns], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[Type["UserJourney"]]:
        if self.user_journeys:
            return self.user_journeys
        else:
            return self.jobs
