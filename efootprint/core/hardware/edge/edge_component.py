from abc import abstractmethod
from typing import List, TYPE_CHECKING, Optional

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
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

    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity,
                 power_per_unit: ExplainableQuantity, lifespan: ExplainableQuantity,
                 idle_power_per_unit: ExplainableQuantity,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(name)
        if nb_of_units is None:
            nb_of_units = SourceValue(1 * u.dimensionless)
        self.carbon_footprint_fabrication_per_unit = carbon_footprint_fabrication_per_unit.set_label(
            f"Carbon footprint fabrication per unit")
        self.power_per_unit = power_per_unit.set_label(f"Power per unit")
        self.lifespan = lifespan.set_label(f"Lifespan")
        self.idle_power_per_unit = idle_power_per_unit.set_label(f"Idle power per unit")
        self.nb_of_units = nb_of_units.set_label(f"Number of units")
        self.carbon_footprint_fabrication = EmptyExplainableObject()
        self.power = EmptyExplainableObject()
        self.idle_power = EmptyExplainableObject()
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        self.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()
        self.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        self.fabrication_footprint_per_edge_device = EmptyExplainableObject()
        self.energy_per_edge_device = EmptyExplainableObject()
        self.energy_footprint_per_edge_device = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        if self.edge_device:
            root_groups = self.edge_device._find_root_groups()
            if root_groups:
                return root_groups
            return [self.edge_device]
        return []

    @property
    def calculated_attributes(self):
        return ["carbon_footprint_fabrication", "power", "idle_power",
                "unitary_power_per_usage_pattern", "fabrication_footprint_per_edge_device_per_usage_pattern",
                "energy_per_edge_device_per_usage_pattern", "energy_footprint_per_edge_device_per_usage_pattern",
                "fabrication_footprint_per_edge_device", "energy_per_edge_device",
                "energy_footprint_per_edge_device",
                "total_unitary_hourly_need_per_usage_pattern"]

    @property
    def recurrent_edge_component_needs(self) -> List["RecurrentEdgeComponentNeed"]:
        from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
        return [container for container in self.modeling_obj_containers
                if isinstance(container, RecurrentEdgeComponentNeed)]

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        from efootprint.core.hardware.edge.edge_device import EdgeDevice
        edge_device_containers = [mod_obj for mod_obj in self.modeling_obj_containers
                                 if isinstance(mod_obj, EdgeDevice)]
        if len(edge_device_containers) > 1:
            raise PermissionError(
                f"EdgeComponent object can only be associated once with one EdgeDevice object but {self.name} "
                f"is associated "
                f"with {[mod_obj.name for mod_obj in edge_device_containers]}.")
        elif len(edge_device_containers) == 1:
            return edge_device_containers[0]

        return None

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([need.edge_usage_patterns for need in self.recurrent_edge_component_needs], start=[])))

    @property
    def instances_fabrication_footprint(self):
        if self.edge_device is None:
            return EmptyExplainableObject()
        return self.edge_device.fabrication_footprint_breakdown_by_source.get(self, EmptyExplainableObject())

    @property
    def energy_footprint(self):
        if self.edge_device is None:
            return EmptyExplainableObject()
        return self.edge_device.energy_footprint_breakdown_by_source.get(self, EmptyExplainableObject())

    @abstractmethod
    def update_unitary_power_per_usage_pattern(self):
        pass

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (
            self.carbon_footprint_fabrication_per_unit * self.nb_of_units).set_label(
                f"Carbon footprint fabrication")

    def update_power(self):
        self.power = (self.power_per_unit * self.nb_of_units).set_label(f"Power")

    def update_idle_power(self):
        self.idle_power = (self.idle_power_per_unit * self.nb_of_units).set_label(f"Idle power")

    def update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        component_fabrication_intensity = self.carbon_footprint_fabrication / self.lifespan
        nb_instances = (
            usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern)[usage_pattern]

        fabrication_footprint_per_edge_device = (
            nb_instances * component_fabrication_intensity * ExplainableQuantity(1 * u.hour, "one hour"))

        self.fabrication_footprint_per_edge_device_per_usage_pattern[usage_pattern] = (
            fabrication_footprint_per_edge_device.to(u.kg).set_label(
                f"Hourly {self.name} fabrication footprint per edge device for {usage_pattern.name}")
        )

    def update_fabrication_footprint_per_edge_device_per_usage_pattern(self):
        """Calculate fabrication footprint per usage pattern."""
        self.fabrication_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_fabrication_footprint_per_edge_device_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_per_edge_device_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        nb_instances = (
            usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern)[usage_pattern]
        unitary_energy = self.unitary_power_per_usage_pattern[usage_pattern] * ExplainableQuantity(1 * u.hour, "one hour")
        energy_per_edge_device = nb_instances * unitary_energy

        self.energy_per_edge_device_per_usage_pattern[usage_pattern] = energy_per_edge_device.set_label(
            f"Hourly energy consumed by {self.name} per edge device for {usage_pattern.name}")

    def update_energy_per_edge_device_per_usage_pattern(self):
        """Calculate energy per usage pattern."""
        self.energy_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_per_edge_device_per_usage_pattern(usage_pattern)

    def update_dict_element_in_energy_footprint_per_edge_device_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        energy_footprint = (
            self.energy_per_edge_device_per_usage_pattern[usage_pattern] * usage_pattern.country.average_carbon_intensity
        )

        self.energy_footprint_per_edge_device_per_usage_pattern[usage_pattern] = energy_footprint.set_label(
            f"Energy footprint per edge device for {usage_pattern.name}").to(u.kg)

    def update_energy_footprint_per_edge_device_per_usage_pattern(self):
        """Calculate energy footprint per usage pattern."""
        self.energy_footprint_per_edge_device_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_energy_footprint_per_edge_device_per_usage_pattern(usage_pattern)

    def update_fabrication_footprint_per_edge_device(self):
        """Sum fabrication footprint across usage patterns."""
        fabrication_footprint_per_edge_device = sum(
            self.fabrication_footprint_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.fabrication_footprint_per_edge_device = fabrication_footprint_per_edge_device.set_label(
            "Total fabrication footprint per edge device across usage patterns")

    def update_energy_per_edge_device(self):
        """Sum energy across usage patterns."""
        energy_per_edge_device = sum(
            self.energy_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.energy_per_edge_device = energy_per_edge_device.set_label(
            "Total energy consumed per edge device across usage patterns")

    def update_energy_footprint_per_edge_device(self):
        """Sum energy footprint across usage patterns."""
        energy_footprint = sum(
            self.energy_footprint_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        self.energy_footprint_per_edge_device = energy_footprint.set_label(
            "Total energy footprint per edge device across usage patterns")

    def update_dict_element_in_total_unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        self.total_unitary_hourly_need_per_usage_pattern[usage_pattern] = sum(
            [
                recurrent_need.unitary_hourly_need_per_usage_pattern.get(usage_pattern, EmptyExplainableObject())
                for recurrent_need in self.recurrent_edge_component_needs
            ],
            start=EmptyExplainableObject(),
        ).set_label(f"Total hourly need on {self.name} for {usage_pattern.name}")

    def update_total_unitary_hourly_need_per_usage_pattern(self):
        self.total_unitary_hourly_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_total_unitary_hourly_need_per_usage_pattern(usage_pattern)
