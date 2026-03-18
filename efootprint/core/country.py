from typing import List, TYPE_CHECKING

import pytz

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.system import System


class Country(ModelingObject):
    default_values =  {
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
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return self.usage_patterns

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["short_name"]

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return self.modeling_obj_containers

    def update_dict_element_in_fabrication_impact_repartition_weights(self, system: "System"):
        self.fabrication_impact_repartition_weights[system] = ExplainableQuantity(
            1 * u.dimensionless, label="Impact repartition weight")

    def update_fabrication_impact_repartition_weights(self):
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for system in self.systems:
            self.update_dict_element_in_fabrication_impact_repartition_weights(system)

    def update_dict_element_in_usage_impact_repartition_weights(self, system: "System"):
        self.usage_impact_repartition_weights[system] = ExplainableQuantity(
            1 * u.dimensionless, label="Impact repartition weight")

    def update_usage_impact_repartition_weights(self):
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for system in self.systems:
            self.update_dict_element_in_usage_impact_repartition_weights(system)
            
