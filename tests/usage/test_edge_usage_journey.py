import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.core.hardware.edge_device import EdgeDevice
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestEdgeUsageJourney(TestCase):
    def setUp(self):
        self.mock_edge_process_1 = MagicMock(spec=RecurrentEdgeProcess)
        self.mock_edge_process_1.id = "mock_process_1"
        self.mock_edge_process_1.name = "Mock Process 1"
        
        self.mock_edge_process_2 = MagicMock(spec=RecurrentEdgeProcess)
        self.mock_edge_process_2.id = "mock_process_2"
        self.mock_edge_process_2.name = "Mock Process 2"
        
        self.mock_edge_device = MagicMock(spec=EdgeDevice)
        self.mock_edge_device.id = "mock_device"
        self.mock_edge_device.name = "Mock Device"
        
        self.usage_span = SourceValue(2 * u.year)
        
        self.edge_usage_journey = EdgeUsageJourney(
            "test edge usage journey",
            edge_processes=[self.mock_edge_process_1, self.mock_edge_process_2],
            edge_device=self.mock_edge_device,
            usage_span=self.usage_span
        )

    def test_init(self):
        """Test EdgeUsageJourney initialization."""
        self.assertEqual("test edge usage journey", self.edge_usage_journey.name)
        self.assertEqual([self.mock_edge_process_1, self.mock_edge_process_2], self.edge_usage_journey.edge_processes)
        self.assertEqual(self.mock_edge_device, self.edge_usage_journey.edge_device)
        self.assertEqual("Usage span of test edge usage journey from e-footprint hypothesis", self.edge_usage_journey.usage_span.label)
        self.assertEqual(2 * u.year, self.edge_usage_journey.usage_span.value)

    def test_edge_usage_pattern_property_no_containers(self):
        """Test edge_usage_pattern property when no containers are set."""
        self.assertIsNone(self.edge_usage_journey.edge_usage_pattern)

    def test_edge_usage_pattern_property_single_container(self):
        """Test edge_usage_pattern property with single container."""
        mock_pattern = MagicMock()
        mock_pattern.name = "Mock Pattern"

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern])

        self.assertEqual(mock_pattern, self.edge_usage_journey.edge_usage_pattern)

    def test_edge_usage_pattern_property_multiple_containers_raises_error(self):
        """Test edge_usage_pattern property raises error with multiple containers."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.name = "Pattern 2"

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])

        with self.assertRaises(PermissionError) as context:
            _ = self.edge_usage_journey.edge_usage_pattern
        
        expected_message_part = ("EdgeUsageJourney object can only be associated with one EdgeUsagePattern object but ")
        self.assertIn(expected_message_part, str(context.exception))

    def test_systems_property(self):
        """Test systems property delegates to edge_usage_pattern."""
        mock_pattern = MagicMock()
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_pattern.systems = [mock_system_1, mock_system_2]

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern])
        
        self.assertEqual([mock_system_1, mock_system_2], self.edge_usage_journey.systems)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_no_edge_usage_pattern(self):
        """Test that edge_processes and edge_device are returned as dependent objects."""
        self.assertIsNone(self.edge_usage_journey.edge_usage_pattern)
        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [self.mock_edge_process_1, self.mock_edge_process_2, self.mock_edge_device]
        self.assertEqual(expected_objects, dependent_objects)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_with_edge_usage_pattern(self):
        """Test that edge_usage_pattern is returned as dependent object when present."""
        mock_pattern = MagicMock()
        mock_pattern.name = "Mock Pattern"

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern])

        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [mock_pattern]
        self.assertEqual(expected_objects, dependent_objects)


if __name__ == "__main__":
    unittest.main()