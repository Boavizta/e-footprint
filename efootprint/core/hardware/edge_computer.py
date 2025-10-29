from copy import copy

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge_storage import EdgeStorage


class EdgeComputer(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(60 * u.kg),
        "power": SourceValue(30 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(5 * u.W),
        "ram": SourceValue(8 * u.GB_ram),
        "compute": SourceValue(4 * u.cpu_core),
        "base_ram_consumption": SourceValue(1 * u.GB_ram),
        "base_compute_consumption": SourceValue(0.1 * u.cpu_core),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 base_ram_consumption: ExplainableQuantity, base_compute_consumption: ExplainableQuantity,
                 storage: EdgeStorage):
        super().__init__(
            name=name,
            structure_carbon_footprint_fabrication=carbon_footprint_fabrication.copy(),
            components=[],
            lifespan=lifespan)
        self.storage = storage
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.ram = ram.set_label(f"RAM of {self.name}")
        self.compute = compute.set_label(f"Compute of {self.name}")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")
        self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption of {self.name}")

        self.ram_component = None
        self.cpu_component = None

    def after_init(self):
        # RAM component has no power
        ram_component = EdgeRAMComponent(
            name=f"{self.name} RAM",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(0 * u.W),
            lifespan=copy(self.lifespan),
            idle_power=SourceValue(0 * u.W),
            ram=copy(self.ram),
            base_ram_consumption=copy(self.base_ram_consumption))

        # CPU component gets all power and idle_power
        cpu_component = EdgeCPUComponent(
            name=f"{self.name} CPU",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=copy(self.power),
            lifespan=copy(self.lifespan),
            idle_power=copy(self.idle_power),
            compute=copy(self.compute),
            base_compute_consumption=copy(self.base_compute_consumption))

        self.ram_component = ram_component
        self.cpu_component = cpu_component
        self.components = [cpu_component, ram_component, self.storage]
        super().after_init()

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value)
        # When lifespan is updated after init, propagate copies to components
        if self.trigger_modeling_updates:
            if name == "lifespan":
                self.ram_component.lifespan = copy(input_value)
                self.cpu_component.lifespan = copy(input_value)
            elif name == "power":
                self.cpu_component.power = copy(input_value)
            elif name == "idle_power":
                self.cpu_component.idle_power = copy(input_value)
            elif name == "ram":
                self.ram_component.ram = copy(input_value)
            elif name == "compute":
                self.cpu_component.compute = copy(input_value)
            elif name == "base_ram_consumption":
                self.ram_component.base_ram_consumption = copy(input_value)
            elif name == "base_compute_consumption":
                self.cpu_component.base_compute_consumption = copy(input_value)
            elif name == "carbon_footprint_fabrication":
                self.structure_carbon_footprint_fabrication = copy(input_value)

    @property
    def available_ram_per_instance(self):
        return self.ram_component.available_ram_per_instance

    @property
    def available_compute_per_instance(self):
        return self.cpu_component.available_compute_per_instance

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self.ram_component.unitary_hourly_ram_need_per_usage_pattern

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self.cpu_component.unitary_hourly_compute_need_per_usage_pattern
