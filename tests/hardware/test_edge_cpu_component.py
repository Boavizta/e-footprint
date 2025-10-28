import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge_cpu_component import EdgeCPUComponent
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestEdgeCPUComponent(TestCase):
    def setUp(self):
        self.cpu_component = EdgeCPUComponent(
            name="Test CPU",
            carbon_footprint_fabrication=SourceValue(20 * u.kg),
            power=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power=SourceValue(10 * u.W),
            compute=SourceValue(8 * u.cpu_core),
            base_compute_consumption=SourceValue(1 * u.cpu_core)
        )
        self.cpu_component.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeCPUComponent initialization."""
        self.assertEqual("Test CPU", self.cpu_component.name)
        self.assertEqual(20 * u.kg, self.cpu_component.carbon_footprint_fabrication.value)
        self.assertEqual(50 * u.W, self.cpu_component.power.value)
        self.assertEqual(5 * u.year, self.cpu_component.lifespan.value)
        self.assertEqual(10 * u.W, self.cpu_component.idle_power.value)
        self.assertEqual(8 * u.cpu_core, self.cpu_component.compute.value)
        self.assertEqual(1 * u.cpu_core, self.cpu_component.base_compute_consumption.value)

    def test_expected_need_units(self):
        """Test expected_need_units returns correct units."""
        expected_units = self.cpu_component.expected_need_units()
        self.assertIn(u.cpu_core, expected_units)

    def test_update_available_compute_per_instance(self):
        """Test update_available_compute_per_instance calculation."""
        self.cpu_component.update_available_compute_per_instance()

        # available = compute - base_compute_consumption = 8 - 1 = 7 cpu_core
        expected_value = 7
        self.assertAlmostEqual(
            expected_value, self.cpu_component.available_compute_per_instance.value.magnitude, places=5)
        self.assertEqual(u.cpu_core, self.cpu_component.available_compute_per_instance.value.units)
        self.assertIn("Available compute per Test CPU instance",
                     self.cpu_component.available_compute_per_instance.label)

    def test_update_available_compute_per_instance_insufficient_capacity(self):
        """Test update_available_compute_per_instance raises error when capacity is insufficient."""
        self.cpu_component.base_compute_consumption = SourceValue(10 * u.cpu_core)

        with self.assertRaises(InsufficientCapacityError) as context:
            self.cpu_component.update_available_compute_per_instance()

        self.assertEqual("compute", context.exception.capacity_type)
        self.assertEqual(self.cpu_component, context.exception.overloaded_object)

    def test_update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern calculation."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        mock_need_1 = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need_2 = MagicMock(spec=RecurrentEdgeComponentNeed)

        compute_need_1 = create_source_hourly_values_from_list([0.5, 1.0, 1.5], pint_unit=u.cpu_core)
        compute_need_2 = create_source_hourly_values_from_list([1.0, 0.5, 2.0], pint_unit=u.cpu_core)

        mock_need_1.unitary_hourly_need_per_usage_pattern = {mock_pattern: compute_need_1}
        mock_need_2.unitary_hourly_need_per_usage_pattern = {mock_pattern: compute_need_2}
        mock_need_1.edge_usage_patterns = [mock_pattern]
        mock_need_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.cpu_component, [mock_need_1, mock_need_2])

        self.cpu_component.update_available_compute_per_instance()
        self.cpu_component.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(mock_pattern)

        expected_values = [1.5, 1.5, 3.5]  # Sum of both needs
        result = self.cpu_component.unitary_hourly_compute_need_per_usage_pattern[mock_pattern]
        self.assertEqual(expected_values, result.value_as_float_list)
        self.assertEqual(u.cpu_core, result.unit)
        self.assertIn("Test CPU hourly compute need for Test Pattern", result.label)

    def test_update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern_insufficient_capacity(self):
        """Test update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern raises error when capacity is exceeded."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        mock_need = MagicMock(spec=RecurrentEdgeComponentNeed)
        compute_need = create_source_hourly_values_from_list([0.5, 1.0, 10.0], pint_unit=u.cpu_core)  # Peak of 10.0 cpu_core
        mock_need.unitary_hourly_need_per_usage_pattern = {mock_pattern: compute_need}
        mock_need.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.cpu_component, [mock_need])

        self.cpu_component.update_available_compute_per_instance()

        with self.assertRaises(InsufficientCapacityError) as context:
            self.cpu_component.update_dict_element_in_unitary_hourly_compute_need_per_usage_pattern(mock_pattern)

        self.assertEqual("compute", context.exception.capacity_type)
        self.assertEqual(self.cpu_component, context.exception.overloaded_object)

    def test_update_dict_element_in_unitary_power_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_power_per_usage_pattern calculation based on compute workload."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_pattern.id = "test_pattern_id"

        compute_need = create_source_hourly_values_from_list([0, 4, 7], pint_unit=u.cpu_core)
        self.cpu_component.unitary_hourly_compute_need_per_usage_pattern = {mock_pattern: compute_need}

        self.cpu_component.update_available_compute_per_instance()
        self.cpu_component.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)

        # Workload ratios: (compute_need + base_compute_consumption) / compute
        # = ([0, 4, 7] + 1) / 8
        # = [1/8, 5/8, 8/8]
        # Power: idle_power + (power - idle_power) * workload_ratio
        # = 10 + (50-10) * [1/8, 5/8, 1]
        # = 10 + 40 * [1/8, 5/8, 1]
        # = [15, 35, 50]
        expected_values = [15, 35, 50]
        result = self.cpu_component.unitary_power_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_values, result.value.to(u.W).magnitude))
        self.assertIn("Test CPU unitary power for Test Pattern", result.label)


if __name__ == "__main__":
    unittest.main()
