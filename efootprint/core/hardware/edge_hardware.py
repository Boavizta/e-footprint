from abc import abstractmethod
from typing import List, TYPE_CHECKING, Union

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import HardwareBase

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class EdgeHardware(HardwareBase):
    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication, power, lifespan, SourceValue(1 * u.dimensionless))
        self.nb_of_instances = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.unitary_power_over_full_timespan = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def calculated_attributes(self):
        return ["nb_of_instances", "instances_fabrication_footprint",
                "unitary_power_over_full_timespan", "instances_energy", "energy_footprint"]

    @property
    def systems(self) -> List:
        return list(set(sum([elt.systems for elt in self.modeling_obj_containers], start=[])))

    @property
    @abstractmethod
    def edge_usage_pattern(self) -> "EdgeUsagePattern":
        pass

    @property
    def average_carbon_intensity(self) -> Union[ExplainableQuantity, EmptyExplainableObject]:
        edge_usage_pattern = self.edge_usage_pattern
        if edge_usage_pattern is not None:
            return edge_usage_pattern.country.average_carbon_intensity
        return EmptyExplainableObject()

    def update_nb_of_instances(self):
        if self.edge_usage_pattern:
            nb_of_instances = self.edge_usage_pattern.nb_edge_usage_journeys_in_parallel.copy()
        else:
            nb_of_instances = EmptyExplainableObject()

        self.nb_of_instances = nb_of_instances.set_label(f"{self.name} nb_of_instances")

    def update_instances_fabrication_footprint(self):
        instances_fabrication_footprint = (
                self.carbon_footprint_fabrication * self.nb_of_instances * ExplainableQuantity(1 * u.hour, "one hour")
                / self.lifespan)

        self.instances_fabrication_footprint = instances_fabrication_footprint.to(u.kg).set_label(
                f"Hourly {self.name} instances fabrication footprint")

    @abstractmethod
    def update_unitary_power_over_full_timespan(self):
        pass

    def update_instances_energy(self):
        unitary_energy_over_full_timespan = (
            self.unitary_power_over_full_timespan * ExplainableQuantity(1 * u.hour, "one hour")
        )

        instances_energy = unitary_energy_over_full_timespan * self.nb_of_instances

        self.instances_energy = instances_energy.to(u.kWh).set_label(
            f"Hourly energy consumed by {self.name} instances")

    def update_energy_footprint(self):
        if getattr(self, "average_carbon_intensity", None) is None:
            raise ValueError(
                f"Variable 'average_carbon_intensity' is not defined in object {self.name}."
                f" This shouldn’t happen as server objects have it as input parameter and Storage as property")
        energy_footprint = (self.instances_energy * self.average_carbon_intensity)

        self.energy_footprint = energy_footprint.to(u.kg).set_label(f"Hourly {self.name} energy footprint")
