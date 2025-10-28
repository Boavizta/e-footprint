from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge_component import EdgeComponent


class EdgeDevice(ModelingObject):
    def __init__(self, name: str, structure_fabrication_carbon_footprint: ExplainableQuantity,
                 components: List["EdgeComponent"], lifespan: ExplainableQuantity):
        super().__init__(name)
        self.lifespan = lifespan.set_label(f"Lifespan of {self.name}")
        self.structure_fabrication_carbon_footprint = structure_fabrication_carbon_footprint.set_label(
            f"Structure fabrication carbon footprint of {self.name}")
        self.components = components

        self.total_carbon_footprint_fabrication = EmptyExplainableObject()
        self.total_component_power = EmptyExplainableObject()
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
        return self.components

    @property
    def recurrent_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([need.edge_usage_patterns for need in self.recurrent_needs], start=[])))

    @property
    def calculated_attributes(self):
        return ["total_carbon_footprint_fabrication", "total_component_power", "nb_of_instances_per_usage_pattern",
                "instances_fabrication_footprint_per_usage_pattern", "unitary_power_per_usage_pattern",
                "instances_energy_per_usage_pattern", "energy_footprint_per_usage_pattern", "nb_of_instances",
                "instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    def update_total_carbon_footprint_fabrication(self):
        total_fabrication = self.structure_fabrication_carbon_footprint
        for component in self.components:
            total_fabrication += component.carbon_footprint_fabrication
        self.total_carbon_footprint_fabrication = total_fabrication.set_label(
            f"Total carbon footprint fabrication of {self.name}")

    def update_total_component_power(self):
        total_power = EmptyExplainableObject()
        for component in self.components:
            total_power += component.power
        self.total_component_power = total_power.set_label(f"Total component power of {self.name}")

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
                self.nb_of_instances_per_usage_pattern[usage_pattern] * self.total_carbon_footprint_fabrication
                * (ExplainableQuantity(1 * u.hour, "one hour") / self.lifespan))

        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = instances_fabrication_footprint.to(
            u.kg).set_label(f"Hourly {self.name} instances fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        total_power = EmptyExplainableObject()
        for component in self.components:
            if usage_pattern in component.unitary_power_per_usage_pattern:
                total_power += component.unitary_power_per_usage_pattern[usage_pattern]
        self.unitary_power_per_usage_pattern[usage_pattern] = total_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)

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
