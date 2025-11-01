from abc import abstractmethod
from typing import List, TYPE_CHECKING, Optional

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge.edge_device import EdgeDevice


class EdgeComponent(ModelingObject):
    @classmethod
    @abstractmethod
    def compatible_root_units(self) -> List["str"]:
        """Return list of acceptable pint units for RecurrentEdgeComponentNeed objects linked to this component."""
        pass

    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):
        super().__init__(name)
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.lifespan = lifespan.set_label(f"Lifespan of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeDevice"]:
        if self.edge_device:
            return [self.edge_device]
        return []

    @property
    def calculated_attributes(self):
        return ["unitary_power_per_usage_pattern", "instances_fabrication_footprint_per_usage_pattern",
                "instances_energy_per_usage_pattern", "energy_footprint_per_usage_pattern",
                "instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    @property
    def recurrent_edge_component_needs(self) -> List["RecurrentEdgeComponentNeed"]:
        from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
        return [container for container in self.modeling_obj_containers
                if isinstance(container, RecurrentEdgeComponentNeed)]

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        from efootprint.core.hardware.edge.edge_device import EdgeDevice
        output = None
        for container in self.modeling_obj_containers:
            if isinstance(container, EdgeDevice):
                if output is not None and container != output:
                    raise PermissionError(
                        f"EdgeComponent object can only be associated with one EdgeDevice object but {self.name} "
                        f"is associated "
                        f"with {[mod_obj.name for mod_obj in self.modeling_obj_containers 
                                 if isinstance(mod_obj, EdgeDevice)]}.")
                output = container

        return output

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([need.edge_usage_patterns for need in self.recurrent_edge_component_needs], start=[])))

    @abstractmethod
    def update_unitary_power_per_usage_pattern(self):
        pass

    def update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        component_fabrication_intensity = (self.carbon_footprint_fabrication / self.lifespan)
        nb_instances = usage_pattern.nb_edge_usage_journeys_in_parallel

        instances_fabrication_footprint = (
            nb_instances * component_fabrication_intensity * ExplainableQuantity(1 * u.hour, "one hour"))

        self.instances_fabrication_footprint_per_usage_pattern[usage_pattern] = instances_fabrication_footprint.to(
            u.kg).set_label(f"Hourly {self.name} instances fabrication footprint for {usage_pattern.name}")

    def update_instances_fabrication_footprint_per_usage_pattern(self):
        """Calculate fabrication footprint per usage pattern."""
        self.instances_fabrication_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_fabrication_footprint_per_usage_pattern(usage_pattern)

    def update_dict_element_in_instances_energy_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        nb_instances = usage_pattern.nb_edge_usage_journeys_in_parallel
        unitary_energy = (self.unitary_power_per_usage_pattern[usage_pattern] *
                        ExplainableQuantity(1 * u.hour, "one hour"))
        instances_energy = nb_instances * unitary_energy

        self.instances_energy_per_usage_pattern[usage_pattern] = instances_energy.set_label(
            f"Hourly energy consumed by {self.name} instances for {usage_pattern.name}")

    def update_instances_energy_per_usage_pattern(self):
        """Calculate energy per usage pattern."""
        self.instances_energy_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_instances_energy_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_footprint_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        energy_footprint = (
                self.instances_energy_per_usage_pattern[usage_pattern] * usage_pattern.country.average_carbon_intensity)

        self.energy_footprint_per_usage_pattern[usage_pattern] = energy_footprint.set_label(
            f"{self.name} energy footprint for {usage_pattern.name}")

    def update_energy_footprint_per_usage_pattern(self):
        """Calculate energy footprint per usage pattern."""
        self.energy_footprint_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_footprint_per_usage_pattern(usage_pattern)

    def update_instances_fabrication_footprint(self):
        """Sum fabrication footprint across usage patterns."""
        instances_fabrication_footprint = sum(
            self.instances_fabrication_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"{self.name} total fabrication footprint across usage patterns")

    def update_instances_energy(self):
        """Sum energy across usage patterns."""
        instances_energy = sum(
            self.instances_energy_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.instances_energy = instances_energy.set_label(
            f"{self.name} total energy consumed across usage patterns")

    def update_energy_footprint(self):
        """Sum energy footprint across usage patterns."""
        energy_footprint = sum(
            self.energy_footprint_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.energy_footprint = energy_footprint.set_label(
            f"{self.name} total energy footprint across usage patterns")
