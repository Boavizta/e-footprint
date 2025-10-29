from copy import copy

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_appliance_component import EdgeApplianceComponent


class EdgeAppliance(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(5 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):
        super().__init__(
            name=name,
            structure_carbon_footprint_fabrication=carbon_footprint_fabrication.copy(),
            components=[],
            lifespan=lifespan)
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")

        self.appliance_component = None

    def after_init(self):
        # Appliance component gets power and idle_power
        appliance_component = EdgeApplianceComponent(
            name=f"{self.name} appliance",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=copy(self.power),
            lifespan=copy(self.lifespan),
            idle_power=copy(self.idle_power))

        self.appliance_component = appliance_component
        self.components = [appliance_component]
        super().after_init()

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value)
        # When attributes are updated after init, propagate copies to component
        if self.trigger_modeling_updates:
            if name == "lifespan":
                self.appliance_component.lifespan = copy(input_value)
            elif name == "power":
                self.appliance_component.power = copy(input_value)
            elif name == "idle_power":
                self.appliance_component.idle_power = copy(input_value)
            elif name == "carbon_footprint_fabrication":
                self.structure_carbon_footprint_fabrication = copy(input_value)

    @property
    def unitary_hourly_workload_per_usage_pattern(self):
        return self.appliance_component.unitary_hourly_workload_per_usage_pattern