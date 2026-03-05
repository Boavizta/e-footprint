from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import HardwareBase

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep


class Device(HardwareBase):
    default_values =  {
            "carbon_footprint_fabrication": SourceValue(150 * u.kg),
            "power": SourceValue(50 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day)
        }

    @classmethod
    def smartphone(cls, name="Default smartphone", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(30 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(1 * u.W),
            "lifespan": SourceValue(3 * u.year),
            "fraction_of_usage_time": SourceValue(3.6 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def laptop(cls, name="Default laptop", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(156 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(50 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def box(cls, name="Default box", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(78 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(10 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "fraction_of_usage_time": SourceValue(24 * u.hour / u.day)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def screen(cls, name="Default screen", **kwargs):
        output_args = {
            "carbon_footprint_fabrication": SourceValue(222 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(30 * u.W),
            "lifespan": SourceValue(6 * u.year),
            "fraction_of_usage_time": SourceValue(7 * u.hour / u.day)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.smartphone, cls.laptop, cls.box, cls.screen]

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity, fraction_of_usage_time: ExplainableQuantity):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan, fraction_of_usage_time)

        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return self.modeling_obj_containers

    @property
    def usage_journey_steps(self) -> List["UsageJourneyStep"]:
        return list(set(sum([usage_pattern.usage_journey.uj_steps for usage_pattern in self.usage_patterns], [])))

    @property
    def calculated_attributes(self) -> List[str]:
        return ["energy_footprint", "instances_fabrication_footprint"] + super().calculated_attributes

    def update_energy_footprint(self):
        energy_spent_over_one_full_hour_by_one_device = self.power * ExplainableQuantity(1 * u.hour, "one full hour")

        energy_footprint = EmptyExplainableObject()

        for usage_pattern in self.usage_patterns:
            instances_energy = (
                    usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
                    * energy_spent_over_one_full_hour_by_one_device).to(u.kWh)
            energy_footprint += (instances_energy * usage_pattern.country.average_carbon_intensity).to(u.kg)

        self.energy_footprint = energy_footprint.set_label(f"Devices energy footprint of {self.name}")

    def update_instances_fabrication_footprint(self):
        instances_fabrication_footprint = EmptyExplainableObject()
        device_fabrication_footprint_over_one_hour = (
                self.carbon_footprint_fabrication * ExplainableQuantity(1 * u.hour, "one hour")
                / (self.lifespan * self.fraction_of_usage_time)
        ).to(u.g).set_label(f"{self.name} fabrication footprint over one hour")

        for usage_pattern in self.usage_patterns:
            instances_fabrication_footprint += (
                usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
                * device_fabrication_footprint_over_one_hour).to(u.kg)

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Devices fabrication footprint of {self.name}")

    def update_dict_element_in_impact_repartition_weights(self, uj_step: "UsageJourneyStep"):
        self.impact_repartition_weights[uj_step] = (
                uj_step.user_time_spent
                * sum([self.nb_of_occurrences_per_container[up] * uj_step.nb_of_occurrences_per_container[up.usage_journey]
                       * up.utc_hourly_usage_journey_starts
                       for up in self.usage_patterns if up in uj_step.usage_patterns])).set_label(
                f"{uj_step.name} weight in {self.name} impact repartition")

    def update_impact_repartition_weights(self):
        self.impact_repartition_weights = ExplainableObjectDict()
        for uj_step in self.usage_journey_steps:
            self.update_dict_element_in_impact_repartition_weights(uj_step)
