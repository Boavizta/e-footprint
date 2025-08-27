from typing import List, TYPE_CHECKING, Optional
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_recurring_quantities import ExplainableRecurringQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceRecurringValues
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.hardware.edge_device import EdgeDevice
    from efootprint.core.system import System


class RecurrentEdgeProcess(ModelingObject):
    default_values = {
        "recurrent_compute_needed": SourceRecurringValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
        "recurrent_ram_needed": SourceRecurringValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB)),
        "recurrent_storage_needed": SourceRecurringValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB)),
    }

    def __init__(self, name: str, recurrent_compute_needed: ExplainableRecurringQuantities, 
                 recurrent_ram_needed: ExplainableRecurringQuantities,
                 recurrent_storage_needed: ExplainableRecurringQuantities):
        super().__init__(name)
        self.unitary_hourly_compute_need_over_full_timespan = EmptyExplainableObject()
        self.unitary_hourly_ram_need_over_full_timespan = EmptyExplainableObject()
        self.unitary_hourly_storage_need_over_full_timespan = EmptyExplainableObject()
        
        self.recurrent_compute_needed = recurrent_compute_needed.set_label(f"{self.name} recurrent compute needed")
        self.recurrent_ram_needed = recurrent_ram_needed.set_label(f"{self.name} recurrent ram needed")
        self.recurrent_storage_needed = recurrent_storage_needed.set_label(f"{self.name} recurrent storage needed")

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_compute_need_over_full_timespan", "unitary_hourly_ram_need_over_full_timespan",
                "unitary_hourly_storage_need_over_full_timespan"]

    @property
    def edge_usage_journey(self) -> Optional["EdgeUsageJourney"]:
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"RecurrentEdgeProcess object can only be associated with one EdgeUsageJourney object but {self.name} is "
                    f"associated with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def edge_usage_pattern(self) -> Optional["EdgeUsagePattern"]:
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_usage_pattern
        else:
            return None

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_device
        else:
            return None
        
    @property
    def systems(self) -> List["System"]:
        if self.modeling_obj_containers:
            return self.edge_usage_journey.systems
        return []

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    def update_unitary_hourly_compute_need_over_full_timespan(self):
        if self.edge_usage_pattern is None:
            self.unitary_hourly_compute_need_over_full_timespan = EmptyExplainableObject()
            return
        self.unitary_hourly_compute_need_over_full_timespan = (
            self.recurrent_compute_needed.generate_hourly_quantities_over_timespan(
                self.edge_usage_pattern.hourly_edge_usage_journey_starts, 
                self.edge_usage_pattern.country.timezone))

    def update_unitary_hourly_ram_need_over_full_timespan(self):
        if self.edge_usage_pattern is None:
            self.unitary_hourly_ram_need_over_full_timespan = EmptyExplainableObject()
            return
        self.unitary_hourly_ram_need_over_full_timespan = (
            self.recurrent_ram_needed.generate_hourly_quantities_over_timespan(
                self.edge_usage_pattern.hourly_edge_usage_journey_starts, 
                self.edge_usage_pattern.country.timezone))

    def update_unitary_hourly_storage_need_over_full_timespan(self):
        if self.edge_usage_pattern is None:
            self.unitary_hourly_storage_need_over_full_timespan = EmptyExplainableObject()
            return
        self.unitary_hourly_storage_need_over_full_timespan = (
            self.recurrent_storage_needed.generate_hourly_quantities_over_timespan(
                self.edge_usage_pattern.hourly_edge_usage_journey_starts,
                self.edge_usage_pattern.country.timezone))
