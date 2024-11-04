import unittest
from datetime import datetime, timedelta

import pint

from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues
from efootprint.builders.time_builders import (
    create_random_hourly_usage_df, create_hourly_usage_df_from_list, linear_growth_hourly_values,
    sinusoidal_fluct_hourly_values, daily_fluct_hourly_values, create_hourly_usage_from_frequency)
from efootprint.constants.units import u


class TestTimeBuilders(unittest.TestCase):
    def test_create_random_hourly_usage_df(self):
        nb_days = 2
        min_val = 1
        max_val = 27
        start_date = datetime.strptime("2025-07-14", "%Y-%m-%d")
        pint_unit = u.dimensionless
        df = create_random_hourly_usage_df(nb_days, min_val, max_val, start_date, pint_unit)

        self.assertEqual(start_date, datetime.strptime(df.index.min().strftime("%Y-%m-%d"), "%Y-%m-%d"))
        self.assertEqual(nb_days * 24 + 1, len(df))
        self.assertEqual(pint_unit, df.dtypes.iloc[0].units)
        self.assertGreaterEqual(df["value"].min(), min_val * pint_unit)
        self.assertLessEqual(df["value"].max(), max_val * pint_unit)

    def test_create_hourly_usage_df_from_list(self):
        start_date = datetime.strptime("2025-07-14", "%Y-%m-%d")
        pint_unit = u.dimensionless
        input_list = [1, 2, 5, 7]
        df = create_hourly_usage_df_from_list(input_list, start_date, pint_unit)

        self.assertEqual(len(input_list), len(df))
        self.assertEqual(input_list, list(df["value"].values._data))
        self.assertEqual(start_date, datetime.strptime(df.index.min().strftime("%Y-%m-%d"), "%Y-%m-%d"))
        self.assertEqual(start_date + timedelta(hours=len(input_list) - 1),
                         df.index.max().to_timestamp().to_pydatetime())

    def test_linear_growth_hourly_values(self):
        nb_of_hours = 5
        start_value = 10
        end_value = 20
        result = linear_growth_hourly_values(nb_of_hours, start_value, end_value)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(len(result.value), nb_of_hours)
        self.assertEqual(result.value['value'][0], 10)
        self.assertEqual(result.value['value'][-1], 20)

    def test_sinusoidal_fluct_hourly_values(self):
        nb_of_hours = 24 * 100
        amplitude = 10
        period_in_hours = 24 * 10
        result = sinusoidal_fluct_hourly_values(nb_of_hours, amplitude, period_in_hours)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(len(result.value), nb_of_hours)
        self.assertLessEqual(result.value["value"].max().magnitude, amplitude)
        self.assertGreaterEqual(result.value["value"].min().magnitude, -amplitude)
        self.assertGreaterEqual(result.value["value"].max().magnitude, amplitude * 0.9)
        self.assertLessEqual(result.value["value"].min().magnitude, -amplitude * 0.9)
        self.assertEqual(result.value['value'].pint.units, u.dimensionless)

    def test_daily_fluct_hourly_values(self):
        nb_of_hours = 24
        fluct_scale = 0.5
        hour_of_min = 4
        result = daily_fluct_hourly_values(nb_of_hours, fluct_scale, hour_of_min)

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(1-fluct_scale, result.value["value"].iloc[hour_of_min].magnitude)
        self.assertEqual(len(result.value), nb_of_hours)
        self.assertEqual(result.value['value'].pint.units, u.dimensionless)

    def test_create_hourly_usage_from_frequency_case_1(self):
        input_volume = 100
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        pint_unit = pint.Unit(u.dimensionless)
        type_frequency = "daily"
        duration = 14 * u.day
        only_word_days = True
        time_list = [9, 11]
        result = create_hourly_usage_from_frequency(input_volume, start_date, pint_unit, type_frequency, duration,
                                                    only_word_days, time_list)

        expected_index_populated = [9, 11, 33, 35, 57, 59, 81, 83, 105, 107, 177, 179, 201, 203, 225, 227,
                            249, 251, 273, 275]

        expected_max_date = datetime.strptime("2024-01-14 23:00", "%Y-%m-%d %H:%M")

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit, pint_unit)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value['value'].iloc[index], input_volume)
            else:
                self.assertEqual(result.value['value'].iloc[index], 0)
        self.assertEqual(max(result.value.index), expected_max_date)



    def test_create_hourly_usage_from_frequency_case_3(self):
        input_volume = 100
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        pint_unit = pint.Unit(u.dimensionless)
        type_frequency = "monthly"
        duration = 2 * u.month
        only_word_days = True
        time_list = [1, 6, 11, 16, 21, 26]
        launch_hours_list = [9, 11]
        result = create_hourly_usage_from_frequency(input_volume, start_date, pint_unit, type_frequency, duration,
                                                    only_word_days, time_list,  launch_hours_list)

        expected_index_populated = [9, 11, 129, 131, 249, 251, 369, 371, 489, 491, 609, 611 ,753, 755 ,873, 875 ,993,
                                    995 ,1113, 1115, 1233, 1235 ,1353, 1355]

        expected_max_date = datetime.strptime("2024-02-29 23:00", "%Y-%m-%d %H:%M")

        self.assertTrue(isinstance(result, SourceHourlyValues))
        self.assertEqual(result.unit, pint_unit)
        self.assertEqual(max(result.value.index), expected_max_date)
        for index in range(0, len(result.value)):
            if index in expected_index_populated:
                self.assertEqual(result.value['value'].iloc[index], input_volume)
            else:
                self.assertEqual(result.value['value'].iloc[index], 0)
        self.assertEqual(max(result.value.index), expected_max_date)