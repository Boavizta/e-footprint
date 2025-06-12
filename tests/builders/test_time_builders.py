import unittest
from datetime import datetime, timedelta

import pandas as pd

from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues
from efootprint.builders.time_builders import (
    create_random_source_hourly_values, create_source_hourly_values_from_list, linear_growth_hourly_values,
    sinusoidal_fluct_hourly_values, daily_fluct_hourly_values, create_hourly_usage_from_frequency,
    create_hourly_usage_from_daily_volume_and_list_of_hours)
from efootprint.constants.units import u


class TestTimeBuilders(unittest.TestCase):
    def test_create_random_source_hourly_values(self):
        nb_days = 2
        timespan = nb_days * u.day
        min_val = 1
        max_val = 27
        start_date = datetime.strptime("2025-07-14", "%Y-%m-%d")
        pint_unit = u.dimensionless
        shv = create_random_source_hourly_values(timespan, min_val, max_val, start_date, pint_unit)

        self.assertEqual(start_date, shv.start_date)
        self.assertEqual(nb_days * 24, len(shv.value))
        self.assertEqual(pint_unit, shv.unit)
        self.assertGreaterEqual(shv.min().value, min_val * pint_unit)
        self.assertLessEqual(shv.max().value, max_val * pint_unit)

    def test_create_source_hourly_values_from_list(self):
        start_date = datetime.strptime("2025-07-14", "%Y-%m-%d")
        pint_unit = u.dimensionless
        input_list = [1, 2, 5, 7]
        shv = create_source_hourly_values_from_list(input_list, start_date, pint_unit)

        self.assertEqual(len(input_list), len(shv.value))
        self.assertEqual(input_list, list(shv.value))
        self.assertEqual(start_date, shv.start_date)

    def test_linear_growth_hourly_values(self):
        nb_of_hours = 5
        timespan = nb_of_hours * u.hour
        start_value = 10
        end_value = 20
        result = linear_growth_hourly_values(timespan, start_value, end_value)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(len(result.value), nb_of_hours)
        self.assertEqual(result.value[0], 10)
        self.assertEqual(result.value[-1], 20)

    def test_sinusoidal_fluct_hourly_values(self):
        nb_of_days = 100
        timespan = nb_of_days * u.day
        amplitude = 10
        period_in_hours = 24 * 10
        result = sinusoidal_fluct_hourly_values(timespan, amplitude, period_in_hours)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(len(result.value), nb_of_days * 24)
        self.assertLessEqual(result.max().magnitude, amplitude)
        self.assertGreaterEqual(result.min().magnitude, -amplitude)
        self.assertGreaterEqual(result.max().magnitude, amplitude * 0.9)
        self.assertLessEqual(result.min().magnitude, -amplitude * 0.9)
        self.assertEqual(result.unit, u.dimensionless)

    def test_daily_fluct_hourly_values(self):
        timespan = 24 * u.hour
        fluct_scale = 0.5
        hour_of_min = 4
        result = daily_fluct_hourly_values(timespan, fluct_scale, hour_of_min)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(1-fluct_scale, result.value[hour_of_min].magnitude)
        self.assertEqual(len(result.value), 24)
        self.assertEqual(result.unit, u.dimensionless)

    def test_create_hourly_usage_from_frequency_case_daily(self):
        input_volume = 100
        frequency = "daily"
        active_days = None
        launch_hours = [9]
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-01-07 23:00", "%Y-%m-%d %H:%M")
        duration = (end_date - start_date).days * u.day + (end_date - start_date).seconds * u.seconds

        result = create_hourly_usage_from_frequency(
            duration, input_volume, frequency, active_days, launch_hours, start_date
        )

        expected_index_populated = [9, 33, 57, 81, 105, 129, 153]

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit, u.dimensionless)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value[index], input_volume)
            else:
                self.assertEqual(result.value[index], 0)

    def test_create_hourly_usage_from_daily_volume_and_list_of_hours(self):
        daily_volume = 100
        launch_hours = [9, 10]
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-01-07 23:00", "%Y-%m-%d %H:%M")
        duration = (end_date - start_date).days * u.day + (end_date - start_date).seconds * u.seconds

        result = create_hourly_usage_from_daily_volume_and_list_of_hours(
            duration, daily_volume, launch_hours, start_date
        )

        expected_index_populated = [9, 10, 33, 34, 57, 58, 81, 82, 105, 106, 129, 130, 153, 154]

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit, u.dimensionless)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value[index], 50)
            else:
                self.assertEqual(result.value[index], 0)

    def test_create_hourly_usage_from_frequency_case_weekly(self):
        input_volume = 100
        frequency = "weekly"
        active_days = [0, 1, 2, 3, 4]
        launch_hours = [9, 11]
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-01-14 23:00", "%Y-%m-%d %H:%M")
        duration = (end_date - start_date).days * u.day + (end_date - start_date).seconds * u.seconds

        result = create_hourly_usage_from_frequency(
            duration, input_volume, frequency, active_days, launch_hours, start_date
        )

        expected_index_populated = [
            9, 11, 33, 35, 57, 59, 81, 83, 105, 107, 177, 179, 201, 203, 225, 227, 249, 251, 273, 275]

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit, u.dimensionless)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value[index], input_volume)
            else:
                self.assertEqual(result.value[index], 0)

    def test_create_hourly_usage_from_frequency_case_monthly(self):
        input_volume = 100
        frequency = "monthly"
        active_days = [1, 6, 11, 16, 21, 26]
        launch_hours = [9, 11]
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-02-29 23:00", "%Y-%m-%d %H:%M")
        duration = (end_date - start_date).days * u.day + (end_date - start_date).seconds * u.seconds

        result = create_hourly_usage_from_frequency(
            duration, input_volume, frequency, active_days, launch_hours, start_date
        )

        expected_index_populated = [9, 11, 129, 131, 249, 251, 369, 371, 489, 491, 609, 611, 753, 755, 873, 875, 993,
                                    995, 1113, 1115, 1233, 1235, 1353, 1355]

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit,u.dimensionless)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value[index], input_volume)
            else:
                self.assertEqual(result.value[index], 0)

    def test_create_hourly_usage_from_frequency_case_yearly(self):
        input_volume = 100
        frequency = "yearly"
        active_days = [1]
        launch_hours = [12]
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2026-12-31 23:00", "%Y-%m-%d %H:%M")
        duration = (end_date - start_date).days * u.day + (end_date - start_date).seconds * u.seconds

        result = create_hourly_usage_from_frequency(
            duration, input_volume, frequency, active_days, launch_hours, start_date
        )

        expected_index_populated = [12, 8796, 17556]

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit,u.dimensionless)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value[index], input_volume)
            else:
                self.assertEqual(result.value[index], 0)
