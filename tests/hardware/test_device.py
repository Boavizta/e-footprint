from unittest import TestCase
from unittest.mock import MagicMock

import numpy as np

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from tests.utils import set_modeling_obj_containers


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

