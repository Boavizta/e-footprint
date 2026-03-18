from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
    def calculated_attributes(self):
        return ["duration", "nb_usage_journeys_in_parallel_per_usage_pattern"] + super().calculated_attributes

    def update_duration(self):
        user_time_spent_sum = sum(
            [uj_step.user_time_spent for uj_step in self.uj_steps], start=EmptyExplainableObject())

        self.duration = user_time_spent_sum.set_label(f"Duration of {self.name}")

    def update_dict_element_in_nb_usage_journeys_in_parallel_per_usage_pattern(self, usage_pattern: "UsagePattern"):
        nb_of_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            usage_pattern.utc_hourly_usage_journey_starts, self.duration)

        self.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern] = nb_of_usage_journeys_in_parallel.to(
            u.concurrent).set_label(f"{usage_pattern.name} hourly nb of user journeys in parallel")

    def update_nb_usage_journeys_in_parallel_per_usage_pattern(self):
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
        ).set_label(f"{usage_pattern.name} fabrication weight in {self.name} impact repartition")

    def update_fabrication_impact_repartition_weights(self):
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_fabrication_impact_repartition_weights(usage_pattern)

    def update_dict_element_in_usage_impact_repartition_weights(self, usage_pattern: "UsagePattern"):
        self.usage_impact_repartition_weights[usage_pattern] = (
            self._usage_pattern_base_weight(usage_pattern) * usage_pattern.country.average_carbon_intensity
        ).set_label(f"{usage_pattern.name} usage weight in {self.name} impact repartition")

    def update_usage_impact_repartition_weights(self):
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_usage_impact_repartition_weights(usage_pattern)
