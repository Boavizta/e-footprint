from abc import abstractmethod
from typing import List

import numpy as np
from pint import Quantity

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
    def __init__(self, name: str, edge_component: EdgeComponent):
        super().__init__(
            name=name,
            edge_component=edge_component,
            recurrent_need=EmptyExplainableObject()
        )

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

    @abstractmethod
    def update_recurrent_need(self):
        pass


class RecurrentEdgeProcessRAMNeed(RecurrentEdgeProcessNeed):
    def update_recurrent_need(self):
        if not self.recurrent_edge_device_needs:
            self.recurrent_need = SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB_ram))
            return
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_ram_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessCPUNeed(RecurrentEdgeProcessNeed):
    def update_recurrent_need(self):
        if not self.recurrent_edge_device_needs:
            self.recurrent_need = SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.cpu_core))
            return
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_compute_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessStorageNeed(RecurrentEdgeProcessNeed, RecurrentEdgeStorageNeed):
    def update_recurrent_need(self):
        if not self.recurrent_edge_device_needs:
            self.recurrent_need = SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB))
            return
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

    def after_init(self):
        if not self.recurrent_edge_component_needs:
            ram_need = RecurrentEdgeProcessRAMNeed(
                name=f"{self.name} RAM need", edge_component=self.edge_device.ram_component)
            compute_need = RecurrentEdgeProcessCPUNeed(
                name=f"{self.name} CPU need", edge_component=self.edge_device.cpu_component)
            storage_need = RecurrentEdgeProcessStorageNeed(
                name=f"{self.name} storage need", edge_component=self.edge_device.storage)

            self.recurrent_edge_component_needs = [ram_need, compute_need, storage_need]
        super().after_init()

    @property
    def ram_need(self) -> RecurrentEdgeProcessRAMNeed:
        return next(need for need in self.recurrent_edge_component_needs
                    if isinstance(need, RecurrentEdgeProcessRAMNeed))

    @property
    def compute_need(self) -> RecurrentEdgeProcessCPUNeed:
        return next(need for need in self.recurrent_edge_component_needs
                    if isinstance(need, RecurrentEdgeProcessCPUNeed))

    @property
    def storage_need(self) -> RecurrentEdgeProcessStorageNeed:
        return next(need for need in self.recurrent_edge_component_needs
                    if isinstance(need, RecurrentEdgeProcessStorageNeed))

    @property
    def attribute_update_entanglements(self):
        return {"edge_device": self.generate_component_needs_changes_from_device_change}

    def generate_component_needs_changes_from_device_change(self, change: List[EdgeComputer]):
        old_edge_computer, new_edge_computer = change[0], change[1]
        component_needs_changes = [
            [self.ram_need.edge_component, new_edge_computer.ram_component],
            [self.compute_need.edge_component, new_edge_computer.cpu_component],
            [self.storage_need.edge_component, new_edge_computer.storage],
        ]
        return component_needs_changes

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self.compute_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self.ram_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_storage_need_per_usage_pattern(self):
        return self.storage_need.unitary_hourly_need_per_usage_pattern
