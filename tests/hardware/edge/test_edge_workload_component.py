import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.usage.edge.recurrent_edge_component_need import (
    RecurrentEdgeComponentNeed,
    WorkloadOutOfBoundsError,
)
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeWorkloadComponent(TestCase):
    def setUp(self):
        self.appliance_component = EdgeWorkloadComponent(
            name="Test Appliance",
            carbon_footprint_fabrication_per_unit=SourceValue(100 * u.kg),
            power_per_unit=SourceValue(50 * u.W),
            lifespan=SourceValue(5 * u.year),
            idle_power_per_unit=SourceValue(5 * u.W)
        )
        self.appliance_component.trigger_modeling_updates = False
        self.appliance_component.update_carbon_footprint_fabrication()
        self.appliance_component.update_power()
        self.appliance_component.update_idle_power()

    def test_init(self):
        """Test EdgeWorkloadComponent initialization."""
        self.assertEqual("Test Appliance", self.appliance_component.name)
        self.assertEqual(100 * u.kg, self.appliance_component.carbon_footprint_fabrication_per_unit.value)
        self.assertEqual(100 * u.kg, self.appliance_component.carbon_footprint_fabrication.value)
        self.assertEqual(50 * u.W, self.appliance_component.power_per_unit.value)
        self.assertEqual(50 * u.W, self.appliance_component.power.value)
        self.assertEqual(5 * u.year, self.appliance_component.lifespan.value)
        self.assertEqual(5 * u.W, self.appliance_component.idle_power_per_unit.value)
        self.assertEqual(5 * u.W, self.appliance_component.idle_power.value)
        self.assertEqual(1 * u.dimensionless, self.appliance_component.nb_of_units.value)

    def test_update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_workload_per_usage_pattern aggregates workloads."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        mock_need_1 = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need_2 = MagicMock(spec=RecurrentEdgeComponentNeed)

        workload_1 = create_source_hourly_values_from_list([0.2, 0.3], pint_unit=u.concurrent)
        workload_2 = create_source_hourly_values_from_list([0.1, 0.15], pint_unit=u.concurrent)

        mock_need_1.unitary_hourly_need_per_usage_pattern = {mock_pattern: workload_1}
        mock_need_2.unitary_hourly_need_per_usage_pattern = {mock_pattern: workload_2}
        mock_need_1.edge_usage_patterns = [mock_pattern]
        mock_need_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.appliance_component, [mock_need_1, mock_need_2])

        self.appliance_component.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(mock_pattern)

        expected_values = [0.3, 0.45]  # Sum of both needs
        result = self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern]
        self.assertTrue(np.allclose(expected_values, result.value_as_float_list))
        self.assertEqual(u.concurrent, result.unit)
        self.assertIn("Hourly workload for Test Pattern", result.label)

    def test_update_dict_element_in_unitary_hourly_workload_per_usage_pattern_raises_when_sum_exceeds_one(self):
        """Test update_dict_element_in_unitary_hourly_workload_per_usage_pattern raises when aggregated workload exceeds 1."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern")

        mock_need_1 = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need_2 = MagicMock(spec=RecurrentEdgeComponentNeed)

        workload_1 = create_source_hourly_values_from_list([0.7, 0.4], pint_unit=u.concurrent)
        workload_2 = create_source_hourly_values_from_list([0.2, 0.7], pint_unit=u.concurrent)

        mock_need_1.unitary_hourly_need_per_usage_pattern = {mock_pattern: workload_1}
        mock_need_2.unitary_hourly_need_per_usage_pattern = {mock_pattern: workload_2}
        mock_need_1.edge_usage_patterns = [mock_pattern]
        mock_need_2.edge_usage_patterns = [mock_pattern]

        set_modeling_obj_containers(self.appliance_component, [mock_need_1, mock_need_2])

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            self.appliance_component.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(mock_pattern)

        self.assertIn("aggregated workload", str(context.exception).lower())

    def test_update_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_unitary_hourly_workload_per_usage_pattern updates all patterns."""
        mock_pattern1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        mock_pattern2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")

        mock_need = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need.edge_usage_patterns = [mock_pattern1, mock_pattern2]

        workload_values1 = create_source_hourly_values_from_list([0.2, 0.3], pint_unit=u.concurrent)
        workload_values2 = create_source_hourly_values_from_list([0.4, 0.5], pint_unit=u.concurrent)

        mock_need.unitary_hourly_need_per_usage_pattern = {
            mock_pattern1: workload_values1,
            mock_pattern2: workload_values2
        }

        set_modeling_obj_containers(self.appliance_component, [mock_need])

        self.appliance_component.update_unitary_hourly_workload_per_usage_pattern()

        self.assertIn(mock_pattern1, self.appliance_component.unitary_hourly_workload_per_usage_pattern)
        self.assertIn(mock_pattern2, self.appliance_component.unitary_hourly_workload_per_usage_pattern)
        result1 = self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern1]
        result2 = self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern2]
        self.assertTrue(np.allclose([0.2, 0.3], result1.value_as_float_list))
        self.assertTrue(np.allclose([0.4, 0.5], result2.value_as_float_list))

    def test_update_dict_element_in_unitary_power_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_power_per_usage_pattern calculates power based on workload."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern", id="test_pattern")

        workload_values = create_source_hourly_values_from_list([0.0, 0.5, 1.0], pint_unit=u.concurrent)
        self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern] = workload_values

        self.appliance_component.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)

        result = self.appliance_component.unitary_power_per_usage_pattern[mock_pattern]
        # Power = idle_power + (power - idle_power) * workload
        # = 5 + (50 - 5) * [0.0, 0.5, 1.0]
        # = 5 + 45 * [0.0, 0.5, 1.0]
        # = [5, 27.5, 50]
        expected_values = [5, 27.5, 50]
        self.assertTrue(np.allclose(expected_values, result.value.to(u.W).magnitude))
        self.assertIn("Unitary power for Test Pattern", result.label)

    def test_update_dict_element_in_unitary_power_with_empty_workload(self):
        """Test power calculation with EmptyExplainableObject workload."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Test Pattern", id="test_pattern")

        self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern] = EmptyExplainableObject()

        self.appliance_component.update_dict_element_in_unitary_power_per_usage_pattern(mock_pattern)

        result = self.appliance_component.unitary_power_per_usage_pattern[mock_pattern]
        # With empty workload, power should be idle_power
        self.assertEqual(5 * u.W, result.value)
        self.assertIn("Unitary power for Test Pattern", result.label)

    def test_update_unitary_power_per_usage_pattern(self):
        """Test update_unitary_power_per_usage_pattern updates all patterns."""
        mock_pattern1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        mock_pattern2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")

        workload_values1 = create_source_hourly_values_from_list([0.2], pint_unit=u.concurrent)
        workload_values2 = create_source_hourly_values_from_list([0.5], pint_unit=u.concurrent)

        self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern1] = workload_values1
        self.appliance_component.unitary_hourly_workload_per_usage_pattern[mock_pattern2] = workload_values2

        mock_need = MagicMock(spec=RecurrentEdgeComponentNeed)
        mock_need.edge_usage_patterns = [mock_pattern1, mock_pattern2]
        set_modeling_obj_containers(self.appliance_component, [mock_need])

        self.appliance_component.update_unitary_power_per_usage_pattern()

        self.assertIn(mock_pattern1, self.appliance_component.unitary_power_per_usage_pattern)
        self.assertIn(mock_pattern2, self.appliance_component.unitary_power_per_usage_pattern)
        result1 = self.appliance_component.unitary_power_per_usage_pattern[mock_pattern1]
        result2 = self.appliance_component.unitary_power_per_usage_pattern[mock_pattern2]
        expected_values1 = [5 + 45 * 0.2]  # = 14W
        expected_values2 = [5 + 45 * 0.5]  # = 27.5W
        self.assertTrue(np.allclose(expected_values1, result1.value_as_float_list))
        self.assertTrue(np.allclose(expected_values2, result2.value_as_float_list))


if __name__ == "__main__":
    unittest.main()
