import unittest
from unittest import TestCase
from unittest.mock import MagicMock
from datetime import datetime
import numpy as np
import pytz

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.source_objects import SourceTimezone
from efootprint.constants.units import u
from efootprint.core.usage.edge.recurrent_edge_component_need import (
    RecurrentEdgeComponentNeed, InvalidComponentNeedUnitError, WorkloadOutOfBoundsError)
from efootprint.core.hardware.edge.edge_component import EdgeComponent
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeComponentNeed(TestCase):
    def setUp(self):
        self.mock_edge_component = MagicMock(spec=EdgeComponent)
        self.mock_edge_component.name = "Mock Component"

        self.recurrent_need = ExplainableRecurrentQuantities(
            np.array([0.5] * 168, dtype=np.float32) * u.cpu_core, "test recurrent need")

        self.component_need = RecurrentEdgeComponentNeed(
            "test component need",
            edge_component=self.mock_edge_component,
            recurrent_need=self.recurrent_need
        )

    def test_init(self):
        """Test RecurrentEdgeComponentNeed initialization."""
        self.assertEqual("test component need", self.component_need.name)
        self.assertEqual(self.mock_edge_component, self.component_need.edge_component)
        self.assertEqual("test component need recurrent need", self.component_need.recurrent_need.label)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that edge_component is returned as dependent object."""
        dependent_objects = self.component_need.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_component], dependent_objects)

    def test_recurrent_edge_device_needs_property(self):
        """Test recurrent_edge_device_needs property returns containers."""
        self.assertEqual([], self.component_need.recurrent_edge_device_needs)

        mock_device_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        set_modeling_obj_containers(self.component_need, [mock_device_need])

        self.assertEqual([mock_device_need], self.component_need.recurrent_edge_device_needs)

    def test_edge_device_property_no_device_needs(self):
        """Test edge_device property when no device needs exist."""
        self.assertIsNone(self.component_need.edge_device)

    def test_edge_device_property_with_device_need(self):
        """Test edge_device property returns device from first device need."""
        mock_edge_device = MagicMock(spec=EdgeDevice)
        mock_device_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need.edge_device = mock_edge_device

        set_modeling_obj_containers(self.component_need, [mock_device_need])

        self.assertEqual(mock_edge_device, self.component_need.edge_device)

    def test_edge_functions_property_no_device_needs(self):
        """Test edge_functions property when no device needs exist."""
        self.assertEqual([], self.component_need.edge_functions)

    def test_edge_functions_property_multiple_device_needs_with_deduplication(self):
        """Test edge_functions property deduplicates across device needs."""
        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_3 = MagicMock(spec=EdgeFunction)

        mock_device_need_1 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need_1.edge_functions = [mock_function_1, mock_function_2]

        mock_device_need_2 = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need_2.edge_functions = [mock_function_2, mock_function_3]

        set_modeling_obj_containers(self.component_need, [mock_device_need_1, mock_device_need_2])

        functions = self.component_need.edge_functions
        self.assertEqual(3, len(functions))
        self.assertIn(mock_function_1, functions)
        self.assertIn(mock_function_2, functions)
        self.assertIn(mock_function_3, functions)

    def test_edge_usage_journeys_property_no_functions(self):
        """Test edge_usage_journeys property when no functions exist."""
        self.assertEqual([], self.component_need.edge_usage_journeys)

    def test_edge_usage_journeys_property_multiple_functions_with_deduplication(self):
        """Test edge_usage_journeys property deduplicates across functions."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_3 = MagicMock(spec=EdgeUsageJourney)

        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]

        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.edge_usage_journeys = [mock_journey_2, mock_journey_3]

        mock_device_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need.edge_functions = [mock_function_1, mock_function_2]

        set_modeling_obj_containers(self.component_need, [mock_device_need])

        journeys = self.component_need.edge_usage_journeys
        self.assertEqual(3, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)
        self.assertIn(mock_journey_3, journeys)

    def test_edge_usage_patterns_property_no_journeys(self):
        """Test edge_usage_patterns property when no journeys exist."""
        self.assertEqual([], self.component_need.edge_usage_patterns)


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

        mock_device_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need.edge_functions = [mock_function]

        set_modeling_obj_containers(self.component_need, [mock_device_need])

        patterns = self.component_need.edge_usage_patterns
        self.assertEqual(3, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)
        self.assertIn(mock_pattern_3, patterns)

    def test_assert_recurrent_workload_is_between_0_and_1_valid(self):
        """Test workload validation with valid values between 0 and 1."""
        valid_workload = ExplainableRecurrentQuantities(
            np.array([0.3, 0.5, 0.8] * 56, dtype=np.float32) * u.concurrent, "valid workload")

        RecurrentEdgeComponentNeed.assert_recurrent_workload_is_between_0_and_1(valid_workload, "test")

    def test_assert_recurrent_workload_is_between_0_and_1_boundary_values(self):
        """Test workload validation with boundary values 0 and 1."""
        boundary_workload = ExplainableRecurrentQuantities(
            np.array([0.0, 1.0, 0.5] * 56, dtype=np.float32) * u.concurrent, "boundary workload")

        RecurrentEdgeComponentNeed.assert_recurrent_workload_is_between_0_and_1(boundary_workload, "test")

    def test_assert_recurrent_workload_is_between_0_and_1_negative_values(self):
        """Test workload validation raises error for negative values."""
        invalid_workload = ExplainableRecurrentQuantities(
            np.array([-0.1, 0.5, 0.8] * 56, dtype=np.float32) * u.concurrent, "invalid workload")

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            RecurrentEdgeComponentNeed.assert_recurrent_workload_is_between_0_and_1(invalid_workload, "test workload")

        self.assertIn("test workload", str(context.exception))
        self.assertIn("values outside the valid range [0, 1]", str(context.exception))

    def test_assert_recurrent_workload_is_between_0_and_1_values_above_1(self):
        """Test workload validation raises error for values above 1."""
        invalid_workload = ExplainableRecurrentQuantities(
            np.array([0.5, 1.2, 0.8] * 56, dtype=np.float32) * u.concurrent, "invalid workload")

        with self.assertRaises(WorkloadOutOfBoundsError) as context:
            RecurrentEdgeComponentNeed.assert_recurrent_workload_is_between_0_and_1(invalid_workload, "test workload")

        self.assertIn("test workload", str(context.exception))
        self.assertIn("values outside the valid range [0, 1]", str(context.exception))

    def test_update_validated_recurrent_need_valid_unit(self):
        """Test update_validated_recurrent_need with valid unit."""
        self.mock_edge_component.expected_need_units.return_value = [u.cpu_core]

        self.component_need.update_validated_recurrent_need()

        self.assertEqual("Validated recurrent need of test component need",
                        self.component_need.validated_recurrent_need.label)

    def test_update_validated_recurrent_need_invalid_unit(self):
        """Test update_validated_recurrent_need raises error for invalid unit."""
        self.mock_edge_component.expected_need_units.return_value = [u.GB]

        with self.assertRaises(InvalidComponentNeedUnitError) as context:
            self.component_need.update_validated_recurrent_need()

        self.assertIn("Mock Component", str(context.exception))
        self.assertIn("incompatible unit", str(context.exception))

    def test_update_validated_recurrent_need_workload_validation(self):
        """Test update_validated_recurrent_need validates workload range for concurrent units."""
        self.mock_edge_component.expected_need_units.return_value = [u.concurrent]

        valid_workload = ExplainableRecurrentQuantities(
            np.array([0.5] * 168, dtype=np.float32) * u.concurrent, "valid workload")

        workload_component_need = RecurrentEdgeComponentNeed(
            "workload need", self.mock_edge_component, valid_workload)

        workload_component_need.update_validated_recurrent_need()

        self.assertEqual("Validated recurrent need of workload need",
                        workload_component_need.validated_recurrent_need.label)

    def test_update_validated_recurrent_need_workload_out_of_bounds(self):
        """Test update_validated_recurrent_need raises error for out-of-bounds workload."""
        self.mock_edge_component.expected_need_units.return_value = [u.concurrent]

        invalid_workload = ExplainableRecurrentQuantities(
            np.array([1.5] * 168, dtype=np.float32) * u.concurrent, "invalid workload")

        workload_component_need = RecurrentEdgeComponentNeed(
            "workload need", self.mock_edge_component, invalid_workload)

        with self.assertRaises(WorkloadOutOfBoundsError):
            workload_component_need.update_validated_recurrent_need()

    def test_update_unitary_hourly_need_per_usage_pattern(self):
        """Test updating unitary hourly need for all usage patterns."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_1.id = "pattern_1"
        start_date_1 = datetime(2023, 1, 1, 0, 0, 0)
        hourly_data_1 = np.array([5.0] * 10000) * u.concurrent
        mock_pattern_1.nb_edge_usage_journeys_in_parallel = ExplainableHourlyQuantities(
            hourly_data_1, start_date_1, "test parallel journeys 1")

        mock_country_1 = MagicMock()
        mock_country_1.timezone = SourceTimezone(pytz.timezone("Europe/Paris"))
        mock_pattern_1.country = mock_country_1

        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2.name = "Pattern 2"

        start_date_2 = datetime(2023, 1, 8, 0, 0, 0)
        hourly_data_2 = np.array([10.0] * 1000) * u.concurrent
        mock_pattern_2.nb_edge_usage_journeys_in_parallel = ExplainableHourlyQuantities(
            hourly_data_2, start_date_2, "test parallel journeys 2")
        mock_pattern_2.id = "pattern_2"
        mock_country_2 = MagicMock()
        mock_country_2.timezone = SourceTimezone(pytz.timezone("Europe/Paris"))
        mock_pattern_2.country = mock_country_2

        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey]

        mock_device_need = MagicMock(spec=RecurrentEdgeDeviceNeed)
        mock_device_need.edge_functions = [mock_function]

        set_modeling_obj_containers(self.component_need, [mock_device_need])

        self.component_need.update_unitary_hourly_need_per_usage_pattern()

        self.assertIn(mock_pattern_1, self.component_need.unitary_hourly_need_per_usage_pattern)
        self.assertIn(mock_pattern_2, self.component_need.unitary_hourly_need_per_usage_pattern)
        result_1 = self.component_need.unitary_hourly_need_per_usage_pattern[mock_pattern_1]
        self.assertIsInstance(result_1, ExplainableHourlyQuantities)
        self.assertEqual(len(hourly_data_1), len(result_1.value))
        result_2 = self.component_need.unitary_hourly_need_per_usage_pattern[mock_pattern_2]
        self.assertIsInstance(result_2, ExplainableHourlyQuantities)
        self.assertEqual(len(hourly_data_2), len(result_2.value))


if __name__ == "__main__":
    unittest.main()