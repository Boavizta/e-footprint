import unittest

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u


class TestUsagePattern(unittest.TestCase):
    def test_compute_nb_occurrences_in_parallel_entire_hour(self):
        input_occs_starts = [20, 10, 14, 15]
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts)
        event_duration = SourceValue(1 * u.hour)
        result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, event_duration)
        self.assertEqual(input_occs_starts, result.value_as_float_list)

    def test_compute_nb_occurrences_in_parallel_2_hours(self):
        input_occs_starts = [20, 10, 14, 15]
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts)
        event_duration = SourceValue(2 * u.hour)
        result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, event_duration)
        self.assertTrue(np.allclose([20, 30, 24, 29, 15], result.value_as_float_list))

    def test_compute_nb_occurrences_in_parallel_partial_hour(self):
        input_occs_starts = [20, 10, 14, 15]
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts)
        event_duration = SourceValue(30 * u.min)
        result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, event_duration)
        self.assertEqual([10, 5, 7, 7.5], result.value_as_float_list)

    def test_compute_nb_occurrences_in_parallel_partial_hour_greater_than_one(self):
        input_occs_starts = [20, 10, 14, 15]
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts)
        event_duration = SourceValue(150 * u.min)
        result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, event_duration)
        self.assertTrue(np.allclose([20, 30, 34, 34, 22, 7.5], result.magnitude))

    def test_compute_nb_occurrences_in_parallel_matches_reference_convolution(self):
        rng = np.random.default_rng(0)
        input_occs_starts = rng.integers(0, 1000, size=500).astype(np.float32)
        input_occs_starts[100:300] = 0
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts.tolist())
        for nb_hours in (1, 2, 24, 499, 500, 800):
            with self.subTest(nb_hours=nb_hours):
                result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, SourceValue(nb_hours * u.hour))
                expected = np.convolve(input_occs_starts.astype(np.float64), np.ones(nb_hours), mode="full")
                np.testing.assert_array_equal(expected.astype(np.float32), result.magnitude)

    def test_compute_nb_occurrences_in_parallel_keeps_empty_hours_at_exactly_zero(self):
        input_occs_starts = [0, 0, 0, 7, 0, 0, 0, 0, 0]
        input_occs_starts_hvals = create_source_hourly_values_from_list(input_occs_starts)
        result = compute_nb_avg_hourly_occurrences(input_occs_starts_hvals, SourceValue(2 * u.hour))
        self.assertEqual([0, 0, 0, 7, 7, 0, 0, 0, 0, 0], result.value_as_float_list)
