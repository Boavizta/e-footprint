from abc import abstractmethod
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import HardwareBase

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class EdgeHardware(HardwareBase):
    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication, power, lifespan, SourceValue(1 * u.dimensionless))
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        self.nb_of_instances_per_usage_pattern = ExplainableObjectDict()
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.nb_of_instances = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def calculated_attributes(self):
        return ["nb_of_instances_per_usage_pattern", "instances_fabrication_footprint_per_usage_pattern",
                "unitary_power_per_usage_pattern", "instances_energy_per_usage_pattern",
                "energy_footprint_per_usage_pattern", "nb_of_instances", "instances_fabrication_footprint",
                "instances_energy", "energy_footprint"]

    @property
    def systems(self) -> List:
        return list(set(sum([elt.systems for elt in self.modeling_obj_containers], start=[])))

    @property
    @abstractmethod
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        pass

    def update_dict_element_in_nb_of_instances_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        self.nb_of_instances_per_usage_pattern[
            usage_pattern] = usage_pattern.nb_edge_usage_journeys_in_parallel.copy().set_label(
            f"Number of {self.name} instances for {usage_pattern.name}")

    def update_nb_of_instances_per_usage_pattern(self):
        self.nb_of_instances_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_nb_of_instances_per_usage_pattern(usage_pattern)

    def update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        instances_fabrication_footprint = (
                self.nb_of_instances_per_usage_pattern[usage_pattern] * self.carbon_footprint_fabrication
                * (ExplainableQuantity(1 * u.hour, "one hour") / self.lifespan))

        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = instances_fabrication_footprint.to(
            u.kg).set_label(f"Hourly {self.name} instances fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    @abstractmethod
    def update_unitary_power_per_usage_pattern(self):
        pass

    def update_dict_element_in_instances_energy_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_energy = self.unitary_power_per_usage_pattern[usage_pattern] * ExplainableQuantity(1 * u.hour,
                                                                                                   "one hour")
        instances_energy = self.nb_of_instances_per_usage_pattern[usage_pattern] * unitary_energy

        self.instances_energy_per_usage_pattern[usage_pattern] = instances_energy.set_label(
            f"Hourly energy consumed by {self.name} instances for {usage_pattern.name}")

    def update_instances_energy_per_usage_pattern(self):
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_energy_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_footprint_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        energy_footprint = (self.instances_energy_per_usage_pattern[usage_pattern] *
                            usage_pattern.country.average_carbon_intensity)
        self.energy_footprint_per_usage_pattern[usage_pattern] = energy_footprint.set_label(
            f"{self.name} energy footprint for {usage_pattern.name}")

    def update_energy_footprint_per_usage_pattern(self):
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_footprint_per_usage_pattern(usage_pattern)

    def sum_calculated_attribute_across_usage_patterns(self, calculated_attribute_name: str,
                                                       calculated_attribute_label: str):
        summed_attribute = EmptyExplainableObject()
        for usage_pattern in self.edge_usage_patterns:
            summed_attribute += getattr(self, calculated_attribute_name)[usage_pattern]

        return summed_attribute.set_label(f"{self.name} {calculated_attribute_label} across usage patterns")

    def update_nb_of_instances(self):
        self.nb_of_instances = self.sum_calculated_attribute_across_usage_patterns(
            "nb_of_instances_per_usage_pattern", "total instances")

    def update_instances_energy(self):
        self.instances_energy = self.sum_calculated_attribute_across_usage_patterns(
            "instances_energy_per_usage_pattern", "total instances energy")

    def update_energy_footprint(self):
        self.energy_footprint = self.sum_calculated_attribute_across_usage_patterns(
            "energy_footprint_per_usage_pattern", "total energy footprint")

    def update_instances_fabrication_footprint(self):
        self.instances_fabrication_footprint = self.sum_calculated_attribute_across_usage_patterns(
            "instances_fabrication_footprint_per_usage_pattern", "total fabrication footprint")
