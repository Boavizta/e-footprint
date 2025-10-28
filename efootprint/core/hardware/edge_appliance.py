from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_appliance_component import EdgeApplianceComponent

if TYPE_CHECKING:
    from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload


class EdgeAppliance(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):

        # Appliance component gets power and idle_power
        appliance_component = EdgeApplianceComponent(
            name=f"{name} appliance",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=power,
            lifespan=lifespan.copy(),
            idle_power=idle_power)

        super().__init__(
            name=name,
            structure_fabrication_carbon_footprint=carbon_footprint_fabrication,
            components=[appliance_component],
            lifespan=lifespan)

        self.appliance_component = appliance_component

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + [
            "power", "idle_power", "carbon_footprint_fabrication"]

    @property
    def power(self):
        return self.appliance_component.power

    @power.setter
    def power(self, value):
        self.appliance_component.power = value

    @property
    def idle_power(self):
        return self.appliance_component.idle_power

    @idle_power.setter
    def idle_power(self, value):
        self.appliance_component.idle_power = value

    @property
    def carbon_footprint_fabrication(self):
        return self.structure_fabrication_carbon_footprint

    @carbon_footprint_fabrication.setter
    def carbon_footprint_fabrication(self, value):
        self.structure_fabrication_carbon_footprint = value

    @property
    def unitary_hourly_workload_per_usage_pattern(self):
        return self.appliance_component.unitary_hourly_workload_per_usage_pattern

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value)
        # When lifespan is updated after init, propagate copy to component
        if name == "lifespan" and hasattr(self, 'appliance_component'):
            self.appliance_component.lifespan = input_value.copy()