from abc import abstractmethod
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.reactive_core import (
    computed_attribute, computed_dict, ReverseCollection, ReverseLink)

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

    param_descriptions = {
        "carbon_footprint_fabrication_per_unit": (
            "Embodied carbon emitted to manufacture one unit of the component."),
        "power_per_unit": (
            "Electrical power drawn by one fully-loaded unit."),
        "lifespan": (
            "Expected time before a unit is replaced. Embodied carbon is amortised over this duration."),
        "idle_power_per_unit": (
            "Electrical power drawn by one idle unit."),
        "nb_of_units": (
            "Number of identical units in the component."),
    }

    # power_per_unit, lifespan and idle_power_per_unit are None (and not stored) for subclasses that
    # compute them from the parent device (the EdgeAppliance and EdgeComputer internal components) —
    # assigning a computed name raises.
    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity = None,
                 power_per_unit: ExplainableQuantity = None, lifespan: ExplainableQuantity = None,
                 idle_power_per_unit: ExplainableQuantity = None,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(name)
        if nb_of_units is None:
            nb_of_units = SourceValue(1 * u.dimensionless)
        self.carbon_footprint_fabrication_per_unit = carbon_footprint_fabrication_per_unit.set_label(
            f"Carbon footprint fabrication per unit")
        if power_per_unit is not None:
            self.power_per_unit = power_per_unit.set_label(f"Power per unit")
        if lifespan is not None:
            self.lifespan = lifespan.set_label(f"Lifespan")
        if idle_power_per_unit is not None:
            self.idle_power_per_unit = idle_power_per_unit.set_label(f"Idle power per unit")
        self.nb_of_units = nb_of_units.set_label(f"Number of units")



    recurrent_edge_component_needs = ReverseCollection("RecurrentEdgeComponentNeed")
    edge_device = ReverseLink("EdgeDevice")

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([need.edge_usage_patterns for need in self.recurrent_edge_component_needs], start=[])))

    def recurrent_needs_in_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Distinct recurring needs targeting this component along the pattern's actual containment paths."""
        return list(dict.fromkeys(
            path.recurrent_edge_component_need
            for path in usage_pattern.containment_inventory.component_need_paths
            if path.recurrent_edge_component_need.edge_component == self))

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

    @computed_dict(keys="edge_usage_patterns")
    @abstractmethod
    def unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        pass

    @property
    def unitary_power_at_zero_recurrent_need(self) -> ExplainableQuantity:
        """Power one component draws when recurring demand is zero — the idle/base floor of the affine power
        curve, consumed only by the attribution layer (EdgeDevice's atom builder)."""
        raise NotImplementedError

    @property
    def carbon_footprint_fabrication_from_inputs(self) -> ExplainableQuantity:
        """Embodied carbon of the component computed from input attributes only — must mirror
        update_carbon_footprint_fabrication. Read by EdgeDevice to book components with no needs at a deployed
        pattern as part of the chassis: such components never enter the calculated-attribute computation chain,
        so their calculated carbon_footprint_fabrication stays Empty and cannot be read."""
        return (self.carbon_footprint_fabrication_per_unit * self.nb_of_units).set_label(
            f"{self.name} carbon footprint fabrication from inputs")

    @computed_attribute
    def carbon_footprint_fabrication(self):
        """Embodied carbon of one component, equal to the per-unit fabrication footprint times the number of units in the component."""
        return (
            self.carbon_footprint_fabrication_per_unit * self.nb_of_units).set_label(
                f"Carbon footprint fabrication")

    @computed_attribute
    def power(self):
        """Power drawn by one fully-loaded component, equal to per-unit power times the number of units."""
        return (self.power_per_unit * self.nb_of_units).set_label(f"Power")

    @computed_attribute
    def idle_power(self):
        """Power drawn by one idle component, equal to per-unit idle power times the number of units."""
        return (self.idle_power_per_unit * self.nb_of_units).set_label(f"Idle power")

    @computed_dict(keys="edge_usage_patterns")
    def fabrication_footprint_per_edge_device_per_usage_pattern(
            self, usage_pattern: "EdgeUsagePattern"):
        """Hourly fabrication footprint of one component on one device, broken down by usage pattern. Equal to the component's amortised fabrication intensity times the number of concurrent edge journeys."""
        component_fabrication_intensity = self.carbon_footprint_fabrication / self.lifespan
        nb_instances = usage_pattern.nb_deployments_in_parallel

        fabrication_footprint_per_edge_device = (
            nb_instances * component_fabrication_intensity * ExplainableQuantity(1 * u.hour, "one hour"))

        return (
            fabrication_footprint_per_edge_device.to(u.kg).set_label(
                f"Hourly fabrication footprint per edge device for {usage_pattern.name}")
        )

    @computed_dict(keys="edge_usage_patterns")
    def energy_per_edge_device_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly energy consumed by one component on one device, broken down by usage pattern. Equal to the unitary power profile times the number of concurrent edge journeys."""
        nb_instances = usage_pattern.nb_deployments_in_parallel
        unitary_energy = self.unitary_power_per_usage_pattern[usage_pattern] * ExplainableQuantity(1 * u.hour, "one hour")
        energy_per_edge_device = nb_instances * unitary_energy

        return energy_per_edge_device.set_label(
            f"Hourly energy consumed by per edge device for {usage_pattern.name}")

    @computed_dict(keys="edge_usage_patterns")
    def energy_footprint_per_edge_device_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly carbon emissions caused by the component's electricity use, broken down by usage pattern. Equal to energy consumption times the country's grid carbon intensity."""
        energy_footprint = (
            self.energy_per_edge_device_per_usage_pattern[usage_pattern] * usage_pattern.country.average_carbon_intensity
        )

        return energy_footprint.set_label(
            f"Energy footprint per edge device for {usage_pattern.name}").to(u.kg)

    @computed_attribute
    def fabrication_footprint_per_edge_device(self):
        """Total hourly fabrication footprint per edge device, summed across all usage patterns this component appears in."""
        fabrication_footprint_per_edge_device = sum(
            self.fabrication_footprint_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        return fabrication_footprint_per_edge_device.set_label(
            "Total fabrication footprint per edge device across usage patterns")

    @computed_attribute
    def energy_per_edge_device(self):
        """Total hourly energy consumed per edge device, summed across all usage patterns."""
        energy_per_edge_device = sum(
            self.energy_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        return energy_per_edge_device.set_label(
            "Total energy consumed per edge device across usage patterns")

    @computed_attribute
    def energy_footprint_per_edge_device(self):
        """Total hourly energy-use footprint per edge device, summed across all usage patterns."""
        energy_footprint = sum(
            self.energy_footprint_per_edge_device_per_usage_pattern.values(), start=EmptyExplainableObject())
        return energy_footprint.set_label(
            "Total energy footprint per edge device across usage patterns")
