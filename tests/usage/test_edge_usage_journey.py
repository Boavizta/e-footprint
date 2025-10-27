import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.recurrent_edge_resource_need import RecurrentEdgeResourceNeed
from efootprint.core.hardware.edge_device_base import EdgeDeviceBase
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestEdgeUsageJourney(TestCase):
    def setUp(self):
        self.mock_edge_device = MagicMock(spec=EdgeDeviceBase)
        self.mock_edge_device.id = "mock_device"
        self.mock_edge_device.name = "Mock Device"
        self.mock_edge_device.lifespan = SourceValue(4 * u.year)

        self.mock_edge_need_1 = MagicMock(spec=RecurrentEdgeResourceNeed)
        self.mock_edge_need_1.id = "mock_need_1"
        self.mock_edge_need_1.name = "Mock Need 1"
        self.mock_edge_need_1.edge_device = self.mock_edge_device

        self.mock_edge_need_2 = MagicMock(spec=RecurrentEdgeResourceNeed)
        self.mock_edge_need_2.id = "mock_need_2"
        self.mock_edge_need_2.name = "Mock Need 2"
        self.mock_edge_need_2.edge_device = self.mock_edge_device

        self.mock_edge_function_1 = MagicMock(spec=EdgeFunction)
        self.mock_edge_function_1.id = "mock_function_1"
        self.mock_edge_function_1.name = "Mock Function 1"
        self.mock_edge_function_1.recurrent_edge_resource_needs = [self.mock_edge_need_1]

        self.mock_edge_function_2 = MagicMock(spec=EdgeFunction)
        self.mock_edge_function_2.id = "mock_function_2"
        self.mock_edge_function_2.name = "Mock Function 2"
        self.mock_edge_function_2.recurrent_edge_resource_needs = [self.mock_edge_need_2]

        self.usage_span = SourceValue(2 * u.year)

        self.edge_usage_journey = EdgeUsageJourney(
            "test edge usage journey",
            edge_functions=[self.mock_edge_function_1, self.mock_edge_function_2],
            usage_span=self.usage_span
        )

    def test_init(self):
        """Test EdgeUsageJourney initialization."""
        self.assertEqual("test edge usage journey", self.edge_usage_journey.name)
        self.assertEqual([self.mock_edge_function_1, self.mock_edge_function_2], self.edge_usage_journey.edge_functions)
        self.assertEqual("Usage span of test edge usage journey from e-footprint hypothesis", self.edge_usage_journey.usage_span.label)
        self.assertEqual(2 * u.year, self.edge_usage_journey.usage_span.value)

    def test_recurrent_edge_resource_needs_property(self):
        """Test recurrent_edge_resource_needs property returns unique edge needs from all edge functions."""
        recurrent_edge_resource_needs = self.edge_usage_journey.recurrent_edge_resource_needs
        self.assertEqual({self.mock_edge_need_1, self.mock_edge_need_2}, set(recurrent_edge_resource_needs))

    def test_edge_devices_property(self):
        """Test edge_devices property returns unique edge devices from all edge needs."""
        edge_devices = self.edge_usage_journey.edge_devices
        self.assertEqual([self.mock_edge_device], edge_devices)

    def test_usage_span_superior_to_lifespan_raises_error(self):
        mock_edge_device = MagicMock(spec=EdgeDeviceBase)
        mock_edge_device.id = "mock_device"
        mock_edge_device.name = "Mock Device"
        mock_edge_device.lifespan = SourceValue(2 * u.year)

        mock_edge_need = MagicMock(spec=RecurrentEdgeResourceNeed)
        mock_edge_need.edge_device = mock_edge_device

        mock_edge_function = MagicMock(spec=EdgeFunction)
        mock_edge_function.recurrent_edge_resource_needs = [mock_edge_need]

        usage_span = SourceValue(4 * u.year)
        with self.assertRaises(InsufficientCapacityError) as context:
            EdgeUsageJourney("test euj", edge_functions=[mock_edge_function], usage_span=usage_span)

        self.assertEqual(mock_edge_device, context.exception.overloaded_object)
        self.assertEqual("lifespan", context.exception.capacity_type)
        self.assertEqual(mock_edge_device.lifespan, context.exception.available_capacity)
        self.assertEqual(usage_span, context.exception.requested_capacity)

    def test_changing_to_usage_span_superior_to_edge_device_lifespan_raises_error(self):
        mock_edge_device = MagicMock(spec=EdgeDeviceBase)
        mock_edge_device.id = "mock_device"
        mock_edge_device.name = "Mock Device"
        mock_edge_device.lifespan = SourceValue(2 * u.year)

        mock_edge_need = MagicMock(spec=RecurrentEdgeResourceNeed)
        mock_edge_need.edge_device = mock_edge_device

        mock_edge_function = MagicMock(spec=EdgeFunction)
        mock_edge_function.recurrent_edge_resource_needs = [mock_edge_need]

        usage_span = SourceValue(1 * u.year)
        euj = EdgeUsageJourney("test euj", edge_functions=[mock_edge_function], usage_span=usage_span)

        with self.assertRaises(InsufficientCapacityError):
            euj.usage_span = SourceValue(3 * u.year)

    def test_changing_to_usage_span_not_superior_to_edge_device_lifespan_doesnt_raise_error(self):
        mock_edge_device = MagicMock(spec=EdgeDeviceBase)
        mock_edge_device.id = "mock_device"
        mock_edge_device.name = "Mock Device"
        mock_edge_device.lifespan = SourceValue(2 * u.year)

        mock_edge_need = MagicMock(spec=RecurrentEdgeResourceNeed)
        mock_edge_need.edge_device = mock_edge_device

        mock_edge_function = MagicMock(spec=EdgeFunction)
        mock_edge_function.recurrent_edge_resource_needs = [mock_edge_need]

        usage_span = SourceValue(1 * u.year)
        euj = EdgeUsageJourney("test euj", edge_functions=[mock_edge_function], usage_span=usage_span)

        euj.usage_span = SourceValue(2 * u.year)

    def test_edge_usage_patterns_property_multiple_containers(self):
        """Test edge_usage_patterns property returns all containers."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.name = "Pattern 2"

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])

        self.assertEqual({mock_pattern_1, mock_pattern_2}, set(self.edge_usage_journey.edge_usage_patterns))

    def test_edge_usage_patterns_property_no_containers(self):
        """Test edge_usage_patterns property when no containers are set."""
        self.assertEqual([], self.edge_usage_journey.edge_usage_patterns)

    def test_systems_property_single_pattern(self):
        """Test systems property with single pattern."""
        mock_pattern = MagicMock()
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_pattern.systems = [mock_system_1, mock_system_2]

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern])
        
        self.assertEqual({mock_system_1, mock_system_2}, set(self.edge_usage_journey.systems))

    def test_systems_property_multiple_patterns(self):
        """Test systems property aggregates across multiple patterns."""
        mock_pattern_1 = MagicMock()
        mock_pattern_2 = MagicMock()
        mock_system_1 = MagicMock()
        mock_system_2 = MagicMock()
        mock_system_3 = MagicMock()
        mock_pattern_1.systems = [mock_system_1, mock_system_2]
        mock_pattern_2.systems = [mock_system_2, mock_system_3]  # mock_system_2 appears in both

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])
        
        systems = self.edge_usage_journey.systems
        # Should deduplicate mock_system_2
        self.assertEqual(3, len(systems))
        self.assertIn(mock_system_1, systems)
        self.assertIn(mock_system_2, systems)
        self.assertIn(mock_system_3, systems)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_no_edge_usage_pattern(self):
        """Test that edge_functions returned as dependent objects."""
        self.assertEqual(len(self.edge_usage_journey.edge_usage_patterns), 0)
        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [self.mock_edge_function_1, self.mock_edge_function_2]
        self.assertEqual(expected_objects, dependent_objects)

    def test_modeling_objects_whose_attributes_depend_directly_on_me_with_edge_usage_patterns(self):
        """Test that all edge_usage_patterns are returned as dependent objects when present."""
        mock_pattern_1 = MagicMock()
        mock_pattern_1.name = "Mock Pattern 1"
        mock_pattern_2 = MagicMock()
        mock_pattern_2.name = "Mock Pattern 2"

        set_modeling_obj_containers(self.edge_usage_journey, [mock_pattern_1, mock_pattern_2])

        dependent_objects = self.edge_usage_journey.modeling_objects_whose_attributes_depend_directly_on_me
        expected_objects = [mock_pattern_1, mock_pattern_2]
        self.assertEqual(set(expected_objects), set(dependent_objects))
        self.assertEqual(len(expected_objects), len(dependent_objects))


if __name__ == "__main__":
    unittest.main()