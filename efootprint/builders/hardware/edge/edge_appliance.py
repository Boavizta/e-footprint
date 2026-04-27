from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent


class EdgeApplianceComponent(EdgeWorkloadComponent):
    """Internal {class:EdgeWorkloadComponent} created automatically by an {class:EdgeAppliance}. Mirrors the appliance's power and lifespan so the appliance behaves like a single workload-style component."""

    param_descriptions = {}

    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
            power_per_unit=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power_per_unit=SourceValue(0 * u.W),
            nb_of_units=SourceValue(1 * u.dimensionless))

    @property
    def calculated_attributes(self):
        return ["power_per_unit", "idle_power_per_unit", "lifespan"] + super().calculated_attributes

    def update_power_per_unit(self):
        """Power per unit, copied from the parent {class:EdgeAppliance}'s power."""
        edge_device = self.edge_device
        if edge_device:
            self.power_per_unit = edge_device.power.copy().set_label(f"Power per unit")
        else:
            self.power_per_unit = EmptyExplainableObject()

    def update_idle_power_per_unit(self):
        """Idle power per unit, copied from the parent {class:EdgeAppliance}'s idle power."""
        edge_device = self.edge_device
        if edge_device:
            self.idle_power_per_unit = edge_device.idle_power.copy().set_label(f"Idle power per unit")
        else:
            self.idle_power_per_unit = EmptyExplainableObject()

    def update_lifespan(self):
        """Lifespan, copied from the parent {class:EdgeAppliance}'s lifespan."""
        edge_device = self.edge_device
        if edge_device:
            self.lifespan = edge_device.lifespan.copy().set_label(f"Lifespan")
        else:
            self.lifespan = EmptyExplainableObject()


class EdgeAppliance(EdgeDevice):
    """An appliance-style {class:EdgeDevice} described by a single power and lifespan, without breaking out individual components. Suitable for sealed devices whose internal hardware is not modelled separately."""

    disambiguation = (
        "Use {class:EdgeAppliance} when only an aggregate power and embodied carbon are known, and the load "
        "is described as a 0..1 workload curve. Use {class:EdgeComputer} for computer-like devices with CPU, "
        "RAM, and storage. Use {class:EdgeDevice} for fully bespoke hardware with custom components.")

    param_descriptions = {
        "carbon_footprint_fabrication": (
            "Embodied carbon emitted to manufacture one appliance."),
        "power": (
            "Electrical power drawn at full workload."),
        "lifespan": (
            "Expected time before the appliance is replaced. Embodied carbon is amortised over this duration."),
        "idle_power": (
            "Electrical power drawn at zero workload."),
    }

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
            f"Carbon footprint fabrication")
        self.power = power.set_label(f"Power")
        self.idle_power = idle_power.set_label(f"Idle power")

    @property
    def calculated_attributes(self):
        return ["structure_carbon_footprint_fabrication"] + super().calculated_attributes

    def update_structure_carbon_footprint_fabrication(self):
        """Structure fabrication footprint of the appliance, copied from the appliance's own fabrication footprint since there are no separate component fabrication contributions."""
        self.structure_carbon_footprint_fabrication = self.carbon_footprint_fabrication.copy().set_label(
            f"Structure fabrication carbon footprint")

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

    def self_delete(self):
        components = list(self.components)
        super().self_delete()
        for component in components:
            component.self_delete()
