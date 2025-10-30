from abc import abstractmethod
from copy import copy
from typing import Optional

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.hardware.edge.edge_component import EdgeComponent


class RecurrentEdgeProcessNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            edge_component=None,
            recurrent_need=EmptyExplainableObject()
        )

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

    @property
    def edge_process(self) -> "RecurrentEdgeProcess":
        if self.modeling_obj_containers:
            return self.modeling_obj_containers[0]
        return None

    @property
    def edge_device(self) -> Optional["EdgeDevice"]:
        if self.edge_process:
            return self.edge_process.edge_device
        return None

    @property
    @abstractmethod
    def edge_component(self) -> EdgeComponent:
        pass

    @abstractmethod
    def update_recurrent_need(self):
        pass


class RecurrentEdgeProcessRAMNeed(RecurrentEdgeProcessNeed):
    @property
    def edge_component(self) -> EdgeComponent:
        contextual_component = ContextualModelingObjectAttribute(self.edge_device.ram_component)
        contextual_component.set_modeling_obj_container(self, "edge_component")
        return contextual_component

    @edge_component.setter
    def edge_component(self, value: EdgeComponent):
        pass

    def update_recurrent_need(self):
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_ram_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessCPUNeed(RecurrentEdgeProcessNeed):
    @property
    def edge_component(self) -> EdgeComponent:
        contextual_component = ContextualModelingObjectAttribute(self.edge_device.cpu_component)
        contextual_component.set_modeling_obj_container(self, "edge_component")
        return contextual_component

    @edge_component.setter
    def edge_component(self, value: EdgeComponent):
        pass

    def update_recurrent_need(self):
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_compute_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessStorageNeed(RecurrentEdgeProcessNeed, RecurrentEdgeStorageNeed):
    @property
    def edge_component(self) -> EdgeComponent:
        contextual_component = ContextualModelingObjectAttribute(self.edge_device.storage)
        contextual_component.set_modeling_obj_container(self, "edge_component")
        return contextual_component

    @edge_component.setter
    def edge_component(self, value: EdgeComponent):
        pass

    def update_recurrent_need(self):
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_storage_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcess(RecurrentEdgeDeviceNeed):
    default_values = {
        "recurrent_compute_needed": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.cpu_core)),
        "recurrent_ram_needed": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.GB_ram)),
        "recurrent_storage_needed": SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB)),
    }

    def __init__(self, name: str, edge_device: EdgeComputer,
                 recurrent_compute_needed: ExplainableRecurrentQuantities,
                 recurrent_ram_needed: ExplainableRecurrentQuantities,
                 recurrent_storage_needed: ExplainableRecurrentQuantities):
        super().__init__(
            name=name,
            edge_device=edge_device,
            recurrent_edge_component_needs=[])
        self.recurrent_compute_needed = recurrent_compute_needed.set_label(
            f"Recurrent compute needed for {self.name}")
        self.recurrent_ram_needed = recurrent_ram_needed.set_label(
            f"Recurrent RAM needed for {self.name}")
        self.recurrent_storage_needed = recurrent_storage_needed.set_label(
            f"Recurrent storage needed for {self.name}")

        self.ram_need = None
        self.cpu_need = None
        self.storage_need = None

    def after_init(self):
        if self.ram_need is None:
            ram_need = RecurrentEdgeProcessRAMNeed(name=f"{self.name} RAM need")
            cpu_need = RecurrentEdgeProcessCPUNeed(name=f"{self.name} CPU need")
            storage_need = RecurrentEdgeProcessStorageNeed(name=f"{self.name} storage need")

            self.ram_need = ram_need
            self.cpu_need = cpu_need
            self.storage_need = storage_need
            self.recurrent_edge_component_needs = [ram_need, cpu_need, storage_need]
        super().after_init()

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self.cpu_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self.ram_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_storage_need_per_usage_pattern(self):
        return self.storage_need.unitary_hourly_need_per_usage_pattern

    def self_delete(self):
        old_needs = copy(self.recurrent_edge_component_needs)
        self.recurrent_edge_component_needs = []
        self.ram_need.set_modeling_obj_container(None, None)
        self.cpu_need.set_modeling_obj_container(None, None)
        self.storage_need.set_modeling_obj_container(None, None)
        del self.ram_need
        del self.cpu_need
        del self.storage_need
        for need in old_needs:
            need.self_delete()
        super().self_delete()
