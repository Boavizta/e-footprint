from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.attribution import Atom
from efootprint.core.hardware.hardware_base import HardwareBase
from efootprint.core.lifecycle_phases import LifeCyclePhases

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep


class Device(HardwareBase):
    """End-user hardware (smartphone, laptop, set-top box, screen) on which a {class:UsageJourney} is performed. Contributes both fabrication and electricity-use emissions to each {class:UsagePattern} that runs on it."""

    pitfalls = (
        "{param:Device.fraction_of_usage_time} is used to compute effective usage lifespan by multiplying with device "
        "lifespan in years. This effective usage lifespan is then used to compute fabrication amortization.")

    interactions = (
        "Pass a list of {class:Device}s to {param:UsagePattern.devices}. Use the archetype helpers "
        "(`Device.smartphone()`, `Device.laptop()`, `Device.box()`, `Device.screen()`) for sensible defaults.")

    param_descriptions = {
        **HardwareBase.param_descriptions,
        "power": (
            "Electrical power drawn by the device while a user is interacting with it."),
        "fraction_of_usage_time": (
            "Fraction of each calendar day during which the device is in use across all activities, used to "
            "scale lifespan in years to effective usage lifespan."),
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
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint = EmptyExplainableObject()

    @property
    def usage_patterns(self) -> List["UsagePattern"]:
        return self.modeling_obj_containers

    @property
    def usage_journey_steps(self) -> List["UsageJourneyStep"]:
        return list(dict.fromkeys(sum([usage_pattern.usage_journey.uj_steps for usage_pattern in self.usage_patterns], [])))

    calculated_attributes: List[str] = [
        "energy_footprint_per_usage_pattern",
        "energy_footprint",
        "instances_fabrication_footprint_per_usage_pattern",
        "instances_fabrication_footprint",
    ] + HardwareBase.calculated_attributes

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

    @property
    def device_fabrication_footprint_over_one_hour(self):
        return (self.carbon_footprint_fabrication * ExplainableQuantity(1 * u.hour, "one hour")
                / (self.lifespan * self.fraction_of_usage_time)).to(u.g).set_label(
            "Fabrication footprint over one hour")

    def update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(self, usage_pattern: "UsagePattern"):
        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = (
            usage_pattern.usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern[usage_pattern]
            * self.device_fabrication_footprint_over_one_hour).to(u.kg).set_label(
            f"Fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        """Hourly fabrication-phase emissions of all devices in use, broken down by usage pattern. Equal to one device's hourly amortised embodied carbon (lifespan and usage-time-adjusted) multiplied by the number of journeys concurrently in progress."""
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    def update_instances_fabrication_footprint(self):
        """Total hourly fabrication-phase emissions of all devices in use, summed across all usage patterns that run on this device."""
        self.instances_fabrication_footprint = sum(
            self.instances_fabrication_footprint_per_usage_pattern.values(), start=EmptyExplainableObject()
        ).set_label(f"Devices fabrication footprint")

    def attribution_atoms(self, phase: LifeCyclePhases):
        """One atom per (step, up) cell of the device's patterns — no shares: each cell is computed ground-up
        from the step's occupancy primitive (hourly_avg_occurrences_per_usage_pattern, which sums over the
        step's positions in the journey, so iterating distinct steps covers repeated ones exactly once).

        USAGE        atom = (power × 1h) × occupancy(step, up) × up.country.average_carbon_intensity
        FABRICATION  atom = device_fabrication_footprint_over_one_hour × occupancy(step, up)

        Since occupancies summed over a journey's steps tile nb_usage_journeys_in_parallel, Σ over a
        pattern's steps recovers energy_footprint_per_usage_pattern[up] /
        instances_fabrication_footprint_per_usage_pattern[up], and Σ over all atoms the eager phase totals.
        """
        energy_over_one_occupied_hour = (
            self.power * ExplainableQuantity(1 * u.hour, "one full hour")).to(u.kWh)
        fabrication_over_one_occupied_hour = self.device_fabrication_footprint_over_one_hour
        for usage_pattern in self.usage_patterns:
            for uj_step in dict.fromkeys(usage_pattern.usage_journey.uj_steps):
                occupancy = uj_step.hourly_avg_occurrences_per_usage_pattern[usage_pattern]
                if phase == LifeCyclePhases.USAGE:
                    value = (energy_over_one_occupied_hour * occupancy
                             * usage_pattern.country.average_carbon_intensity)
                else:
                    value = fabrication_over_one_occupied_hour * occupancy
                yield Atom(
                    source=self, stream="single", up=usage_pattern, step=uj_step,
                    value=value.to(u.kg).set_label(
                        f"{self.name} {phase.value.lower()} footprint in {uj_step.name} "
                        f"({usage_pattern.name})"))
