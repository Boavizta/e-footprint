import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeeded
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge_hardware import EdgeHardware
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeResourceNeeded(TestCase):
    def setUp(self):
        self.mock_edge_hardware = MagicMock(spec=EdgeHardware)
        self.mock_edge_hardware.id = "mock_hardware"
        self.mock_edge_hardware.name = "Mock Hardware"

        self.edge_resource_needed = RecurrentEdgeResourceNeeded(
            "test edge resource needed",
            edge_hardware=self.mock_edge_hardware
        )

    def test_init(self):
        """Test RecurrentEdgeResourceNeeded initialization."""
        self.assertEqual("test edge resource needed", self.edge_resource_needed.name)
        self.assertEqual(self.mock_edge_hardware, self.edge_resource_needed.edge_hardware)

    def test_edge_functions_property_no_containers(self):
        """Test edge_functions property when no containers are set."""
        self.assertEqual([], self.edge_resource_needed.edge_functions)

    def test_edge_functions_property_single_container(self):
        """Test edge_functions property with single container."""
        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.name = "Mock Function"

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function])

        self.assertEqual([mock_function], self.edge_resource_needed.edge_functions)

    def test_edge_functions_property_multiple_containers(self):
        """Test edge_functions property returns all containers."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.name = "Function 1"
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.name = "Function 2"

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function_1, mock_function_2])

        self.assertEqual({mock_function_1, mock_function_2}, set(self.edge_resource_needed.edge_functions))

    def test_edge_usage_journeys_property_no_functions(self):
        """Test edge_usage_journeys property when no functions are set."""
        self.assertEqual([], self.edge_resource_needed.edge_usage_journeys)

    def test_edge_usage_journeys_property_single_function(self):
        """Test edge_usage_journeys property with single function."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function])

        self.assertEqual({mock_journey_1, mock_journey_2}, set(self.edge_resource_needed.edge_usage_journeys))

    def test_edge_usage_journeys_property_multiple_functions_with_deduplication(self):
        """Test edge_usage_journeys property deduplicates journeys across functions."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_3 = MagicMock(spec=EdgeUsageJourney)

        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.edge_usage_journeys = [mock_journey_2, mock_journey_3]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function_1, mock_function_2])

        journeys = self.edge_resource_needed.edge_usage_journeys
        self.assertEqual(3, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)
        self.assertIn(mock_journey_3, journeys)

    def test_edge_usage_patterns_property_no_journeys(self):
        """Test edge_usage_patterns property when no journeys exist."""
        self.assertEqual([], self.edge_resource_needed.edge_usage_patterns)

    def test_edge_usage_patterns_property_single_journey(self):
        """Test edge_usage_patterns property with single journey."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)

        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_resource_needed.edge_usage_patterns))

    def test_edge_usage_patterns_property_multiple_journeys_with_deduplication(self):
        """Test edge_usage_patterns property deduplicates patterns across journeys."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_3 = MagicMock(spec=EdgeUsagePattern)

        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.edge_usage_patterns = [mock_pattern_2, mock_pattern_3]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function])

        patterns = self.edge_resource_needed.edge_usage_patterns
        self.assertEqual(3, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)
        self.assertIn(mock_pattern_3, patterns)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that edge_hardware is returned as dependent object."""
        dependent_objects = self.edge_resource_needed.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_hardware], dependent_objects)

    def test_systems_property_no_functions(self):
        """Test systems property when no functions are set."""
        self.assertEqual([], self.edge_resource_needed.systems)

    def test_systems_property_single_function(self):
        """Test systems property with single function."""
        mock_function = MagicMock(spec=EdgeFunction)
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_function.systems = [mock_system_1, mock_system_2]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function])

        self.assertEqual({mock_system_1, mock_system_2}, set(self.edge_resource_needed.systems))

    def test_systems_property_multiple_functions(self):
        """Test systems property aggregates across multiple functions."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_system_3 = MagicMock()
        mock_function_1.systems = [mock_system_1, mock_system_2]
        mock_function_2.systems = [mock_system_2, mock_system_3]

        set_modeling_obj_containers(self.edge_resource_needed, [mock_function_1, mock_function_2])

        systems = self.edge_resource_needed.systems
        self.assertEqual(3, len(systems))
        self.assertIn(mock_system_1, systems)
        self.assertIn(mock_system_2, systems)
        self.assertIn(mock_system_3, systems)


if __name__ == "__main__":
    unittest.main()