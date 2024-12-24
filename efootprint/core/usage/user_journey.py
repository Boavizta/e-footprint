from typing import List, Type

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject, ModelingObjectMix
from efootprint.core.hardware.servers.server_base_class import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.user_journey_step import UserJourneyStep
from efootprint.core.usage.job import Job


class UserJourney(ModelingObject):
    def __init__(self, name: str, user_journey_step_mix: ModelingObjectMix):
        super().__init__(name)
        self.duration = EmptyExplainableObject()
        self.user_journey_step_mix = user_journey_step_mix

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
        for uj_step in self.user_journey_step_mix:
            output_list += uj_step.jobs

        return output_list

    def add_step(self, step: UserJourneyStep) -> None:
        step.add_obj_to_modeling_obj_containers(self)
        self.user_journey_step_mix = self.user_journey_step_mix + [step]

    def update_duration(self):
        user_time_spent_sum = sum(
            [uj_step.user_time_spent for uj_step in self.user_journey_step_mix], start=EmptyExplainableObject())

        self.duration = user_time_spent_sum.set_label(f"Duration of {self.name}")
