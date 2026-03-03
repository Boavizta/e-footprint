from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
    default_values =  {"user_time_spent": SourceValue(1 * u.min)}

    def __init__(self, name: str, user_time_spent: ExplainableQuantity, jobs: List[JobBase]):
        super().__init__(name)
        self.user_time_spent = user_time_spent
        self.user_time_spent.set_label(f"Time spent on step {self.name}")
        self.jobs = jobs

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["UsageJourney"] | List[JobBase]:
        return self.jobs

    @property
    def usage_journeys(self) -> List["UsageJourney"]:
        return self.modeling_obj_containers

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return list(set(sum([uj.usage_patterns for uj in self.usage_journeys], start=[])))

    @property
    def networks(self) -> List["Network"]:
        return list(set([up.network for up in self.usage_patterns]))

    @property
    def calculated_attributes(self) -> List[str]:
        return ["impact_repartition_weights", "impact_repartition_weight_sum", "impact_repartition"]

    def update_dict_element_in_impact_repartition_weights(self, usage_journey: "UsageJourney"):
        nb_of_occurrences_per_container = self.nb_of_occurrences_per_container
        weight = (sum([up.utc_hourly_usage_journey_starts for up in usage_journey.usage_patterns],
                      start=EmptyExplainableObject())
                * nb_of_occurrences_per_container[usage_journey]).set_label(
            f"{usage_journey.name} weight in {self.name} impact repartition")

        self.impact_repartition_weights[usage_journey] = weight

    def update_impact_repartition_weights(self):
        self.impact_repartition_weights = ExplainableObjectDict()
        for usage_journey in self.usage_journeys:
            self.update_dict_element_in_impact_repartition_weights(usage_journey)
