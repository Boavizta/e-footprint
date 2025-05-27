from typing import List, Type

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job


class UsageJourney(ModelingObject):
    def __init__(self, name: str, uj_steps: List[UsageJourneyStep]):
        super().__init__(name)
        self.duration = EmptyExplainableObject()
        self.uj_steps = uj_steps

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()

    @property
    def calculated_attributes(self):
        return ["duration"]

    @property
    def servers(self) -> List[Server]:
        servers = set()
        for job in self.jobs:
            servers = servers | {job.server}

        return list(servers)

    @property
    def storages(self) -> List[Storage]:
        storages = set()
        for job in self.jobs:
            storages = storages | {job.server.storage}

        return list(storages)

    @property
    def usage_patterns(self):
        return self.modeling_obj_containers

    @property
    def systems(self) -> List:
        return list(set(sum([up.systems for up in self.usage_patterns], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[Type["UsagePattern"]]:
        if self.usage_patterns:
            return self.usage_patterns
        else:
            return self.jobs

    @property
    def jobs(self) -> List[Job]:
        output_list = []
        for uj_step in self.uj_steps:
            output_list += uj_step.jobs

        return output_list

    def update_duration(self):
        user_time_spent_sum = sum(
            [uj_step.user_time_spent for uj_step in self.uj_steps], start=EmptyExplainableObject())

        self.duration = user_time_spent_sum.set_label(f"Duration of {self.name}")
