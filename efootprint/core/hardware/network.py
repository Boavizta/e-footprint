from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.sources import Sources
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.job import JobBase


class Network(ModelingObject):
    default_values = {
            "bandwidth_energy_intensity": SourceValue(0.1 * u.kWh / u.GB)
        }

    @classmethod
    def wifi_network(cls, name: str = "Default wifi network"):
        return cls(
            name=name, bandwidth_energy_intensity=SourceValue(0.05 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

    @classmethod
    def mobile_network(cls, name: str = "Default mobile network"):
        return cls(
            name=name, bandwidth_energy_intensity=SourceValue(0.12 * u("kWh/GB"), Sources.TRAFICOM_STUDY))

    @classmethod
    def archetypes(cls):
        return [cls.wifi_network, cls.mobile_network]

    def __init__(self, name: str, bandwidth_energy_intensity: ExplainableQuantity):
        super().__init__(name)
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.bandwidth_energy_intensity = bandwidth_energy_intensity.set_label(
            f"bandwith energy intensity of {self.name}")

    @property
    def calculated_attributes(self):
        return ["instances_fabrication_footprint", "energy_footprint"] + super().calculated_attributes

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def usage_patterns(self) -> List["UsagePattern"] | List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def jobs(self) -> List["JobBase"]:
        return list(set(sum([up.jobs for up in self.usage_patterns], start=[])))

    def update_energy_footprint(self):
        hourly_data_transferred_per_up = {up: EmptyExplainableObject() for up in self.usage_patterns}
        for job in self.jobs:
            job_ups_in_network_ups = [up for up in job.usage_patterns if up in self.usage_patterns]
            for up in job_ups_in_network_ups:
                hourly_data_transferred_per_up[up] += job.hourly_data_transferred_per_usage_pattern[up]

        energy_footprint = EmptyExplainableObject()
        for up in self.usage_patterns:
            up_network_consumption = (
                        self.bandwidth_energy_intensity * hourly_data_transferred_per_up[up]).to(u.kWh).set_label(
                f"{up.name} network energy consumption")

            energy_footprint += up_network_consumption * up.country.average_carbon_intensity

        self.energy_footprint = energy_footprint.to(u.kg).set_label(f"Hourly {self.name} energy footprint")

    def update_dict_element_in_impact_repartition_weights(self, job: "JobBase"):
        weight = job.data_transferred * job.hourly_avg_occurrences_across_usage_patterns

        self.impact_repartition_weights[job] = weight.to(u.concurrent).set_label(
            f"{job.name} weight in {self.name} impact repartition")

    def update_impact_repartition_weights(self):
        self.impact_repartition_weights = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_impact_repartition_weights(job)

    def update_instances_fabrication_footprint(self):
        self.instances_fabrication_footprint = EmptyExplainableObject()
