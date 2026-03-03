from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.storage import Storage
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.job import Job

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern


class UsageJourney(ModelingObject):
    def __init__(self, name: str, uj_steps: List[UsageJourneyStep]):
        super().__init__(name)
        self.uj_steps = uj_steps

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["UsagePattern"] | List[UsageJourneyStep]:
        return self.uj_steps

    @property
    def servers(self) -> List[Server]:
        servers = set()
        for job in self.jobs:
            if hasattr(job, "server"):
                servers = servers | {job.server}

        return list(servers)

    @property
    def storages(self) -> List[Storage]:
        return list(set([server.storage for server in self.servers]))

    @property
    def usage_patterns(self):
        return self.modeling_obj_containers

    @property
    def jobs(self) -> List[Job]:
        output_list = []
        for uj_step in self.uj_steps:
            output_list += uj_step.jobs

        return output_list

    @property
    def calculated_attributes(self):
        return ["impact_repartition_weights", "impact_repartition_weight_sum", "impact_repartition"]

    @property
    def duration(self):
        user_time_spent_sum = sum(
            [uj_step.user_time_spent for uj_step in self.uj_steps], start=EmptyExplainableObject())

        return user_time_spent_sum.set_label(f"Duration of {self.name}")

    def update_dict_element_in_impact_repartition_weights(self, usage_pattern: "UsagePattern"):
        weight = usage_pattern.utc_hourly_usage_journey_starts.copy().set_label(
            f"{usage_pattern.name} weight in {self.name} impact repartition")

        self.impact_repartition_weights[usage_pattern] = weight

    def update_impact_repartition_weights(self):
        self.impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_impact_repartition_weights(usage_pattern)
