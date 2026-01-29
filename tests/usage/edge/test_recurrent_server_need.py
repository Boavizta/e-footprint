import unittest
from unittest import TestCase
from unittest.mock import MagicMock
from datetime import datetime
import numpy as np
import pytz

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceTimezone
from efootprint.constants.units import u
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed, NegativeServerNeedError
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.usage.job import JobBase
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.utils import set_modeling_obj_containers


class TestRecurrentServerNeed(TestCase):
    def setUp(self):
        self.mock_edge_device = MagicMock(spec=EdgeDevice)
        self.mock_edge_device.name = "Mock Edge Device"
        self.mock_edge_device.id = "mock_device"

        self.mock_job = MagicMock(spec=JobBase)
        self.mock_job.name = "Mock Job"
        self.mock_job.id = "mock_job"

        self.recurrent_volume = ExplainableRecurrentQuantities(
            np.array([2.0] * 168, dtype=np.float32) * u.occurrence, "test recurrent volume")

        self.server_need = RecurrentServerNeed(
            "test server need",
            edge_device=self.mock_edge_device,
            recurrent_volume_per_edge_device=self.recurrent_volume,
            jobs=[self.mock_job])

    def test_modeling_objects_whose_attributes_depend_directly_on_me(self):
        """Test that jobs are returned as dependent objects."""
        self.assertEqual([self.mock_job], self.server_need.modeling_objects_whose_attributes_depend_directly_on_me)

    def test_edge_functions_property_no_containers(self):
        """Test edge_functions returns empty list when no containers."""
        self.assertEqual([], self.server_need.edge_functions)

    def test_edge_functions_property_with_containers(self):
        """Test edge_functions returns containers."""
        mock_function = MagicMock(spec=EdgeFunction)
        set_modeling_obj_containers(self.server_need, [mock_function])
        self.assertEqual([mock_function], self.server_need.edge_functions)

    def test_edge_usage_journeys_property_no_functions(self):
        """Test edge_usage_journeys returns empty list when no functions."""
        self.assertEqual([], self.server_need.edge_usage_journeys)

    def test_edge_usage_journeys_property_with_deduplication(self):
        """Test edge_usage_journeys deduplicates across functions."""
        mock_journey_1 = MagicMock(spec=EdgeUsageJourney)
        mock_journey_2 = MagicMock(spec=EdgeUsageJourney)

        mock_function_1 = MagicMock(spec=EdgeFunction)
        mock_function_1.edge_usage_journeys = [mock_journey_1, mock_journey_2]
        mock_function_2 = MagicMock(spec=EdgeFunction)
        mock_function_2.edge_usage_journeys = [mock_journey_2]

        set_modeling_obj_containers(self.server_need, [mock_function_1, mock_function_2])

        journeys = self.server_need.edge_usage_journeys
        self.assertEqual(2, len(journeys))
        self.assertIn(mock_journey_1, journeys)
        self.assertIn(mock_journey_2, journeys)

    def test_edge_usage_patterns_property_no_journeys(self):
        """Test edge_usage_patterns returns empty list when no journeys."""
        self.assertEqual([], self.server_need.edge_usage_patterns)

    def test_edge_usage_patterns_property_with_deduplication(self):
        """Test edge_usage_patterns deduplicates across journeys."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_2 = MagicMock(spec=EdgeUsagePattern)

        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey]

        set_modeling_obj_containers(self.server_need, [mock_function])

        patterns = self.server_need.edge_usage_patterns
        self.assertEqual(2, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)

    def test_update_validated_recurrent_need_valid_unit(self):
        """Test update_validated_recurrent_need with valid occurrence unit."""
        self.server_need.update_validated_recurrent_need()

        self.assertEqual("test server need validated recurrent need",
                        self.server_need.validated_recurrent_need.label)

    def test_update_validated_recurrent_need_invalid_unit_raises_assertion(self):
        """Test update_validated_recurrent_need raises assertion for invalid unit."""
        invalid_volume = ExplainableRecurrentQuantities(
            np.array([2.0] * 168, dtype=np.float32) * u.GB, "invalid unit volume")

        server_need = RecurrentServerNeed(
            "invalid unit need", self.mock_edge_device, invalid_volume, [self.mock_job])

        with self.assertRaises(AssertionError) as context:
            server_need.update_validated_recurrent_need()

        self.assertIn("invalid unit", str(context.exception))
        self.assertIn("occurrence", str(context.exception))

    def test_update_validated_recurrent_need_negative_values_raises_error(self):
        """Test update_validated_recurrent_need raises NegativeServerNeedError for negative values."""
        negative_volume = ExplainableRecurrentQuantities(
            np.array([-1.0] * 168, dtype=np.float32) * u.occurrence, "negative volume")

        server_need = RecurrentServerNeed(
            "negative need", self.mock_edge_device, negative_volume, [self.mock_job])

        with self.assertRaises(NegativeServerNeedError) as context:
            server_need.update_validated_recurrent_need()

        self.assertIn("negative need", str(context.exception))
        self.assertIn("negative values", str(context.exception))

    def test_update_unitary_hourly_volume_per_usage_pattern(self):
        """Test updating unitary hourly volume for all usage patterns."""
        mock_pattern_1 = MagicMock(spec=EdgeUsagePattern)
        mock_pattern_1.name = "Pattern 1"
        mock_pattern_1.id = "pattern_1"
        start_date_1 = datetime(2023, 1, 1, 0, 0, 0)
        hourly_data_1 = np.array([5.0] * 1000) * u.concurrent
        mock_pattern_1.nb_edge_usage_journeys_in_parallel = ExplainableHourlyQuantities(
            hourly_data_1, start_date_1, "test parallel journeys 1")
        mock_country_1 = MagicMock()
        mock_country_1.timezone = SourceTimezone(pytz.timezone("Europe/Paris"))
        mock_pattern_1.country = mock_country_1

        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.edge_usage_patterns = [mock_pattern_1]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey]

        set_modeling_obj_containers(self.server_need, [mock_function])

        self.server_need.update_unitary_hourly_volume_per_usage_pattern()

        self.assertIn(mock_pattern_1, self.server_need.unitary_hourly_volume_per_usage_pattern)
        result = self.server_need.unitary_hourly_volume_per_usage_pattern[mock_pattern_1]
        self.assertIsInstance(result, ExplainableHourlyQuantities)
        self.assertEqual(len(hourly_data_1), len(result.value))


if __name__ == "__main__":
    unittest.main()