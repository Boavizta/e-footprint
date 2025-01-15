from typing import List

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject


class Country(ModelingObject):
    def __init__(
            self, name: str, short_name: str, average_carbon_intensity: SourceValue, timezone: SourceObject):
        super().__init__(name)
        self.short_name = short_name
        # "[time]**2 / [length]**2" corresponds to mass over energy I.U.
        if not average_carbon_intensity.value.check("[time]**2 / [length]**2"):
            raise ValueError(
                "Variable 'average_carbon_intensity' does not have mass over energy "
                "('[time]**2 / [length]**2') dimensionality"
            )
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
