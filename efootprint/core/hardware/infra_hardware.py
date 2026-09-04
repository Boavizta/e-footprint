from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.hardware_base import HardwareBase
from efootprint.abstract_modeling_classes.reactive_core import ComputationPurpose, computed_attribute


class InfraHardware(HardwareBase):
    param_descriptions = {
        k: v for k, v in HardwareBase.param_descriptions.items() if k != "fraction_of_usage_time"
    }

    def __init__(self, name: str, carbon_footprint_manufacturing: ExplainableQuantity = None,
                 power: ExplainableQuantity = None, lifespan: ExplainableQuantity = None):
        super().__init__(
            name, carbon_footprint_manufacturing, power, lifespan, SourceValue(1 * u.dimensionless))


    @computed_attribute
    @abstractmethod
    def raw_nb_of_instances(self):
        pass

    @computed_attribute
    @abstractmethod
    def nb_of_instances(self):
        pass

    @computed_attribute
    @abstractmethod
    def instances_energy(self):
        pass

    @property
    def systems(self) -> List:
        return list(dict.fromkeys(sum([job.systems for job in self.jobs], start=[])))

    @computed_attribute(serialize=True, purposes={ComputationPurpose.FOOTPRINT})
    def instances_manufacturing_footprint(self):
        """Hourly manufacturing-phase emissions of all instances, equal to the embodied carbon of one instance amortised over its lifespan and multiplied by the number of instances active in each hour."""
        instances_manufacturing_footprint = (
                self.carbon_footprint_manufacturing * self.nb_of_instances * ExplainableQuantity(1 * u.hour, "one hour")
                / self.lifespan)

        return instances_manufacturing_footprint.to(u.kg).set_label(
                f"Hourly instances manufacturing footprint")

    @computed_attribute(serialize=True, purposes={ComputationPurpose.FOOTPRINT})
    def use_footprint(self):
        """Hourly carbon emissions caused by the electricity consumed by this hardware, equal to its hourly energy use times the local grid carbon intensity."""
        use_footprint = (self.instances_energy * self.average_carbon_intensity)

        return use_footprint.to(u.kg).set_label(f"Hourly use footprint")
