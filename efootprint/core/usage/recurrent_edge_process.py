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

        ram_need = RecurrentEdgeComponentNeed(
            name=f"{name} RAM need",
            edge_component=edge_device.ram_component,
            recurrent_need=recurrent_ram_needed)

        cpu_need = RecurrentEdgeComponentNeed(
            name=f"{name} CPU need",
            edge_component=edge_device.cpu_component,
            recurrent_need=recurrent_compute_needed)

        storage_need = RecurrentEdgeComponentNeed(
            name=f"{name} storage need",
            edge_component=edge_device.storage,
            recurrent_need=recurrent_storage_needed)

        super().__init__(
            name=name,
            edge_device=edge_device,
            recurrent_edge_component_needs=[ram_need, cpu_need, storage_need])

        self._ram_need = ram_need
        self._cpu_need = cpu_need
        self._storage_need = storage_need
        self._unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        return ["unitary_hourly_storage_need_per_usage_pattern"]

    @property
    def unitary_hourly_compute_need_per_usage_pattern(self):
        return self._cpu_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_ram_need_per_usage_pattern(self):
        return self._ram_need.unitary_hourly_need_per_usage_pattern

    @property
    def unitary_hourly_storage_need_per_usage_pattern(self):
        return self._unitary_hourly_storage_need_per_usage_pattern

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

        self._unitary_hourly_storage_need_per_usage_pattern[usage_pattern] = base_storage_need.set_label(
            f"{self.name} unitary hourly storage need for {usage_pattern.name}")

    def update_unitary_hourly_storage_need_per_usage_pattern(self):
        self._unitary_hourly_storage_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(usage_pattern)
