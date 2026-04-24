from typing import List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge.edge_storage import EdgeStorage


class EdgeComputerRAMComponent(EdgeRAMComponent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
            power_per_unit=SourceValue(0 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power_per_unit=SourceValue(0 * u.W),
            nb_of_units=SourceValue(1 * u.dimensionless),
            ram_per_unit=SourceValue(1 * u.GB_ram),
            base_ram_consumption=SourceValue(0 * u.GB_ram))

    @property
    def calculated_attributes(self):
        return ["ram_per_unit", "base_ram_consumption", "lifespan"] + super().calculated_attributes

    def update_ram_per_unit(self):
        edge_device = self.edge_device
        if edge_device:
            self.ram_per_unit = self.edge_device.ram.copy().set_label(f"RAM per unit")
        else:
            self.ram_per_unit = EmptyExplainableObject()

    def update_base_ram_consumption(self):
        edge_device = self.edge_device
        if edge_device:
            self.base_ram_consumption = self.edge_device.base_ram_consumption.copy().set_label(
                f"Base RAM consumption")
        else:
            self.base_ram_consumption = EmptyExplainableObject()

    def update_lifespan(self):
        edge_device = self.edge_device
        if edge_device:
            self.lifespan = self.edge_device.lifespan.copy().set_label(f"Lifespan")
        else:
            self.lifespan = EmptyExplainableObject()


class EdgeComputerCPUComponent(EdgeCPUComponent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
            power_per_unit=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            idle_power_per_unit=SourceValue(0 * u.W),
            nb_of_units=SourceValue(1 * u.dimensionless),
            compute_per_unit=SourceValue(1 * u.cpu_core),
            base_compute_consumption=SourceValue(0 * u.cpu_core))

    @property
    def calculated_attributes(self):
        return ["compute_per_unit", "base_compute_consumption", "lifespan", "power_per_unit", "idle_power_per_unit"] + super().calculated_attributes

    def update_compute_per_unit(self):
        edge_device = self.edge_device
        if edge_device:
            self.compute_per_unit = edge_device.compute.copy().set_label(f"Compute per unit")
        else:
            self.compute_per_unit = EmptyExplainableObject()

    def update_base_compute_consumption(self):
        edge_device = self.edge_device
        if edge_device:
            self.base_compute_consumption = self.edge_device.base_compute_consumption.copy().set_label(
                f"Base compute consumption")
        else:
            self.base_compute_consumption = EmptyExplainableObject()

    def update_lifespan(self):
        edge_device = self.edge_device
        if edge_device:
            self.lifespan = self.edge_device.lifespan.copy().set_label(f"Lifespan")
        else:
            self.lifespan = EmptyExplainableObject()

    def update_power_per_unit(self):
        edge_device = self.edge_device
        if edge_device:
            self.power_per_unit = self.edge_device.power.copy().set_label(f"Power per unit")
        else:
            self.power_per_unit = EmptyExplainableObject()


    def update_idle_power_per_unit(self):
        edge_device = self.edge_device
        if edge_device:
            self.idle_power_per_unit = self.edge_device.idle_power.copy().set_label(f"Idle power per unit")
        else:
            self.idle_power_per_unit = EmptyExplainableObject()


class EdgeComputer(EdgeDevice):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(60 * u.kg),
        "power": SourceValue(30 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(5 * u.W),
        "ram": SourceValue(8 * u.GB_ram),
        "compute": SourceValue(4 * u.cpu_core),
        "base_ram_consumption": SourceValue(1 * u.GB_ram),
        "base_compute_consumption": SourceValue(0 * u.cpu_core),
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
            f"Carbon footprint fabrication")
        self.power = power.set_label(f"Power")
        self.idle_power = idle_power.set_label(f"Idle power")
        self.ram = ram.set_label(f"RAM")
        self.compute = compute.set_label(f"Compute")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption")
        self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption")

    @property
    def calculated_attributes(self):
        return ["structure_carbon_footprint_fabrication"] + super().calculated_attributes

    @property
    def attribute_update_entanglements(self):
        return {"storage": self.generate_process_changes_from_storage_change}

    def generate_process_changes_from_storage_change(self, change: List[EdgeStorage]):
        old_storage, new_storage = change[0], change[1]
        component_needs_changes = [
            [edge_process.storage_need.edge_component, new_storage] for edge_process in self.recurrent_needs
        ]
        component_needs_changes.append([
            self.components, [self.cpu_component, self.ram_component, new_storage]
        ])

        return component_needs_changes

    def update_structure_carbon_footprint_fabrication(self):
        self.structure_carbon_footprint_fabrication = self.carbon_footprint_fabrication.copy().set_label(
            f"Structure fabrication carbon footprint")

    def after_init(self):
        if not hasattr(self, "components") or not self.components:
            ram_component = EdgeComputerRAMComponent(name=f"{self.name} RAM")
            cpu_component = EdgeComputerCPUComponent(name=f"{self.name} CPU")

            self.components = [cpu_component, ram_component, self.storage]
        super().after_init()

    @property
    def ram_component(self) -> EdgeComputerRAMComponent:
        return next(comp for comp in self.components if isinstance(comp, EdgeComputerRAMComponent))

    @property
    def cpu_component(self) -> EdgeComputerCPUComponent:
        return next(comp for comp in self.components if isinstance(comp, EdgeComputerCPUComponent))

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

    def self_delete(self):
        ram = self.ram_component
        cpu = self.cpu_component
        super().self_delete()
        for component in [ram, cpu]:
            component.self_delete()
