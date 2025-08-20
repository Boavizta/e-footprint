from typing import List
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u


class EdgeProcess(ModelingObject):
    default_values = {
        # TODO: create ad hoc object to hold recurrent data structure
        "recurrent_cpu_compute": None,
        "recurrent_ram_compute": None
    }

    def __init__(self, name: str, recurrent_cpu_compute: List[float], recurrent_ram_compute: List[float]):
        super().__init__(name)
        
        # Validate weekly template (168 hours = 7 days * 24 hours)
        if len(recurrent_cpu_compute) != 168:
            raise ValueError(f"recurrent_cpu_compute must have exactly 168 values (one per hour of the week), got {len(recurrent_cpu_compute)}")
        if len(recurrent_ram_compute) != 168:
            raise ValueError(f"recurrent_ram_compute must have exactly 168 values (one per hour of the week), got {len(recurrent_ram_compute)}")
        
        self.recurrent_cpu_compute = recurrent_cpu_compute
        self.recurrent_ram_compute = recurrent_ram_compute
        
        # These will be computed based on the recurrent patterns and usage span
        self.hourly_compute_consumption = EmptyExplainableObject()
        self.hourly_ram_consumption = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return ["hourly_compute_consumption", "hourly_ram_consumption"]

    @property
    def edge_usage_journey(self):
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"EdgeProcess object can only be associated with one EdgeUsageJourney object but {self.name} is associated "
                    f"with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def edge_usage_pattern(self):
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_usage_pattern
        else:
            return None

    @property
    def edge_device(self):
        if self.modeling_obj_containers:
            return self.edge_usage_journey.edge_device
        else:
            return None

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return [self.edge_device]

    def update_hourly_compute_consumption(self):
        # For now, assume a simple weekly pattern repeated over time
        # In a full implementation, this would consider the usage_span from EdgeUsageJourney
        weekly_pattern = np.array(self.recurrent_cpu_compute, dtype=np.float32)
        
        # Create an ExplainableHourlyQuantities object with the weekly pattern
        # This is a simplified implementation - in reality you'd need to handle the full timespan
        compute_quantity = Quantity(weekly_pattern, u.cpu_core)
        
        # For now, use a basic start date - this should be coordinated with the system timeframe
        from datetime import datetime
        start_date = datetime(2023, 1, 2)  # Start on a Monday
        
        self.hourly_compute_consumption = ExplainableHourlyQuantities(
            compute_quantity, start_date, f"{self.name} hourly CPU consumption")

    def update_hourly_ram_consumption(self):
        # Similar to compute consumption
        weekly_pattern = np.array(self.recurrent_ram_compute, dtype=np.float32)
        
        ram_quantity = Quantity(weekly_pattern, u.GB)
        
        from datetime import datetime
        start_date = datetime(2023, 1, 2)  # Start on a Monday
        
        self.hourly_ram_consumption = ExplainableHourlyQuantities(
            ram_quantity, start_date, f"{self.name} hourly RAM consumption")