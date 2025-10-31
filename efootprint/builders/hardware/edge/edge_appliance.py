from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent


class EdgeApplianceComponent(EdgeWorkloadComponent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power=SourceValue(0 * u.W))

    @property
    def calculated_attributes(self):
        return ["power", "idle_power", "lifespan"] + super().calculated_attributes

    def update_power(self):
        self.power = self.edge_device.power.copy().set_label(f"Power of {self.name}")

    def update_idle_power(self):
        self.idle_power = self.edge_device.idle_power.copy().set_label(f"Idle power of {self.name}")

    def update_lifespan(self):
        self.lifespan = self.edge_device.lifespan.copy().set_label(f"Lifespan of {self.name}")


class EdgeAppliance(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(100 * u.kg),
        "power": SourceValue(50 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(5 * u.W),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):
        super().__init__(
            name=name,
            structure_carbon_footprint_fabrication=SourceValue(0 * u.kg),
            components=[],
            lifespan=lifespan)
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")

    @property
    def calculated_attributes(self):
        return ["structure_carbon_footprint_fabrication"] + super().calculated_attributes

    def update_structure_carbon_footprint_fabrication(self):
        self.structure_carbon_footprint_fabrication = self.carbon_footprint_fabrication.copy().set_label(
            f"Structure fabrication carbon footprint of {self.name}")

    def after_init(self):
        if not self.components:
            appliance_component = EdgeApplianceComponent(name=f"{self.name} appliance")
            self.components = [appliance_component]
        super().after_init()

    @property
    def appliance_component(self) -> EdgeApplianceComponent:
        return self.components[0]

    @property
    def unitary_hourly_workload_per_usage_pattern(self):
        return self.appliance_component.unitary_hourly_workload_per_usage_pattern
