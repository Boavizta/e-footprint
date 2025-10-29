from copy import copy

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge_storage import EdgeStorage


class EdgeComputerRAMComponent(EdgeRAMComponent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(0 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power=SourceValue(0 * u.W),
            ram=SourceValue(1 * u.GB_ram),
            base_ram_consumption=SourceValue(0 * u.GB_ram))

    @property
    def calculated_attributes(self):
        return ["ram", "base_ram_consumption", "lifespan"] + super().calculated_attributes

    def update_ram(self):
        self.ram = self.edge_device.ram.copy().set_label(f"RAM of {self.name}")

    def update_base_ram_consumption(self):
        self.base_ram_consumption = self.edge_device.base_ram_consumption.copy().set_label(
            f"Base RAM consumption of {self.name}")

    def update_lifespan(self):
        self.lifespan = self.edge_device.lifespan.copy().set_label(f"Lifespan of {self.name}")


class EdgeComputerCPUComponent(EdgeCPUComponent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power=SourceValue(0 * u.W),
            compute=SourceValue(1 * u.cpu_core),
            base_compute_consumption=SourceValue(0 * u.cpu_core))

    @property
    def calculated_attributes(self):
        return ["compute", "base_compute_consumption", "lifespan", "power", "idle_power"] + super().calculated_attributes

    def update_compute(self):
        self.compute = self.edge_device.compute.copy().set_label(f"Compute of {self.name}")

    def update_base_compute_consumption(self):
        self.base_compute_consumption = self.edge_device.base_compute_consumption.copy().set_label(
            f"Base compute consumption of {self.name}")

    def update_lifespan(self):
        self.lifespan = self.edge_device.lifespan.copy().set_label(f"Lifespan of {self.name}")

    def update_power(self):
        self.power = self.edge_device.power.copy().set_label(f"Power of {self.name}")

    def update_idle_power(self):
        self.idle_power = self.edge_device.idle_power.copy().set_label(f"Idle power of {self.name}")


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
            structure_carbon_footprint_fabrication=SourceValue(0 * u.kg),
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

    @property
    def calculated_attributes(self):
        return ["structure_carbon_footprint_fabrication"] + super().calculated_attributes

    def update_structure_carbon_footprint_fabrication(self):
        self.structure_carbon_footprint_fabrication = self.carbon_footprint_fabrication.copy().set_label(
            f"Structure fabrication carbon footprint of {self.name}")

    def after_init(self):
        ram_component = EdgeComputerRAMComponent(name=f"{self.name} RAM")
        cpu_component = EdgeComputerCPUComponent(name=f"{self.name} CPU")

        self.ram_component = ram_component
        self.cpu_component = cpu_component
        self.components = [cpu_component, ram_component, self.storage]
        super().after_init()

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
