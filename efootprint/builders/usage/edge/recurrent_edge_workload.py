from typing import List

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.builders.hardware.edge.edge_appliance import EdgeAppliance
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed


class RecurrentEdgeWorkloadNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str, edge_component: EdgeComponent):
        from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
        super().__init__(
            name=name,
            edge_component=edge_component,
            recurrent_need=SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.concurrent)))

    @property
    def calculated_attributes(self):
        return ["recurrent_need"] + super().calculated_attributes

    def update_recurrent_need(self):
        if not self.recurrent_edge_device_needs:
            self.recurrent_need = SourceRecurrentValues(Quantity(np.array([0] * 168, dtype=np.float32), u.concurrent))
            return
        recurrent_edge_device_need = self.recurrent_edge_device_needs[0]
        self.recurrent_need = recurrent_edge_device_need.recurrent_workload.copy().set_label(
            f"{self.name} recurrent need")


class RecurrentEdgeWorkload(RecurrentEdgeDeviceNeed):
    default_values = {
        "recurrent_workload": SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.concurrent)),
    }

    def __init__(self, name: str, edge_device: EdgeAppliance, recurrent_workload: ExplainableRecurrentQuantities):
        super().__init__(
            name=name,
            edge_device=edge_device,
            recurrent_edge_component_needs=[])
        self.recurrent_workload = recurrent_workload.set_label(f"Recurrent workload for {self.name}")

    def after_init(self):
        if not self.recurrent_edge_component_needs:
            workload_need = RecurrentEdgeWorkloadNeed(
                name=f"{self.name} workload need",
                edge_component=self.edge_device.appliance_component)
            self.recurrent_edge_component_needs = [workload_need]
        super().after_init()

    @property
    def workload_need(self) -> RecurrentEdgeWorkloadNeed:
        return self.recurrent_edge_component_needs[0]

    @property
    def attribute_update_entanglements(self):
        return {
            "edge_device": self.generate_component_needs_changes_from_device_change,
        }

    def generate_component_needs_changes_from_device_change(self, change: List[EdgeAppliance]):
        old_edge_appliance, new_edge_appliance = change[0], change[1]
        component_needs_changes = [
            [self.workload_need.edge_component, new_edge_appliance.appliance_component],
        ]
        return component_needs_changes

    @property
    def unitary_hourly_workload_per_usage_pattern(self):
        return self.workload_need.unitary_hourly_need_per_usage_pattern
