from typing import List, Optional, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.core.hardware.edge_storage import EdgeStorage
from efootprint.core.hardware.hardware_base import InsufficientCapacityError

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess


class EdgeDevice(EdgeHardware):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(60 * u.kg),
        "power": SourceValue(30 * u.W),
        "lifespan": SourceValue(6 * u.year),
        "idle_power": SourceValue(5 * u.W),
        "ram": SourceValue(8 * u.GB),
        "compute": SourceValue(4 * u.cpu_core),
        "power_usage_effectiveness": SourceValue(1.0 * u.dimensionless),
        "utilization_rate": SourceValue(0.8 * u.dimensionless),
        "base_ram_consumption": SourceValue(1 * u.GB),
        "base_compute_consumption": SourceValue(0.1 * u.cpu_core),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity,
                 utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: EdgeStorage):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)

        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.ram = ram.set_label(f"RAM of {self.name}")
        self.compute = compute.set_label(f"Compute of {self.name}")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE of {self.name}")
        self.utilization_rate = utilization_rate.set_label(f"{self.name} utilization rate")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")
        self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption of {self.name}")
        self.storage = storage

        self.available_compute_per_instance = EmptyExplainableObject()
        self.available_ram_per_instance = EmptyExplainableObject()
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ([
            "available_ram_per_instance", "available_compute_per_instance",
            "unitary_hourly_ram_need_per_usage_pattern", "unitary_hourly_compute_need_per_usage_pattern"]
                + super().calculated_attributes)

    @property
    def edge_usage_journey(self) -> Optional["EdgeUsageJourney"]:
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"EdgeDevice object can only be associated with one EdgeUsageJourney object but {self.name} is "
                    f"associated with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        return None

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_usage_patterns
        return []

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return [self.storage]

    @property
    def edge_processes(self) -> List["RecurrentEdgeProcess"]:
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_processes
        return []

    def update_available_ram_per_instance(self):
        available_ram_per_instance = (self.ram * self.utilization_rate - self.base_ram_consumption)
        
        if available_ram_per_instance.value < 0 * u.B:
            raise InsufficientCapacityError(
                self, "RAM", self.ram * self.utilization_rate, self.base_ram_consumption)

        self.available_ram_per_instance = available_ram_per_instance.set_label(
            f"Available RAM per {self.name} instance")

    def update_available_compute_per_instance(self):
        available_compute_per_instance = (self.compute * self.utilization_rate - self.base_compute_consumption)

        if available_compute_per_instance.value < 0 * u.cpu_core:
            raise InsufficientCapacityError(
                self, "compute", self.compute * self.utilization_rate, self.base_compute_consumption)

        self.available_compute_per_instance = available_compute_per_instance.set_label(
            f"Available compute per {self.name} instance")

    def update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_ram_need = sum(
            [edge_process.unitary_hourly_ram_need_per_usage_pattern[usage_pattern]
             for edge_process in self.edge_processes],
            start=EmptyExplainableObject())

        max_ram_need = unitary_hourly_ram_need.max().to(u.GB)
        if max_ram_need > self.available_ram_per_instance:
            raise InsufficientCapacityError(
                self, "RAM", self.available_ram_per_instance, max_ram_need)

        self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern] = unitary_hourly_ram_need.to(u.GB).set_label(
            f"{self.name} hourly RAM need for {usage_pattern.name}")

    def update_unitary_hourly_ram_need_per_usage_pattern(self):
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_compute_need = sum(
            [edge_process.unitary_hourly_compute_need_per_usage_pattern[usage_pattern]
             for edge_process in self.edge_processes],
            start=EmptyExplainableObject())

        max_compute_need = unitary_hourly_compute_need.max().to(u.cpu_core)
        if max_compute_need > self.available_compute_per_instance:
            raise InsufficientCapacityError(
                self, "compute", self.available_compute_per_instance, max_compute_need)
        
        self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern] = unitary_hourly_compute_need.to(
            u.cpu_core).set_label(f"{self.name} hourly compute need for {usage_pattern.name}")

    def update_unitary_hourly_compute_need_per_usage_pattern(self):
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_power_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_compute_workload = (
                (self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern] + self.base_compute_consumption)
                / self.compute)

        unitary_power = (
                (self.idle_power + (self.power - self.idle_power) * unitary_compute_workload)
                * self.power_usage_effectiveness)

        self.unitary_power_per_usage_pattern[usage_pattern] = unitary_power.set_label(
            f"{self.name} unitary power for {usage_pattern.name}")

    def update_unitary_power_per_usage_pattern(self):
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_power_per_usage_pattern(usage_pattern)
