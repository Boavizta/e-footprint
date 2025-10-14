import unittest
from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues
from efootprint.core.usage.recurrent_edge_workload import RecurrentEdgeWorkload
from efootprint.core.usage.edge_function import EdgeFunction
from efootprint.core.usage.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.hardware.edge_hardware import EdgeHardware
from efootprint.constants.units import u
from tests.utils import set_modeling_obj_containers


class TestRecurrentEdgeWorkload(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_edge_hardware = MagicMock(spec=EdgeHardware)
        self.mock_edge_hardware.id = "mock_hardware"
        self.mock_edge_hardware.name = "Mock Hardware"

        self.recurrent_workload = SourceRecurrentValues(
            Quantity(np.array([3.5] * 168, dtype=np.float32), u.GB))

        self.edge_workload = RecurrentEdgeWorkload(
            "test edge workload",
            edge_hardware=self.mock_edge_hardware,
            recurrent_workload=self.recurrent_workload)

    def test_init(self):
        """Test RecurrentEdgeWorkload initialization."""
        self.assertEqual("test edge workload", self.edge_workload.name)
        self.assertEqual(self.mock_edge_hardware, self.edge_workload.edge_hardware)
        self.assertIs(self.recurrent_workload, self.edge_workload.recurrent_workload)
        self.assertIsInstance(self.edge_workload.unitary_hourly_workload_per_usage_pattern, ExplainableObjectDict)

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test modeling_objects_whose_attributes_depend_directly_on_me returns edge_hardware."""
        dependent_objects = self.edge_workload.modeling_objects_whose_attributes_depend_directly_on_me
        self.assertEqual([self.mock_edge_hardware], dependent_objects)

    def test_update_dict_element_in_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_dict_element_in_unitary_hourly_workload_per_usage_pattern method."""
        mock_pattern = MagicMock(spec=EdgeUsagePattern)
        mock_pattern.name = "Test Pattern"
        mock_nb_euj_in_parallel = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country = MagicMock()
        mock_timezone = MagicMock()

        mock_pattern.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel
        mock_pattern.country = mock_country
        mock_country.timezone = mock_timezone

        expected_result = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result.set_label = MagicMock(return_value=expected_result)

        self.edge_workload.recurrent_workload.generate_hourly_quantities_over_timespan = MagicMock(
            return_value=expected_result)

        self.edge_workload.update_dict_element_in_unitary_hourly_workload_per_usage_pattern(mock_pattern)

        self.edge_workload.recurrent_workload.generate_hourly_quantities_over_timespan.assert_called_once_with(
            mock_nb_euj_in_parallel, mock_timezone)

        self.assertDictEqual(
            {mock_pattern: expected_result}, self.edge_workload.unitary_hourly_workload_per_usage_pattern)

    def test_update_unitary_hourly_workload_per_usage_pattern(self):
        """Test update_unitary_hourly_workload_per_usage_pattern method."""
        mock_function = MagicMock(spec=EdgeFunction)
        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_2.name = "Pattern 2"

        mock_nb_euj_in_parallel_1 = MagicMock(spec=ExplainableHourlyQuantities)
        mock_nb_euj_in_parallel_2 = MagicMock(spec=ExplainableHourlyQuantities)
        mock_country_1 = MagicMock()
        mock_country_2 = MagicMock()
        mock_timezone_1 = MagicMock()
        mock_timezone_2 = MagicMock()

        mock_pattern_1.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel_1
        mock_pattern_1.country = mock_country_1
        mock_country_1.timezone = mock_timezone_1
        mock_pattern_2.nb_edge_usage_journeys_in_parallel = mock_nb_euj_in_parallel_2
        mock_pattern_2.country = mock_country_2
        mock_country_2.timezone = mock_timezone_2

        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        mock_function.edge_usage_journeys = [mock_journey]

        expected_result_1 = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result_2 = MagicMock(spec=ExplainableHourlyQuantities)
        expected_result_1.set_label = MagicMock(return_value=expected_result_1)
        expected_result_2.set_label = MagicMock(return_value=expected_result_2)

        mapping = {mock_nb_euj_in_parallel_1: expected_result_1, mock_nb_euj_in_parallel_2: expected_result_2}
        self.edge_workload.recurrent_workload.generate_hourly_quantities_over_timespan = MagicMock(
            side_effect=lambda x, tz: mapping[x])

        set_modeling_obj_containers(self.edge_workload, [mock_function])

        self.edge_workload.update_unitary_hourly_workload_per_usage_pattern()

        self.assertEqual(
            2, self.edge_workload.recurrent_workload.generate_hourly_quantities_over_timespan.call_count)
        self.assertDictEqual(
            {mock_pattern_1: expected_result_1, mock_pattern_2: expected_result_2},
            self.edge_workload.unitary_hourly_workload_per_usage_pattern
        )


if __name__ == "__main__":
    unittest.main()