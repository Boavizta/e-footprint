import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.hardware.edge.edge_component import EdgeComponent


class RecurrentEdgeProcessRAMNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str, edge_component: EdgeComponent):
        from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
        super().__init__(
            name=name,
            edge_component=edge_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB_ram)))

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

    def update_recurrent_need(self):
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_ram_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessCPUNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str, edge_component: EdgeComponent):
        from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
        super().__init__(
            name=name,
            edge_component=edge_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.cpu_core)))

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

    def update_recurrent_need(self):
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_compute_needed.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeProcessStorageNeed(RecurrentEdgeStorageNeed):
    def __init__(self, name: str, edge_component: EdgeComponent):
        from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
        super().__init__(
            name=name,
            edge_component=edge_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.GB)))

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

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

        self._ram_need = None
        self._cpu_need = None
        self._storage_need = None

    def after_init(self):
        ram_need = RecurrentEdgeProcessRAMNeed(
            name=f"{self.name} RAM need",
            edge_component=self.edge_device.ram_component)

        cpu_need = RecurrentEdgeProcessCPUNeed(
            name=f"{self.name} CPU need",
            edge_component=self.edge_device.cpu_component)

        storage_need = RecurrentEdgeProcessStorageNeed(
            name=f"{self.name} storage need",
            edge_component=self.edge_device.storage)

        self._ram_need = ram_need
        self._cpu_need = cpu_need
        self._storage_need = storage_need
        self.recurrent_edge_component_needs = [ram_need, cpu_need, storage_need]
        super().after_init()

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value)
        # When edge_device is updated after init, propagate to component needs
        if self.trigger_modeling_updates:
            if name == "edge_device":
                self._cpu_need.edge_component = input_value.cpu_component
                self._ram_need.edge_component = input_value.ram_component
                self._storage_need.edge_component = input_value.storage

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self._cpu_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self._ram_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_storage_need_per_usage_pattern(self):
        return self._storage_need.unitary_hourly_need_per_usage_pattern
