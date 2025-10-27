from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.hardware.edge_ram_component import EdgeRAMComponent
from efootprint.core.hardware.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.edge_storage import EdgeStorage

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
    from efootprint.core.usage.edge_function import EdgeFunction
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney


class EdgeComputer(EdgeDevice):
    default_values = {
        "structure_fabrication_carbon_footprint": SourceValue(20 * u.kg),
        "cpu_carbon_footprint_fabrication": SourceValue(20 * u.kg),
        "cpu_power": SourceValue(15 * u.W),
        "cpu_idle_power": SourceValue(3 * u.W),
        "ram_carbon_footprint_fabrication": SourceValue(20 * u.kg),
        "ram_power": SourceValue(10 * u.W),
        "ram_idle_power": SourceValue(2 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "ram": SourceValue(8 * u.GB_ram),
        "compute": SourceValue(4 * u.cpu_core),
        "base_ram_consumption": SourceValue(1 * u.GB_ram),
        "base_compute_consumption": SourceValue(0.1 * u.cpu_core),
    }

    def __init__(self, name: str, structure_fabrication_carbon_footprint: ExplainableQuantity,
                 cpu_carbon_footprint_fabrication: ExplainableQuantity, cpu_power: ExplainableQuantity,
                 cpu_idle_power: ExplainableQuantity, ram_carbon_footprint_fabrication: ExplainableQuantity,
                 ram_power: ExplainableQuantity, ram_idle_power: ExplainableQuantity,
                 lifespan: ExplainableQuantity, ram: ExplainableQuantity, compute: ExplainableQuantity,
                 base_ram_consumption: ExplainableQuantity, base_compute_consumption: ExplainableQuantity,
                 storage: EdgeStorage):

        ram_component = EdgeRAMComponent(
            name=f"{name} RAM",
            carbon_footprint_fabrication=ram_carbon_footprint_fabrication,
            power=ram_power,
            lifespan=lifespan,
            idle_power=ram_idle_power,
            ram=ram,
            base_ram_consumption=base_ram_consumption)

        cpu_component = EdgeCPUComponent(
            name=f"{name} CPU",
            carbon_footprint_fabrication=cpu_carbon_footprint_fabrication,
            power=cpu_power,
            lifespan=lifespan,
            idle_power=cpu_idle_power,
            compute=compute,
            base_compute_consumption=base_compute_consumption)

        super().__init__(
            name=name,
            structure_fabrication_carbon_footprint=structure_fabrication_carbon_footprint,
            components=[ram_component, cpu_component, storage],
            lifespan=lifespan)

        self._ram_component = ram_component
        self._cpu_component = cpu_component
        self._storage = storage

    @property
    def ram_component(self) -> EdgeRAMComponent:
        return self._ram_component

    @property
    def cpu_component(self) -> EdgeCPUComponent:
        return self._cpu_component

    @property
    def storage(self) -> EdgeStorage:
        return self._storage

    @property
    def edge_processes(self) -> List["RecurrentEdgeProcess"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ep.edge_usage_journeys for ep in self.edge_processes], start=[])))

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return list(set(sum([ep.edge_functions for ep in self.edge_processes], start=[])))

    @property
    def ram(self):
        return self._ram_component.ram

    @property
    def compute(self):
        return self._cpu_component.compute

    @property
    def base_ram_consumption(self):
        return self._ram_component.base_ram_consumption

    @property
    def base_compute_consumption(self):
        return self._cpu_component.base_compute_consumption

    @property
    def available_ram_per_instance(self):
        return self._ram_component.available_ram_per_instance

    @property
    def available_compute_per_instance(self):
        return self._cpu_component.available_compute_per_instance

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self._ram_component.unitary_hourly_ram_need_per_usage_pattern

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self._cpu_component.unitary_hourly_compute_need_per_usage_pattern
