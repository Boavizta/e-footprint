from typing import List

from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class Service(ModelingObject):
    def __init__(self, name, server):
        super().__init__(name=name)
        self.name = name
        self.server = server
        self.base_ram_consumption = EmptyExplainableObject()
        self.base_cpu_consumption = EmptyExplainableObject()

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return [self.server]

    @property
    def systems(self) -> List:
        return self.server.systems
