import unittest
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge_appliance import EdgeAppliance
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload
from tests.utils import set_modeling_obj_containers


class TestEdgeAppliance(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.edge_device = EdgeAppliance(
            "test edge appliance",
            carbon_footprint_fabrication=SourceValue(100 * u.kg),
            power=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power=SourceValue(5 * u.W))

    def test_init(self):
        """Test EdgeAppliance initialization."""
        self.assertEqual("test edge appliance", self.edge_device.name)
        self.assertEqual(100 * u.kg, self.edge_device.carbon_footprint_fabrication.value)
        self.assertEqual(50 * u.W, self.edge_device.power.value)
        self.assertEqual(5 * u.year, self.edge_device.lifespan.value)
        self.assertEqual(5 * u.W, self.edge_device.idle_power.value)
        self.assertIsInstance(self.edge_device.unitary_hourly_workload_per_usage_pattern, ExplainableObjectDict)

    def test_edge_workloads_property(self):
        """Test edge_workloads property returns modeling_obj_containers."""
        mock_workload1 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload2 = MagicMock(spec=RecurrentEdgeWorkload)

        set_modeling_obj_containers(self.edge_device, [mock_workload1, mock_workload2])

        self.assertEqual({mock_workload1, mock_workload2}, set(self.edge_device.edge_workloads))

    def test_edge_usage_patterns_property(self):
        """Test edge_usage_patterns property aggregates patterns from workloads."""
        mock_pattern1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern1.id = "pattern1"
        mock_pattern2.id = "pattern2"

        mock_workload1 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload2 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload1.edge_usage_patterns = [mock_pattern1]
        mock_workload2.edge_usage_patterns = [mock_pattern2]

        set_modeling_obj_containers(self.edge_device, [mock_workload1, mock_workload2])

        patterns = self.edge_device.edge_usage_patterns
        self.assertEqual(2, len(patterns))
        self.assertIn(mock_pattern1, patterns)
        self.assertIn(mock_pattern2, patterns)

    def test_update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_workload_per_usage_pattern aggregates workloads."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_workload1 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload2 = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload1.edge_usage_patterns = [mock_pattern]
        mock_workload2.edge_usage_patterns = [mock_pattern]

        workload_values1 = create_source_hourly_values_from_list([0.2, 0.3], pint_unit=u.dimensionless)
        workload_values2 = create_source_hourly_values_from_list([0.1, 0.15], pint_unit=u.dimensionless)

        mock_workload1.unitary_hourly_workload_per_usage_pattern = {mock_pattern: workload_values1}
        mock_workload2.unitary_hourly_workload_per_usage_pattern = {mock_pattern: workload_values2}

        set_modeling_obj_containers(self.edge_device, [mock_workload1, mock_workload2])

        self.edge_device.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(mock_pattern)

        result = self.edge_device.unitary_hourly_workload_per_usage_pattern[mock_pattern]
        expected_values = [0.3, 0.45]
        self.assertTrue(np.allclose(expected_values, result.value.magnitude))
        self.assertEqual("test edge appliance hourly workload for Test Pattern", result.label)

    def test_update_dict_element_in_unitary_hourly_workload_exceeds_capacity(self):
        """Test that workload exceeding 100% raises InsufficientCapacityError."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"

        mock_workload = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload.edge_usage_patterns = [mock_pattern]

        # Workload exceeding 100%
        workload_values = create_source_hourly_values_from_list([0.8, 1.2], pint_unit=u.dimensionless)

        mock_workload.unitary_hourly_workload_per_usage_pattern = {mock_pattern: workload_values}

        set_modeling_obj_containers(self.edge_device, [mock_workload])

        with self.assertRaises(InsufficientCapacityError) as context:
            self.edge_device.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(mock_pattern)

        self.assertIn("workload capacity", str(context.exception))

    def test_update_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_unitary_hourly_workload_per_usage_pattern updates all patterns."""
        mock_pattern1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern1.name = "Pattern 1"
        mock_pattern2.name = "Pattern 2"
        mock_pattern1.id = "pattern1"
        mock_pattern2.id = "pattern2"

        mock_workload = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload.edge_usage_patterns = [mock_pattern1, mock_pattern2]

        workload_values1 = create_source_hourly_values_from_list([0.2, 0.3], pint_unit=u.dimensionless)
        workload_values2 = create_source_hourly_values_from_list([0.4, 0.5], pint_unit=u.dimensionless)

        mock_workload.unitary_hourly_workload_per_usage_pattern = {
            mock_pattern1: workload_values1,
            mock_pattern2: workload_values2
        }

        set_modeling_obj_containers(self.edge_device, [mock_workload])

        self.edge_device.update_unitary_hourly_workload_per_usage_pattern()

        self.assertIn(mock_pattern1, self.edge_device.unitary_hourly_workload_per_usage_pattern)
        self.assertIn(mock_pattern2, self.edge_device.unitary_hourly_workload_per_usage_pattern)
        result1 = self.edge_device.unitary_hourly_workload_per_usage_pattern[mock_pattern1]
        result2 = self.edge_device.unitary_hourly_workload_per_usage_pattern[mock_pattern2]
        self.assertTrue(np.allclose([0.2, 0.3], result1.value.magnitude))
        self.assertTrue(np.allclose([0.4, 0.5], result2.value.magnitude))

    def test_update_dict_element_in_unitary_power_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_power_per_usage_pattern calculates power based on workload."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern"

        workload_values = create_source_hourly_values_from_list([0.0, 0.5, 1.0], pint_unit=u.dimensionless)
        self.edge_device.unitary_hourly_workload_per_usage_pattern[mock_pattern] = workload_values

        self.edge_device.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)

        result = self.edge_device.unitary_power_per_usage_pattern[mock_pattern]
        # Power = idle_power + (power - idle_power) * workload
        # = 5 + (50 - 5) * [0.0, 0.5, 1.0]
        # = 5 + 45 * [0.0, 0.5, 1.0]
        # = [5, 27.5, 50]
        expected_values = [5, 27.5, 50]
        self.assertTrue(np.allclose(expected_values, result.value.to(u.W).magnitude))
        self.assertEqual("test edge appliance unitary power for Test Pattern", result.label)

    def test_update_unitary_power_per_usage_pattern(self):
        """Test update_unitary_power_per_usage_pattern updates all patterns."""
        mock_pattern1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern1.name = "Pattern 1"
        mock_pattern2.name = "Pattern 2"
        mock_pattern1.id = "pattern1"
        mock_pattern2.id = "pattern2"

        workload_values1 = create_source_hourly_values_from_list([0.2], pint_unit=u.dimensionless)
        workload_values2 = create_source_hourly_values_from_list([0.5], pint_unit=u.dimensionless)

        self.edge_device.unitary_hourly_workload_per_usage_pattern = ExplainableObjectDict({
            mock_pattern1: workload_values1,
            mock_pattern2: workload_values2
        })

        mock_workload = MagicMock(spec=RecurrentEdgeWorkload)
        mock_workload.edge_usage_patterns = [mock_pattern1, mock_pattern2]
        set_modeling_obj_containers(self.edge_device, [mock_workload])

        self.edge_device.update_unitary_power_per_usage_pattern()

        self.assertIn(mock_pattern1, self.edge_device.unitary_power_per_usage_pattern)
        self.assertIn(mock_pattern2, self.edge_device.unitary_power_per_usage_pattern)
        result1 = self.edge_device.unitary_power_per_usage_pattern[mock_pattern1]
        result2 = self.edge_device.unitary_power_per_usage_pattern[mock_pattern2]
        expected_values1 = [5 + 45 * 0.2]  # = 14W
        expected_values2 = [5 + 45 * 0.5]  # = 27.5W
        self.assertTrue(np.allclose(expected_values1, result1.value.to(u.W).magnitude))
        self.assertTrue(np.allclose(expected_values2, result2.value.to(u.W).magnitude))

    def test_update_dict_element_in_unitary_power_with_empty_workload(self):
        """Test power calculation with EmptyExplainableObject workload."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern"

        self.edge_device.unitary_hourly_workload_per_usage_pattern[mock_pattern] = EmptyExplainableObject()

        self.edge_device.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)

        result = self.edge_device.unitary_power_per_usage_pattern[mock_pattern]
        # With empty workload, power should be idle_power + (power - idle_power) * EmptyExplainableObject()
        # which equals idle_power = 5W
        self.assertIsInstance(result, ExplainableQuantity)
        self.assertEqual(5 * u.W, result.value)


if __name__ == "__main__":
    unittest.main()