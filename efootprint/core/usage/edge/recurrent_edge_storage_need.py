from typing import TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class RecurrentEdgeStorageNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str, edge_component: EdgeStorage, recurrent_need: ExplainableRecurrentQuantities):
        super().__init__(name, edge_component, recurrent_need)
        self.cumulative_unitary_storage_need_per_usage_pattern = ExplainableObjectDict()

    @property
    def calculated_attributes(self):
        base_attrs = super().calculated_attributes
        total_hourly_need_attr_index = base_attrs.index("total_hourly_need_across_usage_patterns")
        return (
            base_attrs[:total_hourly_need_attr_index]
            + ["cumulative_unitary_storage_need_per_usage_pattern"]
            + base_attrs[total_hourly_need_attr_index:]
        )

    def update_dict_element_in_unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # First compute the base hourly need using parent logic
        super().update_dict_element_in_unitary_hourly_need_per_usage_pattern(usage_pattern)

        # Get the computed value
        base_storage_need = self.unitary_hourly_need_per_usage_pattern[usage_pattern]

        # Apply Monday 00:00 logic
        # if usage_pattern.nb_edge_usage_journey_in_parallel.start_date doesn't start on a Monday 00:00,
        # set the first values of the storage need to 0 until the first Monday 00:00, so that if storage need increases
        # during beginning of the week then decreases at the end of the week, it doesn't go negative
        start_date_weekday = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
            usage_pattern].start_date.weekday()
        start_date_hour = usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
            usage_pattern].start_date.hour
        if start_date_weekday != 0 or start_date_hour != 0:
            hours_until_first_monday_00 = (7 - start_date_weekday) * 24 - start_date_hour
            base_storage_need.magnitude[:hours_until_first_monday_00] = 0

        # Re-set with updated label
        self.unitary_hourly_need_per_usage_pattern[usage_pattern] = base_storage_need.set_label(
            f"{self.name} unitary hourly need for {usage_pattern.name}")

    def update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        storage_rate = self.unitary_hourly_need_per_usage_pattern[usage_pattern]
        if isinstance(storage_rate, EmptyExplainableObject):
            self.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern] = EmptyExplainableObject(
                left_parent=storage_rate, label=f"{self.name} cumulative unitary storage need for {usage_pattern.name}")
            return

        from efootprint.constants.units import u
        rate_in_tb = storage_rate.value.to(u.TB)
        cumulative_quantity = Quantity(np.cumsum(rate_in_tb.magnitude, dtype=np.float32), u.TB_stored)
        self.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern] = ExplainableHourlyQuantities(
            cumulative_quantity,
            start_date=storage_rate.start_date,
            label=f"{self.name} cumulative unitary storage need for {usage_pattern.name}",
            left_parent=storage_rate,
            operator="cumulative sum",
        )

    def update_cumulative_unitary_storage_need_per_usage_pattern(self):
        self.cumulative_unitary_storage_need_per_usage_pattern = ExplainableObjectDict()
        for usage_pattern in self.edge_usage_patterns:
            self.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

    def update_total_hourly_need_across_usage_patterns(self):
        self.total_hourly_need_across_usage_patterns = sum(
            [
                self.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern]
                * usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]
                for usage_pattern in self.edge_usage_patterns
            ],
            start=EmptyExplainableObject(),
        ).set_label(f"{self.name} total hourly need across usage patterns")
