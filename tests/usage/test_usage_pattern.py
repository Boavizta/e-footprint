import unittest
from datetime import datetime
from unittest.mock import MagicMock

import pytz

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.builders.time_builders import create_source_hourly_values_from_list, create_random_source_hourly_values


class TestUsagePattern(unittest.TestCase):
    def setUp(self):
        self.job1 = MagicMock()
        self.job2 = MagicMock()

        usage_journey = MagicMock(spec=UsageJourney)
        usage_journey.jobs = [self.job1, self.job2]
        country = MagicMock(spec=Country)
        country.timezone = SourceObject(pytz.timezone("Europe/Paris"), label="country timezone")
        self.device = MagicMock(spec=Device)

        network = MagicMock(spec=Network)

        self.usage_pattern = UsagePattern(
            "usage_pattern",
            usage_journey,
            [self.device],
            network,
            country,
            hourly_usage_journey_starts=create_source_hourly_values_from_list([1, 2, 3]),
        )

        self.usage_pattern.trigger_modeling_updates = False

    def test_jobs(self):
        self.assertEqual([self.job1, self.job2], self.usage_pattern.jobs)

    def test_update_utc_hourly_usage_journey_starts_converts_start_date(self):
        """Test UTC conversion uses country timezone for naive start dates."""
        self.usage_pattern.hourly_usage_journey_starts = create_source_hourly_values_from_list(
            [1, 2, 3], start_date=datetime(2025, 1, 1, 0, 0, 0),
        )

        self.usage_pattern.update_utc_hourly_usage_journey_starts()

        self.assertEqual([1.0, 2.0, 3.0], self.usage_pattern.utc_hourly_usage_journey_starts.value_as_float_list)
        self.assertEqual(pytz.utc, self.usage_pattern.utc_hourly_usage_journey_starts.start_date.tzinfo)
        self.assertEqual(
            pytz.utc.localize(datetime(2024, 12, 31, 23, 0, 0)),
            self.usage_pattern.utc_hourly_usage_journey_starts.start_date,
        )

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
                "usage_pattern", wrong_usage_journey, [self.device], self.usage_pattern.network,
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
