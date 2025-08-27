from copy import copy
from typing import List, TYPE_CHECKING, Optional

import numpy as np
from pint import Quantity

from efootprint.constants.sources import Sources
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
    from efootprint.core.hardware.edge_device import EdgeDevice
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


class NegativeCumulativeStorageNeedError(Exception):
    def __init__(self, storage_obj: "EdgeStorage", cumulative_quantity: Quantity):
        self.storage_obj = storage_obj
        self.cumulative_quantity = cumulative_quantity

        message = (
            f"In EdgeStorage object {self.storage_obj.name}, negative cumulative storage need detected: "
            f"{np.min(cumulative_quantity):~P}. Please check your processes "
            f"or increase the base_storage_need value, currently set to {self.storage_obj.base_storage_need.value}")
        super().__init__(message)


class EdgeStorage(EdgeHardware):
    default_values =  {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB),
            "power_per_storage_capacity": SourceValue(1.3 * u.W / u.TB),
            "lifespan": SourceValue(6 * u.years),
            "idle_power": SourceValue(0 * u.W),
            "storage_capacity": SourceValue(1 * u.TB),
            "base_storage_need": SourceValue(0 * u.TB),
        }

    @classmethod
    def ssd(cls, name="Default SSD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "power_per_storage_capacity": SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years),
            "idle_power": SourceValue(0 * u.W),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB),
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "power_per_storage_capacity": SourceValue(4.2 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years),
            "idle_power": SourceValue(0 * u.W),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "base_storage_need": SourceValue(0 * u.TB),
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.ssd, cls.hdd]

    def __init__(self, name: str, storage_capacity: ExplainableQuantity,
                 carbon_footprint_fabrication_per_storage_capacity: ExplainableQuantity,
                 power_per_storage_capacity: ExplainableQuantity, idle_power: ExplainableQuantity,
                 base_storage_need: ExplainableQuantity, lifespan: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W), lifespan=lifespan)
        self.carbon_footprint_fabrication_per_storage_capacity = (carbon_footprint_fabrication_per_storage_capacity
        .set_label(f"Fabrication carbon footprint of {self.name} per storage capacity"))
        self.power_per_storage_capacity = power_per_storage_capacity.set_label(
            f"Power of {self.name} per storage capacity")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity of {self.name}")
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")
        
        self.unitary_storage_delta_over_full_timespan = EmptyExplainableObject()
        self.cumulative_unitary_storage_need_over_single_usage_span = EmptyExplainableObject()
        self.unitary_power_over_full_timespan = EmptyExplainableObject()

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"An EdgeStorage object can only be associated with one EdgeDevice object but {self.name} is "
                    f"associated with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def calculated_attributes(self):
        return [
            "carbon_footprint_fabrication", "power", "unitary_storage_delta_over_full_timespan",
            "cumulative_unitary_storage_need_over_single_usage_span",
            "unitary_power_over_full_timespan", "nb_of_instances", "instances_energy",
            "energy_footprint", "instances_fabrication_footprint"]

    @property
    def edge_processes(self) -> List["RecurrentEdgeProcess"]:
        edge_device = self.edge_device
        if edge_device is not None:
            return edge_device.edge_processes
        return []
    
    @property
    def edge_usage_pattern(self) -> Optional["EdgeUsagePattern"]:
        edge_device = self.edge_device
        if edge_device is not None:
            return edge_device.edge_usage_pattern
        return None

    @property
    def power_usage_effectiveness(self):
        if self.edge_device is not None:
            return self.edge_device.power_usage_effectiveness
        else:
            return EmptyExplainableObject()

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = (
                self.carbon_footprint_fabrication_per_storage_capacity * self.storage_capacity).set_label(
            f"Carbon footprint of {self.name}")

    def update_power(self):
        self.power = (self.power_per_storage_capacity * self.storage_capacity).set_label(f"Power of {self.name}")

    def update_unitary_storage_delta_over_full_timespan(self):
        unitary_storage_delta_over_full_timespan = EmptyExplainableObject()
        
        for edge_process in self.edge_processes:
            unitary_storage_delta_over_full_timespan += edge_process.unitary_hourly_storage_need_over_full_timespan
        
        self.unitary_storage_delta_over_full_timespan = unitary_storage_delta_over_full_timespan.set_label(
            f"Hourly unitary storage delta for {self.name}")

    def update_cumulative_unitary_storage_need_over_single_usage_span(self):
        if isinstance(self.unitary_storage_delta_over_full_timespan, EmptyExplainableObject):
            self.cumulative_unitary_storage_need_over_single_usage_span = EmptyExplainableObject(
                left_parent=self.unitary_storage_delta_over_full_timespan)
        else:
            edge_device_usage_span_in_hours = int(copy(
                self.edge_device.edge_usage_journey.usage_span.value).to(u.hour).magnitude)
            unitary_storage_delta_over_single_usage_span = ExplainableHourlyQuantities(
                Quantity(
                    self.unitary_storage_delta_over_full_timespan.magnitude[:edge_device_usage_span_in_hours],
                    self.unitary_storage_delta_over_full_timespan.unit
                ),
                start_date=self.unitary_storage_delta_over_full_timespan.start_date,
                left_parent=self.unitary_storage_delta_over_full_timespan,
                right_parent=self.edge_device.edge_usage_journey.usage_span,
                operator="truncated by"
            )
            delta_array = np.copy(unitary_storage_delta_over_single_usage_span.value.magnitude)
            delta_unit = unitary_storage_delta_over_single_usage_span.value.units

            # Add base storage need to first hour
            delta_array[0] += self.base_storage_need.value.to(delta_unit).magnitude

            # Compute cumulative storage
            cumulative_array = np.cumsum(delta_array, dtype=np.float32)
            cumulative_quantity = Quantity(cumulative_array, delta_unit)

            if np.min(cumulative_quantity.magnitude) < 0:
                raise NegativeCumulativeStorageNeedError(self, cumulative_quantity)
            
            if np.max(cumulative_quantity) > self.storage_capacity.value:
                raise InsufficientCapacityError(
                    self, "storage capacity", self.storage_capacity, 
                    ExplainableQuantity(cumulative_quantity.max(), label=f"{self.name} unitary cumulative storage need"))
            
            self.cumulative_unitary_storage_need_over_single_usage_span = ExplainableHourlyQuantities(
                cumulative_quantity,
                start_date=unitary_storage_delta_over_single_usage_span.start_date,
                label=f"Full cumulative storage need for {self.name}",
                left_parent=unitary_storage_delta_over_single_usage_span,
                right_parent=self.base_storage_need,
                operator="cumulative sum of storage delta with initial storage need"
            )

    def update_unitary_power_over_full_timespan(self):
        unitary_activity_level = (
                self.unitary_storage_delta_over_full_timespan.abs() / self.storage_capacity).to(u.dimensionless)

        unitary_power_over_full_timespan = (
                (self.idle_power + (self.power - self.idle_power) * unitary_activity_level)
                * self.power_usage_effectiveness)
        
        self.unitary_power_over_full_timespan = unitary_power_over_full_timespan.set_label(
            f"Hourly number of active instances for {self.name}")
