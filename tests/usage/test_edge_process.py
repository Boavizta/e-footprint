import unittest
from copy import copy
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceRecurringValues
from efootprint.core.usage.edge_process import EdgeProcess
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.core.system import System
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestEdgeProcess(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.recurrent_compute_needed = SourceRecurringValues(
            Quantity(np.array([2.5] * 168, dtype=np.float32), u.cpu_core))
        self.recurrent_ram_needed = SourceRecurringValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB))
        self.recurrent_storage_needed = SourceRecurringValues(
            Quantity(np.array([4.0] * 168, dtype=np.float32), u.GB))
        
        self.edge_process = EdgeProcess(
            "test edge process",
            recurrent_compute_needed=self.recurrent_compute_needed,
            recurrent_ram_needed=self.recurrent_ram_needed,
            recurrent_storage_needed=self.recurrent_storage_needed)

    def test_init(self):
        """Test EdgeProcess initialization."""
        self.assertEqual("test edge process", self.edge_process.name)
        self.assertIs(self.recurrent_compute_needed, self.edge_process.recurrent_compute_needed)
        self.assertIs(self.recurrent_ram_needed, self.edge_process.recurrent_ram_needed)
        self.assertIsInstance(self.edge_process.unitary_hourly_compute_need_over_full_timespan, EmptyExplainableObject)
        self.assertIsInstance(self.edge_process.unitary_hourly_ram_need_over_full_timespan, EmptyExplainableObject)

    def test_edge_usage_journey_property_no_containers(self):
        """Test edge_usage_journey property when no containers are set."""
        self.assertIsNone(self.edge_process.edge_usage_journey)

    def test_edge_usage_journey_property_single_container(self):
        """Test edge_usage_journey property with single container."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.name = "Mock Journey"
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual(mock_journey, self.edge_process.edge_usage_journey)

    def test_edge_usage_journey_property_multiple_containers_raises_error(self):
        """Test edge_usage_journey property raises error with multiple containers."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.name = "Journey 1"
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.name = "Journey 2"
        
        set_modeling_obj_containers(self.edge_process, [mock_journey_1, mock_journey_2])
        
        with self.assertRaises(PermissionError) as context:
            _ = self.edge_process.edge_usage_journey
        
        expected_message_part = ("EdgeProcess object can only be associated with one EdgeUsageJourney object but ")
        self.assertIn(expected_message_part, str(context.exception))

    def test_edge_usage_pattern_property_no_containers(self):
        """Test edge_usage_pattern property when no containers are set."""
        self.assertIsNone(self.edge_process.edge_usage_pattern)

    def test_edge_usage_pattern_property_with_journey(self):
        """Test edge_usage_pattern property delegates to edge_usage_journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_journey.edge_usage_pattern = mock_pattern
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual(mock_pattern, self.edge_process.edge_usage_pattern)

    def test_edge_device_property_no_containers(self):
        """Test edge_device property when no containers are set."""
        self.assertIsNone(self.edge_process.edge_device)

    def test_edge_device_property_with_journey(self):
        """Test edge_device property delegates to edge_usage_journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey.edge_device = mock_device
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.assertEqual(mock_device, self.edge_process.edge_device)

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
        
        self.assertEqual([mock_system_1, mock_system_2], self.edge_process.systems)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test modeling_objects_whose_attributes_depend_directly_on_me returns edge_device."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_device = MagicMock(spec=EdgeDevice)
        mock_journey.edge_device = mock_device
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        dependent_objects = self.edge_process.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([mock_device], dependent_objects)

    def test_update_unitary_hourly_compute_need_over_full_timespan(self):
        """Test update_unitary_hourly_compute_need_over_full_timespan method."""
        # Mock the edge usage pattern and its hourly_edge_usage_journey_starts and country timezone
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_hourly_starts = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country = MagicMock()
        mock_timezone = MagicMock()
        
        mock_pattern.hourly_edge_usage_journey_starts = mock_hourly_starts
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone
        mock_journey.edge_usage_pattern = mock_pattern
        
        # Mock the generate_hourly_quantities_over_timespan method
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result)
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.edge_process.update_unitary_hourly_compute_need_over_full_timespan()
        
        self.edge_process.recurrent_compute_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_hourly_starts, mock_timezone)
        
        self.assertEqual(expected_result, self.edge_process.unitary_hourly_compute_need_over_full_timespan)

    def test_update_unitary_hourly_ram_need_over_full_timespan(self):
        """Test update_unitary_hourly_ram_need_over_full_timespan method."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_hourly_starts = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country = MagicMock()
        mock_timezone = MagicMock()
        
        mock_pattern.hourly_edge_usage_journey_starts = mock_hourly_starts
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone
        mock_journey.edge_usage_pattern = mock_pattern
        
        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        self.edge_process.recurrent_ram_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result
        )
        
        set_modeling_obj_containers(self.edge_process, [mock_journey])
        
        self.edge_process.update_unitary_hourly_ram_need_over_full_timespan()
        
        self.edge_process.recurrent_ram_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_hourly_starts, mock_timezone)
        
        self.assertEqual(expected_result, self.edge_process.unitary_hourly_ram_need_over_full_timespan)

    def test_update_unitary_hourly_storage_need_over_full_timespan(self):
        """Test update_unitary_hourly_storage_need_over_full_timespan method."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_hourly_starts = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country = MagicMock()
        mock_timezone = MagicMock()

        mock_pattern.hourly_edge_usage_journey_starts = mock_hourly_starts
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone
        mock_journey.edge_usage_pattern = mock_pattern

        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result
        )

        set_modeling_obj_containers(self.edge_process, [mock_journey])

        self.edge_process.update_unitary_hourly_storage_need_over_full_timespan()

        self.edge_process.recurrent_storage_needed.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_hourly_starts, mock_timezone)

        self.assertEqual(expected_result, self.edge_process.unitary_hourly_storage_need_over_full_timespan)

    def test_from_defaults_class_method(self):
        """Test EdgeProcess can be created using from_defaults class method."""
        edge_process_from_defaults = EdgeProcess.from_defaults("default process")
        
        self.assertEqual("default process", edge_process_from_defaults.name)
        self.assertIsInstance(edge_process_from_defaults.recurrent_compute_needed, SourceRecurringValues)
        self.assertIsInstance(edge_process_from_defaults.recurrent_ram_needed, SourceRecurringValues)
        self.assertEqual(
            edge_process_from_defaults.recurrent_compute_needed.unit, u.cpu_core)
        self.assertEqual(
            edge_process_from_defaults.recurrent_ram_needed.unit, u.GB)

    def test_recurrent_values_parameters_validation(self):
        """Test that recurrent values parameters must be ExplainableRecurringQuantities."""
        with self.assertRaises(TypeError):
            EdgeProcess(
                "invalid process",
                recurrent_compute_needed="invalid",
                recurrent_ram_needed=copy(self.recurrent_ram_needed)
            )
        
        with self.assertRaises(TypeError):
            EdgeProcess(
                "invalid process", 
                recurrent_compute_needed=copy(self.recurrent_compute_needed.copy()),
                recurrent_ram_needed=123
            )


if __name__ == "__main__":
    unittest.main()