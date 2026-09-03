import unittest
from datetime import datetime
from unittest.mock import MagicMock

import pytz

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.constants.units import u
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_pattern import UsagePattern
from efootprint.builders.time_builders import create_source_hourly_values_from_list, create_random_source_hourly_values
from tests.utils import create_mod_obj_mock, recompute_attribute


class TestUsagePattern(unittest.TestCase):
    def setUp(self):
        self.job1 = MagicMock()
        self.job2 = MagicMock()

        usage_journey = create_mod_obj_mock(UsageJourney, "usage journey")
        usage_journey.jobs = [self.job1, self.job2]
        country = MagicMock(spec=Country)
        country.timezone = SourceObject(pytz.timezone("Europe/Paris"), label="country timezone")
        self.device = MagicMock(spec=Device)

        network = MagicMock(spec=Network)

        self.usage_pattern = UsagePattern(
            "usage_pattern",
            [usage_journey],
            [self.device],
            network,
            country,
            hourly_occurrences=create_source_hourly_values_from_list([1, 2, 3]),
        )


    def test_jobs(self):
        self.assertEqual([self.job1, self.job2], self.usage_pattern.jobs)

    def test_journey_weights_are_positive_nonempty_and_guard_live_mutation(self):
        journey = next(iter(self.usage_pattern.usage_journeys))
        second = create_mod_obj_mock(UsageJourney, "second journey")
        second.jobs = []
        weighted = UsagePattern(
            "weighted pattern", {journey: 0.25, second: 2}, [self.device], self.usage_pattern.network,
            self.usage_pattern.country, create_source_hourly_values_from_list([1]))
        self.assertEqual([0.25, 2], [weight.magnitude for weight in weighted.usage_journeys.values()])
        self.assertTrue(all(
            weight.label == "Journeys per pattern occurrence" for weight in weighted.usage_journeys.values()))

        with self.assertRaises(ValueError):
            UsagePattern(
                "empty pattern", {}, [self.device], self.usage_pattern.network,
                self.usage_pattern.country, create_source_hourly_values_from_list([1]))
        with self.assertRaises(ValueError):
            UsagePattern(
                "zero weight pattern", {journey: 0}, [self.device], self.usage_pattern.network,
                self.usage_pattern.country, create_source_hourly_values_from_list([1]))
        for non_finite_weight in (float("nan"), float("inf")):
            with self.subTest(non_finite_weight=non_finite_weight), self.assertRaises(ValueError):
                UsagePattern(
                    "non-finite weight pattern", {journey: non_finite_weight}, [self.device],
                    self.usage_pattern.network, self.usage_pattern.country,
                    create_source_hourly_values_from_list([1]))

    def test_update_utc_hourly_occurrences_converts_start_date(self):
        """Test UTC conversion keeps UTC midnight anchor and shifts data instead.

        Paris is UTC+1 in January (no DST). Local midnight = UTC 23:00 previous day,
        so UTC midnight = local 01:00. The first local element (00:00-01:00) precedes
        UTC midnight and is rotated to the end of the shifted series; start_date remains
        2025-01-01 00:00 UTC.
        """
        self.usage_pattern.hourly_occurrences = create_source_hourly_values_from_list(
            [1, 2, 3], start_date=datetime(2025, 1, 1, 0, 0, 0),
        )

        recompute_attribute(self.usage_pattern, "utc_hourly_occurrences")

        self.assertEqual([2.0, 3.0, 1.0], self.usage_pattern.utc_hourly_occurrences.value_as_float_list)
        self.assertEqual(pytz.utc, self.usage_pattern.utc_hourly_occurrences.start_date.tzinfo)
        self.assertEqual(
            pytz.utc.localize(datetime(2025, 1, 1, 0, 0, 0)),
            self.usage_pattern.utc_hourly_occurrences.start_date,
        )

    def test_initialisation_with_wrong_devices_types_raises_right_error(self):
        wrong_device = MagicMock(spec=ModelingObject)
        with self.assertRaises(TypeError) as context:
            usage_pattern = UsagePattern(
                "usage_pattern", list(self.usage_pattern.usage_journeys), [wrong_device], self.usage_pattern.network,
                self.usage_pattern.country,
                hourly_occurrences=create_random_source_hourly_values()
            )
        self.assertEqual(
            str(context.exception),
            "All elements in 'devices' must be instances of Device, got [<class 'unittest.mock.MagicMock'>]"
        )

    def test_initialisation_rejects_wrong_usage_journey_type(self):
        """Test initialization delegates usage-journey key type validation to ModelingObject."""
        wrong_usage_journey = MagicMock(spec=ModelingObject)
        with self.assertRaises(TypeError):
            UsagePattern(
                "usage_pattern", [wrong_usage_journey], [self.device], self.usage_pattern.network,
                self.usage_pattern.country,
                hourly_occurrences=create_random_source_hourly_values()
            )


if __name__ == '__main__':
    unittest.main()
