from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestDevice(TestCase):
    def test_update_energy_footprint_sums_over_usage_patterns(self):
        """Test energy footprint sums per usage_pattern with its carbon intensity."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(1 * u.kg),
            power=SourceValue(1000 * u.W),  # 1 kWh over 1 hour
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(1 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_pattern_1 = MagicMock()
        usage_pattern_1.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_2 = MagicMock()
        usage_pattern_2.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)

        usage_journey = MagicMock()
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([1, 2, 3]),
            usage_pattern_2: create_source_hourly_values_from_list([0, 1, 0]),
        }
        usage_pattern_1.usage_journey = usage_journey
        usage_pattern_2.usage_journey = usage_journey

        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_energy_footprint()

        self.assertEqual(u.kg, device.energy_footprint.unit)
        self.assertTrue(np.allclose([0.1, 0.4, 0.3], device.energy_footprint.magnitude))

    def test_update_instances_fabrication_footprint_sums_over_usage_patterns(self):
        """Test fabrication footprint distributes fabrication over lifespan and usage time."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(365.25 * 24 * u.kg),
            power=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(12 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_pattern_1 = MagicMock()
        usage_pattern_2 = MagicMock()

        usage_journey = MagicMock()
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([1, 2, 3]),
            usage_pattern_2: create_source_hourly_values_from_list([0, 1, 0]),
        }
        usage_pattern_1.usage_journey = usage_journey
        usage_pattern_2.usage_journey = usage_journey

        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_instances_fabrication_footprint()

        self.assertEqual(u.kg, device.instances_fabrication_footprint.unit)
        self.assertTrue(np.allclose([2, 6, 6], device.instances_fabrication_footprint.magnitude))

    @patch("efootprint.core.hardware.device.Device.usage_journey_steps", new_callable=PropertyMock)
    def test_update_impact_repartition_weights_scales_steps_by_time_spent_and_matching_patterns(
            self, mock_usage_journey_steps):
        """Test device weights each step by user time spent across the usage patterns where the step appears."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(1 * u.kg),
            power=SourceValue(10 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(1 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_journey = MagicMock()
        step_1 = create_mod_obj_mock(UsageJourneyStep, "Step 1", user_time_spent=SourceValue(10 * u.min))
        step_2 = create_mod_obj_mock(UsageJourneyStep, "Step 2", user_time_spent=SourceValue(30 * u.min))
        step_1.nb_of_occurrences_per_container = {usage_journey: SourceValue(1 * u.dimensionless)}
        step_2.nb_of_occurrences_per_container = {usage_journey: SourceValue(1 * u.dimensionless)}

        usage_pattern_1 = create_mod_obj_mock(UsagePattern, "Pattern 1", usage_journey=usage_journey)
        usage_pattern_1.utc_hourly_usage_journey_starts = create_source_hourly_values_from_list([2], pint_unit=u.occurrence)
        usage_pattern_2 = create_mod_obj_mock(UsagePattern, "Pattern 2", usage_journey=usage_journey)
        usage_pattern_2.utc_hourly_usage_journey_starts = create_source_hourly_values_from_list([1], pint_unit=u.occurrence)

        step_1.usage_patterns = [usage_pattern_1, usage_pattern_2]
        step_2.usage_patterns = [usage_pattern_1]
        mock_usage_journey_steps.return_value = [step_1, step_2]
        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_impact_repartition_weights()

        self.assertTrue(np.allclose([30], device.impact_repartition_weights[step_1].magnitude))
        self.assertTrue(np.allclose([60], device.impact_repartition_weights[step_2].magnitude))
