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
    """End-user hardware (smartphone, laptop, set-top box, screen) on which a {class:UsageJourney} is performed. Contributes both fabrication and electricity-use emissions to each {class:UsagePattern} that runs on it."""

    pitfalls = (
        "{param:Device.fraction_of_usage_time} amortises fabrication: a device only used a few hours per day "
        "still consumes its full embodied carbon during the modeling period, but the share attributed to this "
        "service is scaled by the fraction it is actually used.")

    interactions = (
        "Pass a list of {class:Device}s to {param:UsagePattern.devices}. Use the archetype helpers "
        "(`Device.smartphone()`, `Device.laptop()`, `Device.box()`, `Device.screen()`) for sensible defaults.")

    param_descriptions = {
        "carbon_footprint_fabrication": (
            "Embodied carbon emitted to manufacture one device, amortised over its lifespan."),
        "power": (
            "Electrical power drawn by the device while a user is interacting with it."),
        "lifespan": (
            "Expected time before the device is replaced. Embodied carbon is amortised over this duration."),
        "fraction_of_usage_time": (
            "Fraction of each calendar day during which the device is in use across all activities, used to "
            "share its fabrication footprint between this service and other uses of the same device."),
    }

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

        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return self.modeling_obj_containers

    @property
    def usage_journey_steps(self) -> List["UsageJourneyStep"]:
        return list(dict.fromkeys(sum([usage_pattern.usage_journey.uj_steps for usage_pattern in self.usage_patterns], [])))

    @property
    def calculated_attributes(self) -> List[str]:
        return [
            "energy_footprint_per_usage_pattern",
            "energy_footprint",
            "instances_fabrication_footprint",
        ] + super().calculated_attributes

    def update_dict_element_in_energy_footprint_per_usage_pattern(self, usage_pattern: "UsagePattern"):
        energy_spent_over_one_full_hour_by_one_device = self.power * ExplainableQuantity(1 * u.hour, "one full hour")
        instances_energy = (
            usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
            * energy_spent_over_one_full_hour_by_one_device
        ).to(u.kWh)
        self.energy_footprint_per_usage_pattern[usage_pattern] = (
            instances_energy * usage_pattern.country.average_carbon_intensity
        ).to(u.kg).set_label(f"Usage footprint for {usage_pattern.name}")

    def update_energy_footprint_per_usage_pattern(self):
        """Hourly carbon emissions caused by the device's electricity use, broken down by usage pattern. Equal to the energy spent by concurrent journeys times the country's grid carbon intensity."""
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_energy_footprint_per_usage_pattern(usage_pattern)

    def update_energy_footprint(self):
        """Total hourly carbon emissions caused by the device's electricity use, summed across all usage patterns that run on this device."""
        self.energy_footprint = sum(
            self.energy_footprint_per_usage_pattern.values(), start=EmptyExplainableObject()
        ).set_label(f"Devices energy footprint")

    def update_instances_fabrication_footprint(self):
        """Hourly fabrication-phase emissions of all devices in use, equal to one device's hourly amortised embodied carbon (lifespan and usage-time-adjusted) multiplied by the number of journeys concurrently in progress."""
        instances_fabrication_footprint = EmptyExplainableObject()
        device_fabrication_footprint_over_one_hour = (
                self.carbon_footprint_fabrication * ExplainableQuantity(1 * u.hour, "one hour")
                / (self.lifespan * self.fraction_of_usage_time)
        ).to(u.g).set_label("Fabrication footprint over one hour")

        for usage_pattern in self.usage_patterns:
            instances_fabrication_footprint += (
                usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
                * device_fabrication_footprint_over_one_hour).to(u.kg)

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Devices fabrication footprint")

    def update_dict_element_in_fabrication_impact_repartition_weights(self, uj_step: "UsageJourneyStep"):
        weight = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            if usage_pattern not in uj_step.usage_patterns:
                continue
            weight += (
                self.nb_of_occurrences_per_container[usage_pattern]
                * uj_step.nb_of_occurrences_per_container[usage_pattern.usage_journey]
                * usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
                * uj_step.user_time_spent
            )
        self.fabrication_impact_repartition_weights[uj_step] = weight.set_label(
            f"{uj_step.name} fabrication weight in impact repartition"
        )

    def update_fabrication_impact_repartition_weights(self):
        """Per-{class:UsageJourneyStep} weight used to attribute the device's fabrication footprint to the steps that occupy it, proportional to step occurrences times user-time-spent times concurrent journeys."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for uj_step in self.usage_journey_steps:
            self.update_dict_element_in_fabrication_impact_repartition_weights(uj_step)

    def update_dict_element_in_usage_impact_repartition_weights(self, uj_step: "UsageJourneyStep"):
        weight = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            if usage_pattern not in uj_step.usage_patterns:
                continue
            weight += (
                self.energy_footprint_per_usage_pattern[usage_pattern]
                * self.nb_of_occurrences_per_container[usage_pattern]
                * uj_step.nb_of_occurrences_per_container[usage_pattern.usage_journey]
                * uj_step.user_time_spent
            )
        self.usage_impact_repartition_weights[uj_step] = weight.set_label(
            f"{uj_step.name} usage weight in impact repartition"
        )

    def update_usage_impact_repartition_weights(self):
        """Per-{class:UsageJourneyStep} weight used to attribute the device's electricity-use footprint to the steps that occupy it, weighted by per-pattern energy footprint and step occurrence count."""
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for uj_step in self.usage_journey_steps:
            self.update_dict_element_in_usage_impact_repartition_weights(uj_step)
