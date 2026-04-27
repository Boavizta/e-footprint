from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class EdgeRAMComponent(EdgeComponent):
    """A RAM bank inside an {class:EdgeDevice}. Represents one or more identical RAM units sized so that aggregated recurrent demand never exceeds available memory."""

    param_descriptions = {
        "carbon_footprint_fabrication_per_unit": (
            "Embodied carbon emitted to manufacture one unit of this RAM bank."),
        "power_per_unit": (
            "Electrical power drawn by one fully-loaded RAM unit."),
        "lifespan": (
            "Expected time before a unit is replaced. Embodied carbon is amortised over this duration."),
        "idle_power_per_unit": (
            "Electrical power drawn by one idle RAM unit."),
        "ram_per_unit": (
            "Memory provided by one unit. Total capacity is this value times {param:EdgeRAMComponent.nb_of_units}."),
        "base_ram_consumption": (
            "RAM permanently occupied independently of recurring needs (operating system, baseline processes)."),
        "nb_of_units": (
            "Number of identical RAM units in the component."),
    }

    compatible_root_units = [u.bit_ram]
    default_values = {
        "carbon_footprint_fabrication_per_unit": SourceValue(20 * u.kg),
        "power_per_unit": SourceValue(10 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power_per_unit": SourceValue(2 * u.W),
        "nb_of_units": SourceValue(1 * u.dimensionless),
        "ram_per_unit": SourceValue(8 * u.GB_ram),
        "base_ram_consumption": SourceValue(1 * u.GB_ram),
    }

    def __init__(self, name: str, carbon_footprint_fabrication_per_unit: ExplainableQuantity,
                 power_per_unit: ExplainableQuantity, lifespan: ExplainableQuantity,
                 idle_power_per_unit: ExplainableQuantity, ram_per_unit: ExplainableQuantity,
                 base_ram_consumption: ExplainableQuantity,
                 nb_of_units: ExplainableQuantity | None = None):
        super().__init__(
            name, carbon_footprint_fabrication_per_unit, power_per_unit, lifespan, idle_power_per_unit,
            nb_of_units=nb_of_units)
        self.ram_per_unit = ram_per_unit.set_label(f"RAM per unit").to(u.GB_ram)
        self.ram = EmptyExplainableObject()
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption")

        self.available_ram_per_instance = EmptyExplainableObject()
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ["ram", "available_ram_per_instance", "unitary_hourly_ram_need_per_usage_pattern"] + super().calculated_attributes

    def update_ram(self):
        """Total memory provided by the RAM component, equal to per-unit RAM times the number of units."""
        self.ram = (self.ram_per_unit * self.nb_of_units).set_label(f"RAM")

    def update_available_ram_per_instance(self):
        """Memory available for recurring needs after subtracting the base consumption. Raises if the component is over-subscribed at design time."""
        available_ram_per_instance = self.ram.to(u.GB_ram) - self.base_ram_consumption.to(u.GB_ram)

        if available_ram_per_instance < SourceValue(0 * u.B_ram):
            raise InsufficientCapacityError(self, "RAM", self.ram.to(u.GB_ram), self.base_ram_consumption)

        self.available_ram_per_instance = available_ram_per_instance.set_label(
            f"Available RAM per {self.name} instance")

    def update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_ram_need = sum(
            [need.unitary_hourly_need_per_usage_pattern[usage_pattern]
             for need in self.recurrent_edge_component_needs if usage_pattern in need.edge_usage_patterns],
            start=EmptyExplainableObject())

        if not isinstance(unitary_hourly_ram_need, EmptyExplainableObject):
            max_ram_need = unitary_hourly_ram_need.max().to(u.GB_ram)
            if max_ram_need > self.available_ram_per_instance:
                raise InsufficientCapacityError(self, "RAM", self.available_ram_per_instance, max_ram_need)

        self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern] = unitary_hourly_ram_need.to(u.GB_ram).set_label(
            f"Hourly RAM need for {usage_pattern.name}").generate_explainable_object_with_logical_dependency(
            self.available_ram_per_instance)

    def update_unitary_hourly_ram_need_per_usage_pattern(self):
        """Hourly RAM demand on one component, broken down by usage pattern. Raises if peak demand exceeds the component's available memory."""
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        if usage_pattern in self.unitary_hourly_ram_need_per_usage_pattern:
            ram_need = self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern]
        else:
            ram_need = EmptyExplainableObject()

        if isinstance(ram_need, EmptyExplainableObject):
            unitary_power = self.idle_power
        else:
            ram_workload = (ram_need + self.base_ram_consumption) / self.ram
            unitary_power = self.idle_power + (self.power - self.idle_power) * ram_workload

        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"Unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        """Hourly power profile of the component for one device, derived from the RAM workload (current need plus base consumption divided by total RAM) by linearly interpolating between idle and full power."""
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)
