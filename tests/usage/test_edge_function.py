import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.recurrent_edge_resource_needed import RecurrentEdgeResourceNeed
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from tests.utils import set_modeling_obj_containers


class TestEdgeFunction(TestCase):
    def setUp(self):
        self.mock_edge_need_1 = MagicMock(spec=RecurrentEdgeResourceNeed)
        self.mock_edge_need_1.id = "mock_need_1"
        self.mock_edge_need_1.name = "Mock Need 1"

        self.mock_edge_need_2 = MagicMock(spec=RecurrentEdgeResourceNeed)
        self.mock_edge_need_2.id = "mock_need_2"
        self.mock_edge_need_2.name = "Mock Need 2"

        self.edge_function = EdgeFunction(
            "test edge function",
            edge_needs=[self.mock_edge_need_1, self.mock_edge_need_2]
        )

    def test_init(self):
        """Test EdgeFunction initialization."""
        self.assertEqual("test edge function", self.edge_function.name)
        self.assertEqual([self.mock_edge_need_1, self.mock_edge_need_2], self.edge_function.edge_needs)

    def test_edge_usage_journeys_property_no_containers(self):
        """Test edge_usage_journeys property when no containers are set."""
        self.assertEqual([], self.edge_function.edge_usage_journeys)

    def test_edge_usage_journeys_property_single_container(self):
        """Test edge_usage_journeys property with single container."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.name = "Mock Journey"

        set_modeling_obj_containers(self.edge_function, [mock_journey])

        self.assertEqual([mock_journey], self.edge_function.edge_usage_journeys)

    def test_edge_usage_journeys_property_multiple_containers(self):
        """Test edge_usage_journeys property returns all containers."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_1.name = "Journey 1"
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2.name = "Journey 2"

        set_modeling_obj_containers(self.edge_function, [mock_journey_1, mock_journey_2])

        self.assertEqual({mock_journey_1, mock_journey_2}, set(self.edge_function.edge_usage_journeys))

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that edge_needs are returned as dependent objects."""
        dependent_objects = self.edge_function.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_need_1, self.mock_edge_need_2], dependent_objects)

    def test_systems_property_no_journeys(self):
        """Test systems property when no journeys are set."""
        self.assertEqual([], self.edge_function.systems)

    def test_systems_property_single_journey(self):
        """Test systems property with single journey."""
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_journey.systems = [mock_system_1, mock_system_2]

        set_modeling_obj_containers(self.edge_function, [mock_journey])

        self.assertEqual({mock_system_1, mock_system_2}, set(self.edge_function.systems))

    def test_systems_property_multiple_journeys(self):
        """Test systems property aggregates across multiple journeys."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_system_3 = MagicMock()
        mock_journey_1.systems = [mock_system_1, mock_system_2]
        mock_journey_2.systems = [mock_system_2, mock_system_3]

        set_modeling_obj_containers(self.edge_function, [mock_journey_1, mock_journey_2])

        systems = self.edge_function.systems
        self.assertEqual(3, len(systems))
        self.assertIn(mock_system_1, systems)
        self.assertIn(mock_system_2, systems)
        self.assertIn(mock_system_3, systems)


if __name__ == "__main__":
    unittest.main()