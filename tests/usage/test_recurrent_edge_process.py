import unittest
from copy import copy
from unittest import TestCase
from unittest.mock import MagicMock

import ciso8601
import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.system import System
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeProcess(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.recurrent_compute_needed = SourceRecurrentValues(
            Quantity(np.array([2.5] * 168, dtype=np.float32), u.cpu_core))
        self.recurrent_ram_needed = SourceRecurrentValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB))
        self.recurrent_storage_needed = SourceRecurrentValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB))
        
        self.edge_process = RecurrentEdgeProcess(
            "test edge process",
            recurrent_compute_needed=self.recurrent_compute_needed,
            recurrent_ram_needed=self.recurrent_ram_needed,
            recurrent_storage_needed=self.recurrent_storage_needed)

    def test_init(self):
        """Test RecurrentEdgeProcess initialization."""
        self.assertEqual("test edge process", self.edge_process.name)
        self.assertIs(self.recurrent_compute_needed, self.edge_process.recurrent_compute_needed)
        self.assertIs(self.recurrent_ram_needed, self.edge_process.recurrent_ram_needed)
        from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
        self.assertIsInstance(self.edge_process.unitary_hourly_compute_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_process.unitary_hourly_ram_need_per_usage_pattern, ExplainableObjectDict)
        self.assertIsInstance(self.edge_process.unitary_hourly_storage_need_per_usage_pattern, ExplainableObjectDict)

    def test_edge_usage_journeys_property_no_containers(self):
        """Test edge_usage_journeys property when no containers are set."""
        self.assertEqual([], self.edge_process.edge_usage_journeys)

    def test_edge_usage_journeys_property_single_container(self):
        """Test edge_usage_journeys property with single container."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.name = "Mock Journey"
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual([mock_journey], self.edge_process.edge_usage_journeys)

    def test_edge_usage_journeys_property_multiple_containers(self):
        """Test edge_usage_journey property raises error with multiple containers."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.name = "Journey 1"
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.name = "Journey 2"
        
        set_modeling_obj_containers(self.edge_process, [mock_journey_1, mock_journey_2])

        self.assertEqual({mock_journey_1, mock_journey_2}, set(self.edge_process.edge_usage_journeys))

    def test_edge_usage_patterns_property_no_containers(self):
        """Test edge_usage_patterns property when no containers are set."""
        self.assertEqual([], self.edge_process.edge_usage_patterns)

    def test_edge_usage_patterns_property_with_journey(self):
        """Test edge_usage_patterns property delegates to edge_usage_journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_process.edge_usage_patterns))

    def test_edge_devices_property_no_containers(self):
        """Test edge_devices property when no containers are set."""
        self.assertEqual([], self.edge_process.edge_devices)

    def test_edge_devices_property_with_journey(self):
        """Test edge_devices property delegates to edge_usage_journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey.edge_device = mock_device
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual([mock_device], self.edge_process.edge_devices)

    def test_systems_property_no_containers(self):
        """Test systems property when no containers are set."""
        self.assertEqual([], self.edge_process.systems)

    def test_systems_property_with_journey(self):
        """Test systems property delegates to edge_usage_journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_system_1 = MagicMock(spec=System)
        mock_system_2 = MagicMock(spec=System)
        mock_journey.systems = [mock_system_1, mock_system_2]
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual({mock_system_1, mock_system_2}, set(self.edge_process.systems))

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test modeling_objects_whose_attributes_depend_directly_on_me returns empty list."""
        dependent_objects = self.edge_process.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([], dependent_objects)

    def test_update_unitary_hourly_compute_need_per_usage_pattern(self):
        """Test update_unitary_hourly_compute_need_per_usage_pattern method."""
        # Mock the edge usage patterns and their properties
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2.name = "Pattern 2"

        mock_nb_euj_in_parallel_1 = MagicMock(spec=ExplainableHourlyQuantities)
        mock_nb_euj_in_parallel_2 = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country_1 = MagicMock()
        mock_country_2 = MagicMock()
        mock_timezone_1 = MagicMock()
        mock_timezone_2 = MagicMock()

        mock_pattern_1.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel_1
        mock_pattern_1.country = mock_country_1
        mock_country_1.timezone = mock_timezone_1
        mock_pattern_2.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel_2
        mock_pattern_2.country = mock_country_2
        mock_country_2.timezone = mock_timezone_2

        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        
        # Mock the generate_hourly_quantities_over_timespan method
        expected_result_1 = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result_2 = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result_1.set_label = MagicMock(return_value=expected_result_1)
        expected_result_2.set_label = MagicMock(return_value=expected_result_2)

        mapping = {mock_nb_euj_in_parallel_1: expected_result_1, mock_nb_euj_in_parallel_2: expected_result_2}
        self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan = MagicMock(
            side_effect=lambda x, tz: mapping[x])
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.edge_process.update_unitary_hourly_compute_need_per_usage_pattern()
        
        self.assertEqual(
            2, self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan.call_count)
        self.assertDictEqual(
            {mock_pattern_1: expected_result_1, mock_pattern_2: expected_result_2},
            self.edge_process.unitary_hourly_compute_need_per_usage_pattern
        )

    def test_update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern method."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country = MagicMock()
        mock_timezone = MagicMock()
        
        mock_pattern.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone
        
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result.set_label = MagicMock(return_value=expected_result)
        
        self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result)
        
        self.edge_process.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(mock_pattern)
        
        self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_nb_euj_in_parallel, mock_timezone)
        
        self.assertDictEqual(
            {mock_pattern: expected_result}, self.edge_process.unitary_hourly_compute_need_per_usage_pattern)

    def test_update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern_monday_start(self):
        """Test update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern when starting on Monday 00:00."""
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
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result.magnitude = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        expected_result.set_label = MagicMock(return_value=expected_result)

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result
        )

        self.edge_process.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(mock_pattern)

        # Values should not be modified since it starts on Monday 00:00
        np.testing.assert_array_equal(expected_result.magnitude, [1.0, 2.0, 3.0, 4.0, 5.0])

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_nb_euj_in_parallel, mock_timezone)

        self.assertEqual(
            {mock_pattern: expected_result}, self.edge_process.unitary_hourly_storage_need_per_usage_pattern)

    def test_update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern_non_monday_start(self):
        """Test update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern when not starting on Monday 00:00."""
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
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        original_values = np.array([1.0, 2.0, 3.0] * 50)  # 150 values
        expected_result.magnitude = original_values.copy()
        expected_result.set_label = MagicMock(return_value=expected_result)

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result
        )

        self.edge_process.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(mock_pattern)

        # First 120 hours (5 days * 24 hours) should be set to 0
        # Wednesday (weekday 2) to Monday (weekday 0): (7 - 2) * 24 - 0 = 120 hours
        expected_modified_values = original_values.copy()
        expected_modified_values[:120] = 0
        np.testing.assert_array_equal(expected_result.magnitude, expected_modified_values)

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_nb_euj_in_parallel, mock_timezone)

        self.assertEqual(
            {mock_pattern: expected_result}, self.edge_process.unitary_hourly_storage_need_per_usage_pattern)

    def test_update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern_friday_afternoon_start(self):
        """Test update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern when starting on Friday afternoon."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern Friday Afternoon"
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        # 2025-01-03 is a Friday at 15:00
        mock_nb_euj_in_parallel.start_date = ciso8601.parse_datetime("2025-01-03T15:00:00")
        mock_country = MagicMock()
        mock_timezone = MagicMock()

        mock_pattern.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        # Create mock result with magnitude array
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        original_values = np.array([1.0, 2.0, 3.0] * 20)  # 60 values, enough to cover until first Monday
        expected_result.magnitude = original_values.copy()
        expected_result.set_label = MagicMock(return_value=expected_result)

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result
        )

        self.edge_process.update_dict_element_in_unitary_hourly_storage_need_per_usage_pattern(mock_pattern)

        # From Friday 15:00 to Monday 00:00: (7 - 4) * 24 - 15 = 57 hours
        # Friday is weekday 4, so (7 - 4) * 24 - 15 = 3 * 24 - 15 = 72 - 15 = 57 hours
        expected_modified_values = original_values.copy()
        expected_modified_values[:57] = 0
        np.testing.assert_array_equal(expected_result.magnitude, expected_modified_values)

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_nb_euj_in_parallel, mock_timezone)

        self.assertEqual(
            {mock_pattern: expected_result}, self.edge_process.unitary_hourly_storage_need_per_usage_pattern)

    def test_from_defaults_class_method(self):
        """Test RecurrentEdgeProcess can be created using from_defaults class method."""
        edge_process_from_defaults = RecurrentEdgeProcess.from_defaults("default process")
        
        self.assertEqual("default process", edge_process_from_defaults.name)
        self.assertIsInstance(edge_process_from_defaults.recurrent_compute_needed, SourceRecurrentValues)
        self.assertIsInstance(edge_process_from_defaults.recurrent_ram_needed, SourceRecurrentValues)
        self.assertEqual(
            edge_process_from_defaults.recurrent_compute_needed.unit, u.cpu_core)
        self.assertEqual(
            edge_process_from_defaults.recurrent_ram_needed.unit, u.GB)

    def test_recurrent_values_parameters_validation(self):
        """Test that recurrent values parameters must be ExplainableRecurrentQuantities."""
        with self.assertRaises(TypeError):
            RecurrentEdgeProcess(
                "invalid process",
                recurrent_compute_needed="invalid",
                recurrent_ram_needed=copy(self.recurrent_ram_needed)
            )
        
        with self.assertRaises(TypeError):
            RecurrentEdgeProcess(
                "invalid process", 
                recurrent_compute_needed=copy(self.recurrent_compute_needed.copy()),
                recurrent_ram_needed=123
            )


if __name__ == "__main__":
    unittest.main()