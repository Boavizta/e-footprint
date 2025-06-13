import unittest
from unittest.mock import MagicMock, patch

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.builders.time_builders import create_random_source_hourly_values, create_source_hourly_values_from_list
from efootprint.constants.units import u


class TestUsagePattern(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(ListLinkedToModelingObj, "check_value_type", return_value=True)
        self.mock_check_value_type = patcher.start()
        self.addCleanup(patcher.stop)

        self.job1 = MagicMock()
        self.job2 = MagicMock()

        usage_journey = MagicMock(spec=UsageJourney)
        usage_journey.duration = SourceValue(2.0 * u.min, label="duration")
        usage_journey.data_transferred = SourceValue(5.0 * u.MB, label="data_transferred")

        usage_journey.jobs = [self.job1, self.job2]
        country = MagicMock(spec=Country)
        country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        self.device1 = MagicMock(spec=Device)
        self.device1.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device1.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device1.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        self.device2 = MagicMock(spec=Device)
        self.device2.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        self.device2.carbon_footprint_fabrication = SourceValue(10 * u.kg, Sources.BASE_ADEME_V19)
        self.device2.fraction_of_usage_time = SourceValue(2 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)

        network = MagicMock(spec=Network)

        self.usage_pattern = UsagePattern(
            "usage_pattern", usage_journey, [self.device1, self.device2], network, country,
            hourly_usage_journey_starts=create_random_source_hourly_values())

        self.usage_pattern.trigger_modeling_updates = False

    def test_jobs(self):
        self.assertEqual([self.job1, self.job2], self.usage_pattern.jobs)

    def test_devices_energy(self):
        test_device1 = MagicMock(spec=Device)
        test_device1.power = SourceValue(5 * u.W)
        test_device2 = MagicMock(spec=Device)
        test_device2.power = SourceValue(10 * u.W)
        nb_uj_in_parallel = [10, 20, 30]

        with patch.object(self.usage_pattern, "devices", new=[test_device1, test_device2]), \
             patch.object(self.usage_pattern, "nb_usage_journeys_in_parallel",
                          create_source_hourly_values_from_list(nb_uj_in_parallel)):
            self.usage_pattern.update_devices_energy()

            self.assertEqual(u.kWh, self.usage_pattern.devices_energy.unit)
            self.assertEqual([0.15, 0.3, 0.45], self.usage_pattern.devices_energy.value_as_float_list)

    def test_devices_energy_footprint(self):
        with patch.object(self.usage_pattern, "devices_energy",
                          create_source_hourly_values_from_list([10, 20, 30], pint_unit=u.kWh)):
            self.usage_pattern.update_devices_energy_footprint()
            self.assertEqual(u.kg, self.usage_pattern.devices_energy_footprint.unit)
            self.assertEqual([1, 2, 3], self.usage_pattern.devices_energy_footprint.value_as_float_list)

    def test_devices_fabrication_footprint(self):
        device1 = MagicMock(spec=Device)
        device1.name = "device1"
        device1.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        device1.carbon_footprint_fabrication = SourceValue(365.25 * 24 * u.kg, Sources.BASE_ADEME_V19)
        device1.fraction_of_usage_time = SourceValue(12 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        device2 = MagicMock(spec=Device)
        device2.name = "device2"
        device2.lifespan = SourceValue(1 * u.year, Sources.HYPOTHESIS)
        device2.carbon_footprint_fabrication = SourceValue(365.25 * 24 * 3 * u.kg, Sources.BASE_ADEME_V19)
        device2.fraction_of_usage_time = SourceValue(8 * u.hour / u.day, Sources.STATE_OF_MOBILE_2022)
        with patch.object(
                self.usage_pattern, "devices", new=[device1, device2]),\
                patch.object(self.usage_pattern, "nb_usage_journeys_in_parallel",
                             create_source_hourly_values_from_list([10, 20, 30])):
            self.usage_pattern.update_devices_fabrication_footprint()
            self.assertEqual(u.kg, self.usage_pattern.devices_fabrication_footprint.unit)
            self.assertEqual(
                [110, 220, 330], round(self.usage_pattern.devices_fabrication_footprint, 0).value_as_float_list)

    def test_initialisation_with_wrong_devices_types_raises_right_error(self):
        wrong_device = MagicMock(spec=ModelingObject)
        with self.assertRaises(TypeError) as context:
            usage_pattern = UsagePattern(
                "usage_pattern", self.usage_pattern.usage_journey, [wrong_device], self.usage_pattern.network,
                self.usage_pattern.country,
                hourly_usage_journey_starts=create_random_source_hourly_values()
            )
        self.assertEqual(
            str(context.exception),
            "All elements in 'devices' must be instances of Device, got [<class 'unittest.mock.MagicMock'>]"
        )

    def test_initialisation_with_wrong_usage_journey_type_raises_right_error(self):
        wrong_usage_journey = MagicMock(spec=ModelingObject)
        with self.assertRaises(TypeError) as context:
            usage_pattern = UsagePattern(
                "usage_pattern", wrong_usage_journey, [self.device1], self.usage_pattern.network,
                self.usage_pattern.country,
                hourly_usage_journey_starts=create_random_source_hourly_values()
            )
        self.assertEqual(
            str(context.exception),
            "In usage_pattern, attribute usage_journey should be of type "
            "<class 'efootprint.core.usage.usage_journey.UsageJourney'> but is of type "
            "<class 'unittest.mock.MagicMock'>"
        )


if __name__ == '__main__':
    unittest.main()
