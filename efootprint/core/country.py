from typing import List

import pytz

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u


class Country(ModelingObject):
    @classmethod
    def default_values(cls):
        return {
            "average_carbon_intensity": SourceValue(50 * u.g / u.kWh, label="Average carbon intensity of the country"),
            "timezone": SourceObject(pytz.timezone('Europe/Paris'), label="Country timezone")
        }

    def __init__(
            self, name: str, short_name: str, average_carbon_intensity: ExplainableQuantity,
            timezone: ExplainableTimezone):
        super().__init__(name)
        self.short_name = short_name
        self.average_carbon_intensity = average_carbon_intensity.set_label(f"Average carbon intensity of {self.name}")
        self.timezone = timezone.set_label(f"{self.name} timezone")

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["short_name"]

    @property
    def usage_patterns(self):
        return self.modeling_obj_containers

    @property
    def systems(self) -> List:
        return list(set(sum([usage_pattern.systems for usage_pattern in self.usage_patterns], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return self.usage_patterns
