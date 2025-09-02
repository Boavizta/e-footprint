from typing import List, TYPE_CHECKING, Optional
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.hardware.edge_device import EdgeDevice
    from efootprint.core.system import System


class RecurrentEdgeProcess(ModelingObject):
    default_values = {
        "recurrent_compute_needed": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
        "recurrent_ram_needed": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
        "recurrent_storage_needed": SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB)),
    }

    def __init__(self, name: str, recurrent_compute_needed: ExplainableRecurrentQuantities, 
                 recurrent_ram_needed: ExplainableRecurrentQuantities,
                 recurrent_storage_needed: ExplainableRecurrentQuantities):
        super().__init__(name)
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()
        self.unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()
        
        self.recurrent_compute_needed = recurrent_compute_needed.set_label(f"{self.name} recurrent compute needed")
        self.recurrent_ram_needed = recurrent_ram_needed.set_label(f"{self.name} recurrent ram needed")
        self.recurrent_storage_needed = recurrent_storage_needed.set_label(f"{self.name} recurrent storage needed")

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_compute_need_per_usage_pattern", "unitary_hourly_ram_need_per_usage_pattern",
                "unitary_hourly_storage_need_per_usage_pattern"]

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    @property
    def edge_devices(self) -> List["EdgeDevice"]:
        return [euj.edge_device for euj in self.edge_usage_journeys]
        
    @property
    def systems(self) -> List["System"]:
        return list(set(sum([euj.systems for euj in self.edge_usage_journeys], start=[])))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    def update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_compute_need = self.recurrent_compute_needed.generate_hourly_quantities_over_timespan(
            usage_pattern.hourly_edge_usage_journey_starts, usage_pattern.country.timezone)
        self.unitary_hourly_compute_need_per_usage_pattern[usage_pattern] = unitary_hourly_compute_need.set_label(
            f"{self.name} unitary hourly compute need for {usage_pattern.name}")

    def update_unitary_hourly_compute_need_per_usage_pattern(self):
        self.unitary_hourly_compute_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_ram_need = self.recurrent_ram_needed.generate_hourly_quantities_over_timespan(
            usage_pattern.hourly_edge_usage_journey_starts, usage_pattern.country.timezone)
        self.unitary_hourly_ram_need_per_usage_pattern[usage_pattern] = unitary_hourly_ram_need.set_label(
            f"{self.name} unitary hourly ram need for {usage_pattern.name}")

    def update_unitary_hourly_ram_need_per_usage_pattern(self):
        self.unitary_hourly_ram_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_ram_need_per_usage_pattern(usage_pattern)

    def update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_storage_need = self.recurrent_storage_needed.generate_hourly_quantities_over_timespan(
            usage_pattern.hourly_edge_usage_journey_starts, usage_pattern.country.timezone)
        self.unitary_hourly_storage_need_per_usage_pattern[usage_pattern] = unitary_hourly_storage_need.set_label(
            f"{self.name} unitary hourly storage need for {usage_pattern.name}")

    def update_unitary_hourly_storage_need_per_usage_pattern(self):
        self.unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(usage_pattern)
