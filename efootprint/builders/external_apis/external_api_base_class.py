from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ExternalAPI(ModelingObject):
    def __init__(self, name: str):
        super().__init__(name=name)
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return ["instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    @abstractmethod
    def update_instances_fabrication_footprint(self) -> None:
        pass

    @abstractmethod
    def update_instances_energy(self) -> None:
        pass

    @abstractmethod
    def update_energy_footprint(self) -> None:
        pass
