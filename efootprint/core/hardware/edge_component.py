from abc import abstractmethod
from typing import List, TYPE_CHECKING, Optional

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

if TYPE_CHECKING:
    from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.hardware.edge_device import EdgeDevice


class EdgeComponent(ModelingObject):
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity, power: ExplainableQuantity,
                 lifespan: ExplainableQuantity, idle_power: ExplainableQuantity):
        super().__init__(name)
        self.carbon_footprint_fabrication = carbon_footprint_fabrication.set_label(
            f"Carbon footprint fabrication of {self.name}")
        self.power = power.set_label(f"Power of {self.name}")
        self.lifespan = lifespan.set_label(f"Lifespan of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.unitary_power_per_usage_pattern = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List["EdgeDevice"]:
        if self.edge_device:
            return [self.edge_device]
        return []

    @property
    def calculated_attributes(self):
        return ["unitary_power_per_usage_pattern"]

    @property
    def recurrent_edge_component_needs(self) -> List["RecurrentEdgeComponentNeed"]:
        from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed
        return [container for container in self.modeling_obj_containers
                if isinstance(container, RecurrentEdgeComponentNeed)]

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        if not self.recurrent_edge_component_needs:
            return None

        return self.recurrent_edge_component_needs[0].edge_device

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(set(sum([need.edge_usage_patterns for need in self.recurrent_edge_component_needs], start=[])))

    @abstractmethod
    def expected_need_units(self) -> List:
        """Return list of acceptable pint units for RecurrentEdgeComponentNeed objects linked to this component."""
        pass

    @abstractmethod
    def update_unitary_power_per_usage_pattern(self):
        pass
