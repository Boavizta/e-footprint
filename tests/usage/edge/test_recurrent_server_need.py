import unittest
from unittest import TestCase
from unittest.mock import MagicMock
from datetime import datetime
import numpy as np
import pytz

from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.abstract_modeling_classes.source_objects import SourceTimezone
from efootprint.constants.units import u
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_device_group import EdgeDeviceGroup
from efootprint.core.usage.job import JobBase
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers
from tests.utils import recompute_attribute


class TestRecurrentServerNeed(TestCase):
    def setUp(self):
        self.mock_edge_device = MagicMock(spec=EdgeDevice)
        self.mock_edge_device.name = "Mock Edge Device"
        self.mock_edge_device.id = "mock_device"
        self.mock_edge_device.total_nb_of_units = ExplainableQuantity(1 * u.dimensionless, "one unit")

        self.mock_job = create_mod_obj_mock(JobBase, name="Mock Job", id="mock_job")

        self.recurrent_volume = ExplainableRecurrentQuantities(
            np.array([2.0] * 168, dtype=np.float32) * u.occurrence, "test recurrent volume")

        self.server_need = RecurrentServerNeed(
            "test server need",
            edge_device=self.mock_edge_device,
            recurrent_volume_per_edge_device=self.recurrent_volume,
            jobs=[self.mock_job])


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
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2")

        mock_journey = MagicMock(spec=EdgeUsageJourney)
        mock_journey.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        mock_function = MagicMock(spec=EdgeFunction)
        mock_function.edge_usage_journeys = [mock_journey]

        set_modeling_obj_containers(self.server_need, [mock_function])

        patterns = self.server_need.edge_usage_patterns
        self.assertEqual(2, len(patterns))
        self.assertIn(mock_pattern_1, patterns)
        self.assertIn(mock_pattern_2, patterns)

    def test_update_recurrent_need_validation_valid_unit(self):
        """Test update_recurrent_need_validation with valid occurrence unit."""
        recompute_attribute(self.server_need, "recurrent_need_validation")

        self.assertEqual("Validated recurrent need",
                        self.server_need.recurrent_need_validation.label)

    def test_update_recurrent_need_validation_invalid_unit_raises_assertion(self):
        """Test update_recurrent_need_validation raises assertion for invalid unit."""
        invalid_volume = ExplainableRecurrentQuantities(
            np.array([2.0] * 168, dtype=np.float32) * u.GB, "invalid unit volume")

        server_need = RecurrentServerNeed(
            "invalid unit need", self.mock_edge_device, invalid_volume, [self.mock_job])

        with self.assertRaises(AssertionError) as context:
            recompute_attribute(server_need, "recurrent_need_validation")

        self.assertIn("invalid unit", str(context.exception))
        self.assertIn("occurrence", str(context.exception))

    def test_negative_recurrent_volume_is_rejected_as_an_input(self):
        negative_volume = ExplainableRecurrentQuantities(
            np.array([-1.0] * 168, dtype=np.float32) * u.occurrence, "negative volume")

        with self.assertRaisesRegex(ValueError, "should be positive but is negative"):
            RecurrentServerNeed(
                "negative need", self.mock_edge_device, negative_volume, [self.mock_job])


    def _contain_in_one_usage_pattern(self, server_need):
        """Put server_need in a single edge usage pattern with 5 parallel deployments and one occurrence, and return that pattern."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1")
        start_date = datetime(2023, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        mock_pattern.country = MagicMock(timezone=SourceTimezone(pytz.timezone("Europe/Paris")))
        mock_pattern.nb_deployments_in_parallel = ExplainableHourlyQuantities(
            np.array([5.0] * 1000) * u.concurrent, start_date, "test parallel journeys 1")
        mock_pattern.containment_inventory = MagicMock(
            server_need_paths=[MagicMock(recurrent_server_need=server_need, nb_occurrences=1)])

        mock_journey = create_mod_obj_mock(EdgeUsageJourney, name="Mock Journey")
        mock_journey.edge_usage_patterns = [mock_pattern]
        mock_function = create_mod_obj_mock(EdgeFunction, name="Mock Function")
        mock_function.edge_usage_journeys = [mock_journey]
        mock_journey.edge_functions = [mock_function]
        set_modeling_obj_containers(server_need, [mock_function])
        return mock_pattern

    def test_update_unitary_hourly_volume_per_usage_pattern(self):
        """Test updating unitary hourly volume for all usage patterns."""
        mock_pattern = self._contain_in_one_usage_pattern(self.server_need)

        recompute_attribute(self.server_need, "unitary_hourly_volume_per_usage_pattern")

        result = self.server_need.unitary_hourly_volume_per_usage_pattern[mock_pattern]
        self.assertIsInstance(result, ExplainableHourlyQuantities)
        # Paris is UTC+1 in January → convert_to_utc keeps the same length and rotates the first value to the end
        self.assertEqual(1000, len(result.value))

    def test_unitary_hourly_volume_of_ungrouped_device_is_unchanged(self):
        """A device in no group is one unit, so the volume stays the recurrent volume."""
        mock_pattern = self._contain_in_one_usage_pattern(self.server_need)

        recompute_attribute(self.server_need, "unitary_hourly_volume_per_usage_pattern")

        result = self.server_need.unitary_hourly_volume_per_usage_pattern[mock_pattern]
        np.testing.assert_allclose(result.value.magnitude, 2.0)

    def test_unitary_hourly_volume_scales_with_total_units_of_nested_grouped_device(self):
        """A device counted 4 times in a sub-group of 3 is 12 units, so the server receives 12 times the volume."""
        device = EdgeDevice(
            name="grouped edge device", structure_carbon_footprint_manufacturing=SourceValue(0 * u.kg),
            components=[], lifespan=SourceValue(5 * u.year))
        root_group = EdgeDeviceGroup("root group")
        sub_group = EdgeDeviceGroup("sub group")
        root_group.sub_group_counts[sub_group] = SourceValue(3 * u.dimensionless)
        sub_group.edge_device_counts[device] = SourceValue(4 * u.dimensionless)
        recompute_attribute(root_group, "effective_nb_of_units_within_root")
        recompute_attribute(sub_group, "effective_nb_of_units_within_root")
        recompute_attribute(device, "total_nb_of_units")
        server_need = RecurrentServerNeed(
            "grouped server need", device,
            ExplainableRecurrentQuantities(np.array([2.0] * 168, dtype=np.float32) * u.occurrence, "grouped volume"),
            [self.mock_job])
        mock_pattern = self._contain_in_one_usage_pattern(server_need)

        recompute_attribute(server_need, "unitary_hourly_volume_per_usage_pattern")

        result = server_need.unitary_hourly_volume_per_usage_pattern[mock_pattern]
        np.testing.assert_allclose(result.value.magnitude, 2.0 * 12)


if __name__ == "__main__":
    unittest.main()
