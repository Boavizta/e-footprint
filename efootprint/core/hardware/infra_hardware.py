from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import HardwareBase


class InfraHardware(HardwareBase):
    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication, power, lifespan, SourceValue(1 * u.dimensionless, Sources.HYPOTHESIS))
        self.raw_nb_of_instances = EmptyExplainableObject()
        self.nb_of_instances = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def calculated_attributes(self):
        return (
            ["raw_nb_of_instances", "nb_of_instances", "instances_fabrication_footprint", "instances_energy",
             "energy_footprint"])

    @abstractmethod
    def update_raw_nb_of_instances(self):
        pass

    @abstractmethod
    def update_nb_of_instances(self):
        pass

    @abstractmethod
    def update_instances_energy(self):
        pass

    @property
    def jobs(self) -> List[ModelingObject]:
        return self.modeling_obj_containers

    @property
    def systems(self) -> List:
        return list(set(sum([job.systems for job in self.jobs], start=[])))

    def update_instances_fabrication_footprint(self):
        instances_fabrication_footprint = (
                self.carbon_footprint_fabrication * self.nb_of_instances * ExplainableQuantity(1 * u.hour, "one hour")
                / self.lifespan)

        self.instances_fabrication_footprint = instances_fabrication_footprint.to(u.kg).set_label(
                f"Hourly {self.name} instances fabrication footprint")

    def update_energy_footprint(self):
        if getattr(self, "average_carbon_intensity", None) is None:
            raise ValueError(
                f"Variable 'average_carbon_intensity' is not defined in object {self.name}."
                f" This shouldn’t happen as server objects have it as input parameter and Storage as property")
        energy_footprint = (self.instances_energy * self.average_carbon_intensity)

        self.energy_footprint = energy_footprint.to(u.kg).set_label(f"Hourly {self.name} energy footprint")
