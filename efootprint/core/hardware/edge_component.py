from abc import abstractmethod
from typing import List, TYPE_CHECKING, Optional

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u

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

    @property
    def device_carbon_footprint_fabrication_intensity_share(self) -> ExplainableQuantity:
        """Component's share of device's total carbon footprint fabrication intensity."""
        if not self.edge_device:
            return EmptyExplainableObject()

        component_intensity = (self.carbon_footprint_fabrication / self.lifespan).to(u.kg / u.year)
        device_total_intensity = self.edge_device.total_carbon_footprint_fabrication_intensity

        if device_total_intensity.value == 0:
            return EmptyExplainableObject()

        share = (component_intensity / device_total_intensity).set_label(
            f"{self.name} carbon footprint fabrication intensity share of {self.edge_device.name}")
        return share

    @property
    def device_power_share(self) -> ExplainableQuantity:
        """Component's share of device's total component power."""
        if not self.edge_device:
            return EmptyExplainableObject()

        device_total_power = self.edge_device.total_component_power

        if device_total_power.value == 0:
            return EmptyExplainableObject()

        share = (self.power / device_total_power).set_label(f"{self.name} power share of {self.edge_device.name}")
        return share

    @property
    def instances_fabrication_footprint(self) -> ExplainableQuantity:
        """Component's instances fabrication footprint based on its share of device footprint."""
        if not self.edge_device:
            return EmptyExplainableObject()

        device_footprint = self.edge_device.instances_fabrication_footprint
        share = self.device_carbon_footprint_fabrication_intensity_share

        if isinstance(share, EmptyExplainableObject) or isinstance(device_footprint, EmptyExplainableObject):
            return EmptyExplainableObject()

        component_footprint = (device_footprint * share).set_label(f"{self.name} instances fabrication footprint")
        return component_footprint

    @property
    def instances_energy(self) -> ExplainableQuantity:
        """Component's instances energy based on its share of device energy."""
        if not self.edge_device:
            return EmptyExplainableObject()

        device_energy = self.edge_device.instances_energy
        share = self.device_power_share

        if isinstance(share, EmptyExplainableObject) or isinstance(device_energy, EmptyExplainableObject):
            return EmptyExplainableObject()

        component_energy = (device_energy * share).set_label(f"{self.name} instances energy")
        return component_energy

    @property
    def energy_footprint(self) -> ExplainableQuantity:
        """Component's energy footprint based on its share of device energy footprint."""
        if not self.edge_device:
            return EmptyExplainableObject()

        device_energy_footprint = self.edge_device.energy_footprint
        share = self.device_power_share

        if isinstance(share, EmptyExplainableObject) or isinstance(device_energy_footprint, EmptyExplainableObject):
            return EmptyExplainableObject()

        component_energy_footprint = (device_energy_footprint * share).set_label(f"{self.name} energy footprint")
        return component_energy_footprint

    @abstractmethod
    def expected_need_units(self) -> List:
        """Return list of acceptable pint units for RecurrentEdgeComponentNeed objects linked to this component."""
        pass

    @abstractmethod
    def update_unitary_power_per_usage_pattern(self):
        pass
