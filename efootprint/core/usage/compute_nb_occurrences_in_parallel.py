import math
from copy import copy

import numpy as np

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.units import u


def compute_nb_avg_hourly_occurrences(
        hourly_occurrences_starts: ExplainableHourlyQuantities, event_duration: ExplainableQuantity):
    if isinstance(hourly_occurrences_starts, EmptyExplainableObject) or event_duration.magnitude == 0:
        return EmptyExplainableObject(left_parent=hourly_occurrences_starts, right_parent=event_duration)

    nb_avg_hourly_occurrences_in_parallel = None
    # Use copy not to convert event_duration in place
    event_duration_in_nb_of_hours = copy(event_duration.value).to(u.hour).magnitude
    nb_of_full_hours_in_event_duration = math.floor(event_duration_in_nb_of_hours)

    for hour_shift in range(0, nb_of_full_hours_in_event_duration):
        if nb_avg_hourly_occurrences_in_parallel is None:
            nb_avg_hourly_occurrences_in_parallel = hourly_occurrences_starts.value.astype(np.float32, copy=False)
        else:
            nb_avg_hourly_occurrences_in_parallel_padded = np.pad(
                nb_avg_hourly_occurrences_in_parallel, (0, 1), constant_values=np.float32(0))
            shifted_values = np.pad(nb_avg_hourly_occurrences_in_parallel, (1, 0), constant_values=np.float32(0))
            nb_avg_hourly_occurrences_in_parallel = nb_avg_hourly_occurrences_in_parallel_padded + shifted_values

    nonfull_duration_rest = event_duration_in_nb_of_hours - nb_of_full_hours_in_event_duration
    if nonfull_duration_rest > 0:
        if nb_avg_hourly_occurrences_in_parallel is None:
            nb_avg_hourly_occurrences_in_parallel = (
                    hourly_occurrences_starts.value.astype(np.float32, copy=False) * nonfull_duration_rest)
        else:
            initial_values_padded = np.pad(
                nb_avg_hourly_occurrences_in_parallel, (0, 1), constant_values=np.float32(0))
            shifted_values = np.pad(
                hourly_occurrences_starts.value.astype(np.float32, copy=False), (nb_of_full_hours_in_event_duration, 0),
                constant_values=np.float32(0))
            nb_avg_hourly_occurrences_in_parallel = initial_values_padded + shifted_values * nonfull_duration_rest

    return ExplainableHourlyQuantities(
        nb_avg_hourly_occurrences_in_parallel, start_date=hourly_occurrences_starts.start_date,
        left_parent=hourly_occurrences_starts, right_parent=event_duration, operator=f"hourly occurrences average")
