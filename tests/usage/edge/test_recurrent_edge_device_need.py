import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeDeviceNeed(TestCase):
    def setUp(self):
        self.mock_edge_device = MagicMock(spec=EdgeDevice)
        self.mock_edge_device.name = "Mock Device"

        self.mock_component_need_1 = MagicMock(spec=RecurrentEdgeComponentNeed)
        self.mock_component_need_1.name = "Component Need 1"

        self.mock_component_need_2 = MagicMock(spec=RecurrentEdgeComponentNeed)
        self.mock_component_need_2.name = "Component Need 2"

        self.device_need = RecurrentEdgeDeviceNeed(
            "test device need",
            edge_device=self.mock_edge_device,
            recurrent_edge_component_needs=[self.mock_component_need_1, self.mock_component_need_2]
        )

    def test_init(self):
        """Test RecurrentEdgeDeviceNeed initialization."""
        self.assertEqual("test device need", self.device_need.name)
        self.assertEqual(self.mock_edge_device, self.device_need.edge_device)
        self.assertEqual(
            [self.mock_component_need_1, self.mock_component_need_2],
            self.device_need.recurrent_edge_component_needs
        )

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that recurrent_edge_component_needs are returned as dependent objects."""
        dependent_objects = self.device_need.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_component_need_1, self.mock_component_need_2], dependent_objects)

    def test_edge_functions_property_no_containers(self):
        """Test edge_functions property when no containers are set."""
        self.assertEqual([], self.device_need.edge_functions)

    def test_edge_functions_property_single_container(self):
        """Test edge_functions property with single container."""
        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.name = "Mock Function"

        set_modeling_obj_containers(self.device_need, [mock_function])

        self.assertEqual([mock_function], self.device_need.edge_functions)

    def test_edge_functions_property_multiple_containers(self):
        """Test edge_functions property returns all containers."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.name = "Function 1"
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.name = "Function 2"

        set_modeling_obj_containers(self.device_need, [mock_function_1, mock_function_2])

        self.assertEqual({mock_function_1, mock_function_2}, set(self.device_need.edge_functions))

    def test_edge_usage_journeys_property_no_functions(self):
        """Test edge_usage_journeys property when no functions exist."""
        self.assertEqual([], self.device_need.edge_usage_journeys)

    def test_edge_usage_journeys_property_multiple_functions_with_deduplication(self):
        """Test edge_usage_journeys property deduplicates across functions."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_3 = MagicMock(spec=EdgeUsageJourney)

        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.edge_usage_journeys = [mock_journey_2, mock_journey_3]

        set_modeling_obj_containers(self.device_need, [mock_function_1, mock_function_2])

        journeys = self.device_need.edge_usage_journeys
        self.assertEqual(3, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)
        self.assertIn(mock_journey_3, journeys)

    def test_edge_usage_patterns_property_no_journeys(self):
        """Test edge_usage_patterns property when no journeys exist."""
        self.assertEqual([], self.device_need.edge_usage_patterns)

    def test_edge_usage_patterns_property_multiple_journeys_with_deduplication(self):
        """Test edge_usage_patterns property deduplicates across journeys."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_3 = MagicMock(spec=EdgeUsagePattern)

        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.edge_usage_patterns = [mock_pattern_2, mock_pattern_3]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        set_modeling_obj_containers(self.device_need, [mock_function])

        patterns = self.device_need.edge_usage_patterns
        self.assertEqual(3, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)
        self.assertIn(mock_pattern_3, patterns)


if __name__ == "__main__":
    unittest.main()
