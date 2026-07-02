from typing import TYPE_CHECKING

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute, computed_dict

if TYPE_CHECKING:
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


class RecurrentEdgeStorageNeed(RecurrentEdgeComponentNeed):
    """A {class:RecurrentEdgeComponentNeed} targeting an {class:EdgeStorage} component. Tracks the cumulative storage consumed by writes and freed by negative values across the typical week."""

    pitfalls = (
        "Values represent net storage rate (positive = writes, negative = deletes). The cumulative integral "
        "must stay non-negative within each week, otherwise the cumulative storage need would go below zero "
        "and break downstream sizing.")

    param_descriptions = {
        "edge_component": (
            "{class:EdgeStorage} component holding the data."),
        "recurrent_need": (
            "Hourly net storage rate over a typical week (positive for writes, negative for deletes). Cumulated "
            "to derive the cumulative volume actually held."),
    }

    def __init__(self, name: str, edge_component: EdgeStorage, recurrent_need: ExplainableRecurrentQuantities):
        super().__init__(name, edge_component, recurrent_need)


    @computed_dict(keys="edge_usage_patterns")
    def unitary_hourly_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        # First compute the base hourly need using parent logic
        base_storage_need = RecurrentEdgeComponentNeed.unitary_hourly_need_per_usage_pattern(self, usage_pattern)

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

        return base_storage_need.set_label(
            f"Unitary hourly need for {usage_pattern.name}")

    @computed_dict(keys="edge_usage_patterns")
    def cumulative_unitary_storage_need_per_usage_pattern(self, usage_pattern: "EdgeUsagePattern"):
        """Hourly cumulative storage held by one edge device, integrating the net storage rate from the start of the modeling period."""
        storage_rate = self.unitary_hourly_need_per_usage_pattern[usage_pattern]
        if isinstance(storage_rate, EmptyExplainableObject):
            return EmptyExplainableObject(
                left_parent=storage_rate, label=f"Cumulative unitary storage need for {usage_pattern.name}")

        from efootprint.constants.units import u
        rate_in_tb = storage_rate.value.to(u.TB_stored)
        cumulative_quantity = Quantity(np.cumsum(rate_in_tb.magnitude, dtype=np.float32), u.TB_stored)
        return ExplainableHourlyQuantities(
            cumulative_quantity,
            start_date=storage_rate.start_date,
            label=f"Cumulative unitary storage need for {usage_pattern.name}",
            left_parent=storage_rate,
            operator="cumulative sum",
        )

    @computed_attribute
    def total_hourly_need_across_usage_patterns(self):
        """Total hourly storage volume held across the deployed fleet, summing per-device cumulative storage weighted by the hourly count of edge devices in deployment."""
        return sum(
            [
                self.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern]
                * usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]
                for usage_pattern in self.edge_usage_patterns
            ],
            start=EmptyExplainableObject(),
        ).set_label("Total hourly need across usage patterns")
