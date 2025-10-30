from typing import TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class RecurrentEdgeStorageNeed(RecurrentEdgeComponentNeed):
    def __init__(self, name: str, edge_component: EdgeStorage, recurrent_need: ExplainableRecurrentQuantities):
        super().__init__(name, edge_component, recurrent_need)

    def update_dict_element_in_unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # First compute the base hourly need using parent logic
        super().update_dict_element_in_unitary_hourly_need_per_usage_pattern(usage_pattern)

        # Get the computed value
        base_storage_need = self.unitary_hourly_need_per_usage_pattern[usage_pattern]

        # Apply Monday 00:00 logic
        # if usage_pattern.nb_edge_usage_journey_in_parallel.start_date doesn't start on a Monday 00:00,
        # set the first values of the storage need to 0 until the first Monday 00:00, so that if storage need increases
        # during beginning of the week then decreases at the end of the week, it doesn't go negative
        start_date_weekday = usage_pattern.nb_edge_usage_journeys_in_parallel.start_date.weekday()
        start_date_hour = usage_pattern.nb_edge_usage_journeys_in_parallel.start_date.hour
        if start_date_weekday != 0 or start_date_hour != 0:
            hours_until_first_monday_00 = (7 - start_date_weekday) * 24 - start_date_hour
            base_storage_need.magnitude[:hours_until_first_monday_00] = 0

        # Re-set with updated label
        self.unitary_hourly_need_per_usage_pattern[usage_pattern] = base_storage_need.set_label(
            f"{self.name} unitary hourly need for {usage_pattern.name}")
