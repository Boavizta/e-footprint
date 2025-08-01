from typing import List

from efootprint.core.country import Country
from efootprint.constants.units import u
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


class EdgeUsagePattern(ModelingObject):
    def __init__(self, name: str, edge_usage_journey: EdgeUsageJourney, edge_device: EdgeDevice,
                 country: Country, hourly_edge_usage_journey_starts: ExplainableHourlyQuantities):
        super().__init__(name)
        self.utc_hourly_edge_usage_journey_starts = EmptyExplainableObject()
        self.nb_edge_usage_journeys_in_parallel = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        
        self.hourly_edge_usage_journey_starts = hourly_edge_usage_journey_starts.set_label(
            f"{self.name} hourly nb of edge device starts")
        self.edge_usage_journey = edge_usage_journey
        self.edge_device = edge_device
        self.country = country

    @property
    def calculated_attributes(self):
        return ["utc_hourly_edge_usage_journey_starts", "nb_edge_usage_journeys_in_parallel", 
                "energy_footprint", "instances_fabrication_footprint"]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.edge_device]

    @property
    def edge_processes(self) -> List:
        return self.edge_usage_journey.edge_processes

    @property
    def systems(self) -> List:
        return self.modeling_obj_containers

    def update_utc_hourly_edge_usage_journey_starts(self):
        utc_hourly_edge_usage_journey_starts = self.hourly_edge_usage_journey_starts.convert_to_utc(
            local_timezone=self.country.timezone)

        self.utc_hourly_edge_usage_journey_starts = utc_hourly_edge_usage_journey_starts.set_label(
            f"{self.name} UTC")

    def update_nb_edge_usage_journeys_in_parallel(self):
        nb_of_edge_usage_journeys_in_parallel = compute_nb_avg_hourly_occurrences(
            self.utc_hourly_edge_usage_journey_starts, self.edge_usage_journey.duration)

        self.nb_edge_usage_journeys_in_parallel = nb_of_edge_usage_journeys_in_parallel.set_label(
            f"{self.name} hourly nb of edge usage journeys in parallel")

    def update_energy_footprint(self):
        # EdgeUsagePattern energy footprint is the same as the edge device's energy footprint
        self.energy_footprint = self.edge_device.energy_footprint.copy().set_label(
            f"{self.name} total energy footprint")

    def update_instances_fabrication_footprint(self):
        # EdgeUsagePattern fabrication footprint is the same as the edge device's fabrication footprint
        self.instances_fabrication_footprint = self.edge_device.instances_fabrication_footprint.copy().set_label(
            f"{self.name} total fabrication footprint")