import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import ciso8601
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.constants.units import u


class TestRecurrentEdgeStorageNeed(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_storage = MagicMock(spec=EdgeStorage)
        self.mock_storage.name = "Mock Storage"
        self.mock_storage.expected_need_units.return_value = [u.GB, u.TB, u.B, u.MB, u.kB]
        self.mock_storage.edge_device = None

        self.recurrent_storage_needed = SourceRecurrentValues(
            Quantity(np.array([2.0] * 168, dtype=np.float32), u.GB))

        self.storage_need = RecurrentEdgeStorageNeed(
            name="Test Storage Need",
            edge_component=self.mock_storage,
            recurrent_need=self.recurrent_storage_needed
        )

    def test_init(self):
        """Test initialization of RecurrentEdgeStorageNeed."""
        self.assertEqual("Test Storage Need", self.storage_need.name)
        self.assertEqual(self.mock_storage, self.storage_need.edge_component)

    def test_update_dict_element_in_unitary_hourly_need_per_usage_pattern_monday_start(self):
        """Test update when starting on Monday 00:00 - no values should be zeroed."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern Monday"
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        # 2025-01-06 is a Monday
        mock_nb_euj_in_parallel.start_date = ciso8601.parse_datetime("2025-01-06T00:00:00")
        mock_country = MagicMock()
        mock_timezone = MagicMock()

        mock_pattern.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        # Create mock result with magnitude array
        base_storage_result = MagicMock(spec=ExplainableHourlyQuantities)
        original_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        base_storage_result.magnitude = original_values.copy()
        base_storage_result.set_label = MagicMock(return_value=base_storage_result)

        self.storage_need.recurrent_need.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=base_storage_result
        )

        self.storage_need.update_dict_element_in_unitary_hourly_need_per_usage_pattern(mock_pattern)

        # Since we start on Monday 00:00, no values should be zeroed
        result = self.storage_need.unitary_hourly_need_per_usage_pattern[mock_pattern]
        np.testing.assert_array_equal(result.magnitude, original_values)
        # Verify set_label was called with the correct label (may be called multiple times during parent/child updates)
        result.set_label.assert_called_with("Test Storage Need unitary hourly need for Test Pattern Monday")

    def test_update_dict_element_in_unitary_hourly_need_per_usage_pattern_non_monday_start(self):
        """Test update when not starting on Monday 00:00 - values should be zeroed until first Monday."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern Wednesday"
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        # 2025-01-01 is a Wednesday at 00:00
        mock_nb_euj_in_parallel.start_date = ciso8601.parse_datetime("2025-01-01T00:00:00")
        mock_country = MagicMock()
        mock_timezone = MagicMock()

        mock_pattern.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        # Create mock result with magnitude array - enough hours to cover until first Monday
        # From Wednesday 00:00 to Monday 00:00 = 5 days = 120 hours
        base_storage_result = MagicMock(spec=ExplainableHourlyQuantities)
        original_values = np.array([1.0, 2.0, 3.0] * 50)  # 150 values
        base_storage_result.magnitude = original_values.copy()
        base_storage_result.set_label = MagicMock(return_value=base_storage_result)

        self.storage_need.recurrent_need.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=base_storage_result
        )

        self.storage_need.update_dict_element_in_unitary_hourly_need_per_usage_pattern(mock_pattern)

        result = self.storage_need.unitary_hourly_need_per_usage_pattern[mock_pattern]
        # From Wednesday 00:00, we need to zero until Monday 00:00
        # Wednesday is weekday 2, so (7-2)*24 - 0 = 120 hours
        expected_zeros = 120
        np.testing.assert_array_equal(result.magnitude[:expected_zeros], np.zeros(expected_zeros))
        # After the zeros, values should be original
        np.testing.assert_array_equal(result.magnitude[expected_zeros:], original_values[expected_zeros:])


if __name__ == '__main__':
    unittest.main()
