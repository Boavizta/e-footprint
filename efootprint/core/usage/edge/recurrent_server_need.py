from typing import List, TYPE_CHECKING

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.usage.job import JobBase
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    

class NegativeServerNeedError(Exception):
    def __init__(self, server_need_name: str, min_value: float):
        message = (
            f"Server need '{server_need_name}' has negative values (min {min_value:.3f}). "
            f"Server need volumes must be positive.")
        super().__init__(message)


class RecurrentServerNeed(ModelingObject):
    default_values = {
        "recurrent_volume_per_edge_device": ExplainableRecurrentQuantities(
            np.array([1.0] * 168, dtype=np.float32) * u.occurrence, label="Default recurrent volume per edge device")
    }

    def __init__(self, name: str, edge_device: EdgeDevice,
                 recurrent_volume_per_edge_device: ExplainableRecurrentQuantities,
                 jobs: List[JobBase]):
        super().__init__(name)
        self.edge_device = edge_device
        self.recurrent_volume_per_edge_device = recurrent_volume_per_edge_device
        self.jobs = jobs
        
        self.validated_recurrent_need = EmptyExplainableObject()
        self.unitary_hourly_volume_per_usage_pattern = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[JobBase]:
        return self.jobs

    @property
    def edge_functions(self) -> List["EdgeFunction"]:
        return self.modeling_obj_containers

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(set(sum([ef.edge_usage_journeys for ef in self.edge_functions], start=[])))

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([euj.edge_usage_patterns for euj in self.edge_usage_journeys], start=[])))

    @property
    def calculated_attributes(self):
        return ["validated_recurrent_need", "unitary_hourly_volume_per_usage_pattern"]

    def update_validated_recurrent_need(self):
        assert self.recurrent_volume_per_edge_device.unit == u.occurrence, \
            (f"RecurrentServerNeed '{self.name}' has invalid unit '{self.recurrent_volume_per_edge_device.unit}', "
             f"expected 'occurrence'.")
        min_value = np.min(self.recurrent_volume_per_edge_device.magnitude)
        if min_value < 0:
            raise NegativeServerNeedError(self.name, min_value)
        self.validated_recurrent_need = self.recurrent_volume_per_edge_device.copy().set_label(
            f"{self.name} validated recurrent need")
        
    def update_dict_element_in_unitary_hourly_volume_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        unitary_hourly_volume = self.recurrent_volume_per_edge_device.generate_hourly_quantities_over_timespan(
            usage_pattern.nb_edge_usage_journeys_in_parallel, usage_pattern.country.timezone)
        self.unitary_hourly_volume_per_usage_pattern[usage_pattern] = unitary_hourly_volume.set_label(
            f"{self.name} unitary hourly need for {usage_pattern.name}")

    def update_unitary_hourly_volume_per_usage_pattern(self):
        self.unitary_hourly_volume_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_volume_per_usage_pattern(usage_pattern)
