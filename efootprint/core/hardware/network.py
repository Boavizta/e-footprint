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
    """Telecommunications network carrying traffic between users and the servers — Wi-Fi, fixed broadband, cellular. Modelled by its energy intensity per gigabyte transferred."""

    param_descriptions = {
        "bandwidth_energy_intensity": (
            "Electricity consumed per gigabyte transferred end-to-end through the network. Multiplied by the "
            "data transferred by jobs to obtain hourly energy use."),
    }

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
        self.energy_footprint_per_job = ExplainableObjectDict()
        self.energy_footprint = EmptyExplainableObject()
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.bandwidth_energy_intensity = bandwidth_energy_intensity.set_label(
            f"bandwith energy intensity")

    @property
    def calculated_attributes(self):
        return [
            "energy_footprint_per_job",
            "instances_fabrication_footprint",
            "energy_footprint",
        ] + [
            attr for attr in super().calculated_attributes if attr != "usage_impact_repartition_weights"
        ]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def usage_patterns(self) -> List["UsagePattern"] | List["EdgeUsagePattern"]:
        return self.modeling_obj_containers

    @property
    def jobs(self) -> List["JobBase"]:
        return list(dict.fromkeys(sum([up.jobs for up in self.usage_patterns], start=[])))

    def update_instances_fabrication_footprint(self):
        """Network fabrication footprint, currently always empty: e-footprint does not account for the embodied carbon of network infrastructure since it is shared across countless services."""
        self.instances_fabrication_footprint = EmptyExplainableObject()

    def update_dict_element_in_energy_footprint_per_job(self, job: "JobBase"):
        energy_footprint = EmptyExplainableObject()
        for usage_pattern in [up for up in job.usage_patterns if up in self.usage_patterns]:
            energy_footprint += (
                self.bandwidth_energy_intensity
                * job.hourly_data_transferred_per_usage_pattern[usage_pattern]
            ).to(u.kWh) * usage_pattern.country.average_carbon_intensity

        self.energy_footprint_per_job[job] = energy_footprint.to(u.kg).set_label(
            f"{job.name} energy footprint in {self.name}"
        )

    def update_energy_footprint_per_job(self):
        """Hourly carbon emissions caused by network traffic, broken down by job. Equal to data transferred times bandwidth energy intensity times the country's grid carbon intensity."""
        self.energy_footprint_per_job = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_energy_footprint_per_job(job)

    def update_energy_footprint(self):
        """Total hourly carbon emissions caused by network traffic, summed across all jobs that route through this network."""
        self.energy_footprint = sum(self.energy_footprint_per_job.values(), start=EmptyExplainableObject()).set_label(
            f"Hourly {self.name} energy footprint"
        )

    def update_dict_element_in_fabrication_impact_repartition_weights(self, job: "JobBase"):
        raise NotImplementedError(
            f"Fabrication impact repartition is not implemented for {self.name} when Network has a fabrication footprint."
        )

    def update_fabrication_impact_repartition_weights(self):
        """Per-job weights for attributing the network's fabrication footprint, currently empty since {class:Network} carries no fabrication footprint."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        if isinstance(self.instances_fabrication_footprint, EmptyExplainableObject):
            return
        for job in self.jobs:
            self.update_dict_element_in_fabrication_impact_repartition_weights(job)

    @property
    def usage_impact_repartition_weights(self):
        return self.energy_footprint_per_job
