from copy import copy
from typing import TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.constants.units import u
from efootprint.core.hardware.edge_computer import EdgeComputer
from efootprint.core.usage.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern


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
        self.unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()

    def after_init(self):
        ram_need = RecurrentEdgeComponentNeed(
            name=f"{self.name} RAM need",
            edge_component=self.edge_device.ram_component,
            recurrent_need=copy(self.recurrent_ram_needed))

        cpu_need = RecurrentEdgeComponentNeed(
            name=f"{self.name} CPU need",
            edge_component=self.edge_device.cpu_component,
            recurrent_need=copy(self.recurrent_compute_needed))

        storage_need = RecurrentEdgeComponentNeed(
            name=f"{self.name} storage need",
            edge_component=self.edge_device.storage,
            recurrent_need=copy(self.recurrent_storage_needed))

        self._ram_need = ram_need
        self._cpu_need = cpu_need
        self._storage_need = storage_need
        self.recurrent_edge_component_needs = [ram_need, cpu_need, storage_need]
        super().after_init()

    def __setattr__(self, name, input_value, check_input_validity=True):
        super().__setattr__(name, input_value)
        # When attributes are updated after init, propagate copies to component needs
        if self.trigger_modeling_updates:
            if name == "recurrent_compute_needed":
                self._cpu_need.recurrent_need = copy(input_value)
            elif name == "recurrent_ram_needed":
                self._ram_need.recurrent_need = copy(input_value)
            elif name == "recurrent_storage_needed":
                self._storage_need.recurrent_need = copy(input_value)

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_storage_need_per_usage_pattern"]

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self._cpu_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self._ram_need.unitary_hourly_need_per_usage_pattern

    def update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # Get the base storage need from the component need
        base_storage_need = self._storage_need.unitary_hourly_need_per_usage_pattern[usage_pattern]

        # Apply Monday 00:00 logic
        # if usage_pattern.nb_edge_usage_journey_in_parallel.start_date doesn't start on a Monday 00:00,
        # set the first values of the storage need to 0 until the first Monday 00:00, so that if storage need increases
        # during beginning of the week then decreases at the end of the week, it doesn't go negative
        start_date_weekday = usage_pattern.nb_edge_usage_journeys_in_parallel.start_date.weekday()
        start_date_hour = usage_pattern.nb_edge_usage_journeys_in_parallel.start_date.hour
        if start_date_weekday != 0 or start_date_hour != 0:
            hours_until_first_monday_00 = (7 - start_date_weekday) * 24 - start_date_hour
            base_storage_need.magnitude[:hours_until_first_monday_00] = 0

        self.unitary_hourly_storage_need_per_usage_pattern[usage_pattern] = base_storage_need.set_label(
            f"{self.name} unitary hourly storage need for {usage_pattern.name}")

    def update_unitary_hourly_storage_need_per_usage_pattern(self):
        self.unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(usage_pattern)
