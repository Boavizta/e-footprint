import numpy as np

from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.constants.units import u


def compute_nb_avg_hourly_occurrences(hourly_occurrences_starts, event_duration):
    """
    Compute the average number of hourly occurrences running in parallel
    for events of a given duration.

    Summing the occurrences still running at each hour is a convolution with a "boxcar"
    (a vector of ones of length = event duration in hours), which is a sliding-window sum:
    it is computed as the difference of two shifted cumulative sums.

    Parameters
    ----------
    hourly_occurrences_starts : ExplainableHourlyQuantities
        The base hourly occurrence pattern (numpy array under `.value`).
    event_duration : ExplainableQuantity
        The duration of one event, converted internally to hours.

    Returns
    -------
    ExplainableHourlyQuantities
        The summed pattern of overlapping events.
    """
    if isinstance(hourly_occurrences_starts, EmptyExplainableObject) or event_duration.magnitude == 0:
        return EmptyExplainableObject(left_parent=hourly_occurrences_starts, right_parent=event_duration)

    event_duration_in_hours = event_duration.value.to(u.hour).magnitude
    nb_full_hours = int(np.floor(event_duration_in_hours))

    values = hourly_occurrences_starts.value.magnitude.astype(np.float32, copy=False)

    if nb_full_hours > 0:
        # Sum in float64 so that the difference of cumulative sums stays exact at float32 precision.
        cumulative_sum = np.cumsum(values, dtype=np.float64)
        window_end_sums = np.concatenate((cumulative_sum, np.full(nb_full_hours - 1, cumulative_sum[-1])))
        window_start_sums = np.concatenate((np.zeros(nb_full_hours), cumulative_sum[:-1]))
        result = (window_end_sums - window_start_sums).astype(np.float32)
    else:
        result = None

    nonfull_duration_rest = event_duration_in_hours - nb_full_hours
    if nonfull_duration_rest > 0:
        rest_f32 = np.float32(nonfull_duration_rest)
        if result is None:
            result = values * rest_f32
        else:
            initial_values_padded = np.pad(result, (0, 1), constant_values=np.float32(0))
            shifted_values = np.pad(values, (nb_full_hours, 0), constant_values=np.float32(0))
            result = initial_values_padded + shifted_values * rest_f32

    # Avoid negative values that could lead to NegativeCumulativeStorageNeedError.
    np.maximum(result, 0, out=result)

    return ExplainableHourlyQuantities(
        Quantity(result, u.concurrent),
        start_date=hourly_occurrences_starts.start_date,
        left_parent=hourly_occurrences_starts,
        right_parent=event_duration,
        operator="hourly occurrences average"
    )
