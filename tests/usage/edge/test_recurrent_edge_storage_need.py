import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import ciso8601
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.constants.units import u
from tests.utils import create_mod_obj_mock


class TestRecurrentEdgeStorageNeed(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.mock_storage.name = "Mock Storage"
        self.mock_storage.compatible_root_units = [u.bit]
        self.mock_storage.edge_device = None

        self.recurrent_storage_needed = SourceRecurrentValues(
            Quantity(np.array([2.0] * 168, dtype=np.float32), u.GB))

        self.storage_need = RecurrentEdgeStorageNeed(name="Test Storage Need", edge_component=self.mock_storage,
                                                     recurrent_need=self.recurrent_storage_needed)

    def test_init(self):
        """Test initialization of RecurrentEdgeStorageNeed."""
        self.assertEqual("Test Storage Need", self.storage_need.name)
        self.assertEqual(self.mock_storage, self.storage_need.edge_component)

    def test_update_dict_element_in_unitary_hourly_need_per_usage_pattern_monday_start(self):
        """Test update when starting on Monday 00:00 - no values should be zeroed."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern Monday")
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        # 2025-01-06 is a Monday
        mock_nb_euj_in_parallel.start_date = ciso8601.parse_datetime("2025-01-06T00:00:00")
        mock_country = MagicMock()
        mock_timezone = MagicMock()
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, name="Mock Journey")

        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: mock_nb_euj_in_parallel
        }
        mock_edge_function = create_mod_obj_mock(EdgeFunction, name="Mock Function")
        mock_recurrent_device_need = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Device Need")
        mock_recurrent_device_need.recurrent_edge_component_needs = [self.storage_need]
        mock_edge_function.recurrent_edge_device_needs = [mock_recurrent_device_need]
        mock_edge_usage_journey.edge_functions = [mock_edge_function]
        mock_pattern.edge_usage_journey = mock_edge_usage_journey
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        # Create mock result with magnitude array
        original_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        base_storage_result = ExplainableHourlyQuantities(
            original_values * u.GB,
            mock_nb_euj_in_parallel.start_date,
            "base storage result"
        )

        # Patch at class level because __slots__ prevents instance-level patching
        with patch.object(SourceRecurrentValues, 'generate_hourly_quantities_over_timespan',
                          return_value=base_storage_result):
            self.storage_need.update_dict_element_in_unitary_hourly_need_per_usage_pattern(mock_pattern)

            # Since we start on Monday 00:00, no values should be zeroed
            result = self.storage_need.unitary_hourly_need_per_usage_pattern[mock_pattern]
            np.testing.assert_array_equal(result.magnitude, original_values)
            self.assertEqual("Test Storage Need unitary hourly need for Test Pattern Monday", result.label)

    def test_update_dict_element_in_unitary_hourly_need_per_usage_pattern_non_monday_start(self):
        """Test update when not starting on Monday 00:00 - values should be zeroed until first Monday."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern Wednesday")
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        # 2025-01-01 is a Wednesday at 00:00
        mock_nb_euj_in_parallel.start_date = ciso8601.parse_datetime("2025-01-01T00:00:00")
        mock_country = MagicMock()
        mock_timezone = MagicMock()
        mock_edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, name="Mock Journey")

        mock_edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            mock_pattern: mock_nb_euj_in_parallel
        }
        mock_edge_function = create_mod_obj_mock(EdgeFunction, name="Mock Function")
        mock_recurrent_device_need = create_mod_obj_mock(RecurrentEdgeDeviceNeed, name="Mock Device Need")
        mock_recurrent_device_need.recurrent_edge_component_needs = [self.storage_need]
        mock_edge_function.recurrent_edge_device_needs = [mock_recurrent_device_need]
        mock_edge_usage_journey.edge_functions = [mock_edge_function]
        mock_pattern.edge_usage_journey = mock_edge_usage_journey
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        # Create mock result with magnitude array - enough hours to cover until first Monday
        # From Wednesday 00:00 to Monday 00:00 = 5 days = 120 hours
        original_values = np.array([1.0, 2.0, 3.0] * 50)  # 150 values
        base_storage_result = ExplainableHourlyQuantities(
            original_values * u.GB,
            mock_nb_euj_in_parallel.start_date,
            "base storage result"
        )

        # Patch at class level because __slots__ prevents instance-level patching
        with patch.object(SourceRecurrentValues, 'generate_hourly_quantities_over_timespan',
                          return_value=base_storage_result):
            self.storage_need.update_dict_element_in_unitary_hourly_need_per_usage_pattern(mock_pattern)

            result = self.storage_need.unitary_hourly_need_per_usage_pattern[mock_pattern]
            # From Wednesday 00:00, we need to zero until Monday 00:00
            # Wednesday is weekday 2, so (7-2)*24 - 0 = 120 hours
            expected_zeros = 120
            np.testing.assert_array_equal(result.magnitude[:expected_zeros], np.zeros(expected_zeros))
            # After the zeros, values should be original
            np.testing.assert_array_equal(result.magnitude[expected_zeros:], original_values[expected_zeros:])

    def test_update_cumulative_unitary_storage_need_per_usage_pattern(self):
        """Test cumulative unitary storage need per usage pattern is computed independently."""
        pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        self.storage_need.unitary_hourly_need_per_usage_pattern = {
            pattern: ExplainableHourlyQuantities(
                np.array([1.0, 0.0, 2.0], dtype=np.float32) * u.GB,
                ciso8601.parse_datetime("2025-01-06T00:00:00"),
                "pattern need",
            )
        }

        self.storage_need.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(pattern)

        np.testing.assert_array_equal(
            self.storage_need.cumulative_unitary_storage_need_per_usage_pattern[pattern].to(u.GB_stored).magnitude,
            np.array([1.0, 1.0, 3.0], dtype=np.float32)
        )

    def test_update_total_hourly_need_across_usage_patterns_uses_cumulative_per_pattern(self):
        """Test total hourly need across usage patterns uses cumulative per-pattern need and parallel journeys."""
        pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")
        pattern_1.edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey 1")
        pattern_2.edge_usage_journey = create_mod_obj_mock(EdgeUsageJourney, "Journey 2")
        pattern_1.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            pattern_1: ExplainableHourlyQuantities(
                np.array([2.0, 2.0, 2.0], dtype=np.float32) * u.concurrent,
                ciso8601.parse_datetime("2025-01-06T00:00:00"),
                "pattern 1 journeys",
            )
        }
        pattern_2.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern = {
            pattern_2: ExplainableHourlyQuantities(
                np.array([3.0, 3.0, 3.0], dtype=np.float32) * u.concurrent,
                ciso8601.parse_datetime("2025-01-06T00:00:00"),
                "pattern 2 journeys",
            )
        }
        self.storage_need.cumulative_unitary_storage_need_per_usage_pattern = {
            pattern_1: ExplainableHourlyQuantities(
                np.array([1.0, 1.0, 3.0], dtype=np.float32) * u.GB,
                ciso8601.parse_datetime("2025-01-06T00:00:00"),
                "pattern 1 cumulative need",
            ),
            pattern_2: ExplainableHourlyQuantities(
                np.array([0.0, 2.0, 2.0], dtype=np.float32) * u.GB,
                ciso8601.parse_datetime("2025-01-06T00:00:00"),
                "pattern 2 cumulative need",
            ),
        }

        with patch.object(
            RecurrentEdgeStorageNeed, "edge_usage_patterns", new_callable=PropertyMock, return_value=[pattern_1, pattern_2]
        ):
            self.storage_need.update_total_hourly_need_across_usage_patterns()

        np.testing.assert_array_equal(
            self.storage_need.total_hourly_need_across_usage_patterns.magnitude,
            np.array([2.0, 8.0, 12.0]),
        )


if __name__ == '__main__':
    unittest.main()
