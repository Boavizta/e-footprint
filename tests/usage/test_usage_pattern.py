import unittest
from unittest.mock import MagicMock, patch

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.hardware.hardware_base_classes import Hardware
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.builders.time_builders import create_random_hourly_usage_df, create_hourly_usage_df_from_list
from efootprint.constants.units import u


class TestUsagePattern(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)

        self.storage = MagicMock()
        self.server = MagicMock()

        self.job1 = MagicMock()
        self.job2 = MagicMock()

        user_journey = MagicMock()
        user_journey.duration = SourceValue(2.0 * u.min, label="duration")
        user_journey.data_upload = SourceValue(2.0 * u.MB, label="data_upload")
        user_journey.data_download = SourceValue(3.0 * u.MB, label="data_download")

        user_journey.jobs = [self.job1, self.job2]
        country = MagicMock()
        country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        self.device1 = MagicMock()
        self.device1.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device1.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device1.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        self.device2 = MagicMock()
        self.device2.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device2.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device2.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)

        network = MagicMock()

        self.usage_pattern = UsagePattern(
            "usage_pattern", user_journey, [self.device1, self.device2], network, country,
            hourly_user_journey_starts=SourceHourlyValues(create_random_hourly_usage_df())
        )
        self.usage_pattern.trigger_modeling_updates = False

    def test_jobs(self):
        self.assertEqual([self.job1, self.job2], self.usage_pattern.jobs)

    def test_devices_energy(self):
        test_device1 = MagicMock(spec=Hardware)
        test_device1.power = SourceValue(5 * u.W)
        test_device2 = MagicMock(spec=Hardware)
        test_device2.power = SourceValue(10 * u.W)
        nb_uj_in_parallel = [10, 20, 30]

        with patch.object(self.usage_pattern, "devices", new=[test_device1, test_device2]), \
             patch.object(self.usage_pattern, "nb_user_journeys_in_parallel",
                          SourceHourlyValues(create_hourly_usage_df_from_list(nb_uj_in_parallel))):
            self.usage_pattern.update_devices_energy()

            self.assertEqual(u.kWh, self.usage_pattern.devices_energy.unit)
            self.assertEqual([0.15, 0.3, 0.45], self.usage_pattern.devices_energy.value_as_float_list)

    def test_devices_energy_footprint(self):
        with patch.object(self.usage_pattern, "devices_energy",
                          SourceHourlyValues(create_hourly_usage_df_from_list([10, 20, 30], pint_unit=u.kWh))):
            self.usage_pattern.update_devices_energy_footprint()
            self.assertEqual(u.kg, self.usage_pattern.devices_energy_footprint.unit)
            self.assertEqual([1, 2, 3], self.usage_pattern.devices_energy_footprint.value_as_float_list)

    def test_devices_fabrication_footprint(self):
        device1 = MagicMock(spec=Hardware)
        device1.name = "device1"
        device1.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        device1.carbon_footprint_fabrication = SourceValue(365.25 * 24 * u.kg, Sources.BASE_ADEME_V19)
        device1.fraction_of_usage_time = SourceValue(12 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        device2 = MagicMock(spec=Hardware)
        device2.name = "device2"
        device2.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        device2.carbon_footprint_fabrication = SourceValue(365.25 * 24 * 3 * u.kg, Sources.BASE_ADEME_V19)
        device2.fraction_of_usage_time = SourceValue(8 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        with patch.object(
                self.usage_pattern, "devices", new=[device1, device2]),\
                patch.object(self.usage_pattern, "nb_user_journeys_in_parallel",
                             SourceHourlyValues(create_hourly_usage_df_from_list([10, 20, 30]))):
            self.usage_pattern.update_devices_fabrication_footprint()
            self.assertEqual(u.kg, self.usage_pattern.devices_fabrication_footprint.unit)
            self.assertEqual(
                [110, 220, 330], self.usage_pattern.devices_fabrication_footprint.value_as_float_list)


if __name__ == '__main__':
    unittest.main()
