from typing import List

from efootprint.core.country import Country
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.core.usage.job import Job
from efootprint.core.hardware.network import Network
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


class UsagePattern(ModelingObject):
    def __init__(self, name: str, usage_journey: UsageJourney, devices: List[Device],
                 network: Network, country: Country, hourly_usage_journey_starts: ExplainableHourlyQuantities):
        super().__init__(name)
        self.utc_hourly_usage_journey_starts = EmptyExplainableObject()
        self.nb_usage_journeys_in_parallel = EmptyExplainableObject()
        self.devices_energy = EmptyExplainableObject()
        self.devices_energy_footprint = EmptyExplainableObject()
        self.devices_fabrication_footprint = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.hourly_usage_journey_starts = hourly_usage_journey_starts.set_label(f"{self.name} hourly nb of visits")
        self.usage_journey = usage_journey
        self.devices = devices
        self.network = network
        self.country = country

    @property
    def calculated_attributes(self):
        return ["utc_hourly_usage_journey_starts", "nb_usage_journeys_in_parallel", "devices_energy",
                "devices_energy_footprint", "devices_fabrication_footprint", "energy_footprint",
                "instances_fabrication_footprint"]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return self.jobs

    @property
    def jobs(self) -> List[Job]:
        return self.usage_journey.jobs

    @property
    def systems(self) -> List:
        return self.modeling_obj_containers

    def update_utc_hourly_usage_journey_starts(self):
        utc_hourly_usage_journey_starts = self.hourly_usage_journey_starts.convert_to_utc(
            local_timezone=self.country.timezone)

        self.utc_hourly_usage_journey_starts = utc_hourly_usage_journey_starts.set_label(f"{self.name} UTC")

    def update_nb_usage_journeys_in_parallel(self):
        nb_of_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            self.utc_hourly_usage_journey_starts, self.usage_journey.duration)

        self.nb_usage_journeys_in_parallel = nb_of_usage_journeys_in_parallel.set_label(
            f"{self.name} hourly nb of user journeys in parallel")

    def update_devices_energy(self):
        total_devices_energy_spent_over_one_full_hour = sum(
            [device.power for device in self.devices]) * ExplainableQuantity(1 * u.hour, "one full hour")

        devices_energy = (self.nb_usage_journeys_in_parallel * total_devices_energy_spent_over_one_full_hour).to(u.kWh)

        self.devices_energy = devices_energy.set_label(f"Energy consumed by {self.name} devices")

    def update_devices_energy_footprint(self):
        energy_footprint = (self.devices_energy * self.country.average_carbon_intensity).to(u.kg)
        
        self.devices_energy_footprint = energy_footprint.set_label(f"Devices energy footprint of {self.name}")

    def update_devices_fabrication_footprint(self):
        devices_fabrication_footprint_over_one_hour = EmptyExplainableObject()
        for device in self.devices:
            device_uj_fabrication_footprint = (
                    device.carbon_footprint_fabrication * ExplainableQuantity(1 * u.hour, "one hour")
                    / (device.lifespan * device.fraction_of_usage_time)
            ).to(u.g).set_label(
                f"{device.name} fabrication footprint over one hour")
            devices_fabrication_footprint_over_one_hour += device_uj_fabrication_footprint

        devices_fabrication_footprint = (
                self.nb_usage_journeys_in_parallel * devices_fabrication_footprint_over_one_hour).to(u.kg)

        self.devices_fabrication_footprint = devices_fabrication_footprint.set_label(
            f"Devices fabrication footprint of {self.name}")

    def update_energy_footprint(self):
        # The copy is to create a new ExplainableObject with the same value as the previous one, and hence make clear
        # in the calculation graph that the usage pattern energy footprint is the same as the devices energy footprint
        self.energy_footprint = self.devices_energy_footprint.copy().set_label(f"{self.name} total energy footprint")

    def update_instances_fabrication_footprint(self):
        self.instances_fabrication_footprint = self.devices_fabrication_footprint.copy().set_label(
            f"{self.name} total fabrication footprint")
