import random
import unittest
from copy import copy
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytz

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.constants.units import u


class TestExplainableHourlyQuantities(unittest.TestCase):
    def setUp(self):
        self.usage1 = [1] * 24
        self.usage2 = [2] * 24
        self.start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        self.hourly_usage1 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(self.usage1, self.start_date, pint_unit=u.W), "Usage 1")
        self.hourly_usage2 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(self.usage2, self.start_date, pint_unit=u.W), "Usage 2")

    def test_init(self):
        self.assertEqual(self.hourly_usage1.label, "Usage 1")
        self.assertEqual(len(self.hourly_usage1.value), 24)

    def test_addition_between_hourly_quantities_with_same_unit(self):
        sum_hourly_usage = self.hourly_usage1 + self.hourly_usage2
        self.assertEqual([3] * 24, sum_hourly_usage.value_as_float_list)

    def test_addition_between_hourly_quantities_with_homogeneous_but_different_units(self):
        hourly_usage1 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([1, 2, 3], self.start_date, pint_unit=u.kW), "Usage 1")
        hourly_usage2 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([10, 20, 30], self.start_date, pint_unit=u.W), "Usage 2")
        sum_hourly_usage = hourly_usage1 + hourly_usage2
        self.assertEqual([1.01, 2.02, 3.03], sum_hourly_usage.value_as_float_list)

    def test_addition_between_non_overlapping_hourly_quantities_with_same_units(self):
        hourly_usage1 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([1, 2, 3],
            datetime.strptime("2025-01-01", "%Y-%m-%d"), pint_unit=u.W), "Usage 1")
        hourly_usage2 = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([10, 20, 30],
            datetime.strptime("2025-01-02", "%Y-%m-%d"), pint_unit=u.W), "Usage 2")
        sum_hourly_usage = hourly_usage1 + hourly_usage2
        self.assertEqual([1, 2, 3, 10, 20, 30], sum_hourly_usage.value_as_float_list)
        self.assertEqual(hourly_usage1.value.index.min(), sum_hourly_usage.value.index.min())
        self.assertEqual(hourly_usage2.value.index.max(), sum_hourly_usage.value.index.max())

    def test_addition_with_shifted_hourly_quantities(self):
        nb_hours_shifted = 2
        shifted_hour_usage = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(
                self.usage2, self.start_date + timedelta(hours=nb_hours_shifted), pint_unit=u.W), "Usage 2")
        sum_hourly_usage = self.hourly_usage1 + shifted_hour_usage

        self.assertTrue(isinstance(sum_hourly_usage, ExplainableHourlyQuantities))
        self.assertEqual(len(self.hourly_usage1) + nb_hours_shifted, len(sum_hourly_usage))
        self.assertEqual(self.hourly_usage1.value.index.min(), sum_hourly_usage.value.index.min())
        self.assertEqual(self.hourly_usage1.value_as_float_list[:nb_hours_shifted],
                         sum_hourly_usage.value_as_float_list[:nb_hours_shifted])
        self.assertEqual(shifted_hour_usage.value_as_float_list[-nb_hours_shifted:],
                         sum_hourly_usage.value_as_float_list[-nb_hours_shifted:])

    def test_addition_with_quantity_fails(self):
        with self.assertRaises(ValueError):
            addition_result = self.hourly_usage1 + ExplainableQuantity(4 * u.W, "4W")

    def test_mul_with_quantity(self):
        mul_result = self.hourly_usage1 * ExplainableQuantity(4 * u.h, "4 hours")

        self.assertTrue(isinstance(mul_result, ExplainableHourlyQuantities))
        self.assertTrue(u.Wh.is_compatible_with(mul_result.unit))
        self.assertEqual([4] * 24, mul_result.value_as_float_list)

    def test_mul_2_hourly_quantities(self):
        result = self.hourly_usage1 * self.hourly_usage2

        self.assertTrue(isinstance(result, ExplainableHourlyQuantities))
        self.assertEqual([2] * 24, result.value_as_float_list)
        self.assertEqual(self.hourly_usage1.value.index.min, result.value.index.min)
        self.assertEqual(self.hourly_usage1.value.index.max, result.value.index.max)

    def test_mul_with_shifted_hourly_quantities(self):
        nb_hours_shifted = 2
        shifted_hour_usage = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(
                self.usage2, self.start_date + timedelta(hours=nb_hours_shifted), pint_unit=u.W), "Usage 2")
        mul_hourly_usage = self.hourly_usage1 * shifted_hour_usage

        self.assertTrue(isinstance(mul_hourly_usage, ExplainableHourlyQuantities))
        self.assertEqual(len(self.hourly_usage1) + nb_hours_shifted, len(mul_hourly_usage))
        self.assertEqual(self.hourly_usage1.value.index.min(), mul_hourly_usage.value.index.min())
        self.assertEqual([0] * nb_hours_shifted,
                         mul_hourly_usage.value_as_float_list[:nb_hours_shifted])
        self.assertEqual([0] * nb_hours_shifted,
                         mul_hourly_usage.value_as_float_list[-nb_hours_shifted:])

    def test_subtraction(self):
        result = self.hourly_usage2 - self.hourly_usage1
        self.assertEqual([1] * 24, result.value_as_float_list)

    def test_subtraction_with_quantity_fails(self):
        with self.assertRaises(ValueError):
            subtraction_result = self.hourly_usage1 - ExplainableQuantity(4 * u.W, "4W")

    def test_convert_to_utc(self):
        start_date = datetime(2023, 10, 1)
        # Artificially fix datetime to avoid test crashing because of annual time changes.
        mock_data = [1] * 12
        usage = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(mock_data, start_date=start_date), "usage")

        local_tz_ahead_utc = ExplainableObject(pytz.timezone('Europe/Berlin'), "local timezone ahead UTC")
        local_tz_behind_utc = ExplainableObject(pytz.timezone('America/New_York'), "local timezone behind UTC")

        converted_ahead_utc = usage.convert_to_utc(local_tz_ahead_utc)
        converted_behind_utc = usage.convert_to_utc(local_tz_behind_utc)

        # Berlin is 2 hours ahead, converting to UTC results in the array shifted by 2 positions to the left
        self.assertEqual(mock_data, converted_ahead_utc.value_as_float_list)
        self.assertEqual(mock_data, converted_behind_utc.value_as_float_list)

        self.assertEqual(str(start_date - timedelta(hours=2)), str(converted_ahead_utc.value.index.min())[:19])
        self.assertEqual(str(start_date + timedelta(hours=4)), str(converted_behind_utc.value.index.min())[:19])

        # Check other attributes of converted ExplainableHourlyUsage
        self.assertEqual(None, converted_ahead_utc.label)
        self.assertEqual(usage, converted_ahead_utc.left_parent)
        self.assertEqual(local_tz_ahead_utc, converted_ahead_utc.right_parent)
        self.assertEqual("converted to UTC from", converted_ahead_utc.operator)

    def test_convert_to_utc_return_non_duplicated_index(self):
        # create datetime index that includes summer French time change
        nb_hours = 24
        datetime_index = pd.date_range(start=datetime(2025, 3, 30), periods=nb_hours, freq="h")
        usage = ExplainableHourlyQuantities(
            pd.DataFrame({"value": np.arange(nb_hours)}, index=datetime_index, dtype="pint[kg]"), "usage")

        utc_converted = usage.convert_to_utc(ExplainableObject(pytz.timezone('Europe/Paris'), "local French timezone"))

        # Check that the index is unique
        self.assertTrue(utc_converted.value.index.is_unique)
        self.assertEqual([0, 1, 5, 4, 5, 6] + list(range(7, nb_hours)), utc_converted.value_as_float_list)

    def test_sum(self):
        summed = self.hourly_usage1.sum()
        self.assertEqual(summed, ExplainableQuantity(24 * u.W, "24 W"))

    def test_max(self):
        maximum = self.hourly_usage1.max()
        self.assertEqual(maximum, ExplainableQuantity(1 * u.W, "1 W"))

    def test_abs(self):
        self.assertEqual(self.hourly_usage1, self.hourly_usage1.abs())

    def test_abs_complex_case(self):
        test_data = ExplainableHourlyQuantities(create_hourly_usage_df_from_list([1, -1, -4]), "test")

        self.assertEqual([1, 1, 4], test_data.abs().value_as_float_list)

    def test_eq_returns_true_when_equal(self):
        self.assertTrue(self.hourly_usage1 == self.hourly_usage1)

    def test_eq_returns_false_when_not_equal(self):
        self.assertFalse(self.hourly_usage1 == self.hourly_usage2)

    def test_to_json(self):
        self.maxDiff = None
        self.assertDictEqual(
            {"label": "Usage 1", "compressed_values": "KLUv/SDAlQAASAAAAAAAAPA/AAIArxUCLTgC", "unit": "watt",
             "start_date": "2025-01-01 00:00:00", "timezone": None},
            self.hourly_usage1.to_json())

    def test_to_json_with_compressed_data_from_json(self):
        self.maxDiff = None
        json_data = {
            "compressed_values": "KLUv/SDAlQAASAAAAAAAAPA/AAIArxUCLTgC",
            "unit": "watt",
            "start_date": "2025-01-01 00:00:00",
            "timezone": None
        }
        obj = ExplainableHourlyQuantities(json_data, "Usage 1")
        expected_json = copy(json_data)
        expected_json["label"] = "Usage 1"
        self.assertDictEqual(json_data, obj.to_json())

    def test_ceil_dimensionless(self):
        usage_data = [1.5] * 24
        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_data, pint_unit=u.dimensionless), "test")

        ceil = hourly_usage_data.ceil()
        self.assertEqual([2] * 24, ceil.value_as_float_list)
        self.assertEqual(u.dimensionless, ceil.unit)

    def test_ceil_with_unit_specified(self):
        usage_data = [1.5] * 24
        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_data, pint_unit=u.GB), "test")

        ceil = hourly_usage_data.ceil()
        self.assertEqual([2] * 24, ceil.value_as_float_list)
        self.assertEqual(u.GB, ceil.unit)

    def test_copy(self):
        usage_data = [1.5] * 24
        expected_data = [1.5] * 24
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        end_date = start_date + timedelta(hours=len(usage_data) - 1)

        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_data, start_date=start_date, pint_unit=u.GB, ), "test")

        duplicated = hourly_usage_data.copy()
        self.assertEqual(expected_data, duplicated.value_as_float_list)
        self.assertEqual(u.GB, duplicated.unit)
        self.assertEqual(start_date, duplicated.value.index.min())
        self.assertEqual(end_date, duplicated.value.index.max())

    def test_np_compared_with(self):
        usage_to_compare = [0.5, 1.5] * 12
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        hourly_usage_to_compare = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_to_compare, start_date=start_date, pint_unit=u.W), "Usage to compare")
        self.assertEqual(
            [1, 1.5] * 12,
            self.hourly_usage1.np_compared_with(hourly_usage_to_compare, "max").value_as_float_list)
        self.assertEqual(
            [0.5, 1] * 12,
             self.hourly_usage1.np_compared_with(hourly_usage_to_compare, "min").value_as_float_list)

    def test_np_compared_only_with_only_empty_explainable_object(self):
        usage_to_compare_a = EmptyExplainableObject()
        usage_to_compare_b = EmptyExplainableObject()
        self.assertEqual(usage_to_compare_a.np_compared_with(usage_to_compare_b, "max"), EmptyExplainableObject())

    def test_np_compared_max_with_an_empty_explainable_object_and_positive_usage(self):
        usage_to_compare = EmptyExplainableObject()
        expected_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([1] * 24, self.start_date, pint_unit=u.W), "Usage 1")
        self.assertEqual(expected_data.value_as_float_list,
                         self.hourly_usage1.np_compared_with(usage_to_compare, "max").value_as_float_list)

    def test_np_compared_max_with_an_empty_explainable_object_and_negative_usage(self):
        usage_base = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1] * 24, self.start_date, pint_unit=u.W), "Usage 1")
        usage_to_compare = EmptyExplainableObject()
        self.assertEqual(usage_base.np_compared_with(usage_to_compare, "max").value_as_float_list, [0]*24)

    def test_np_compared_min_with_an_empty_explainable_object_and_positive_usage(self):
        usage_base = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([1] * 24, self.start_date, pint_unit=u.W), "Usage 1")
        usage_to_compare = EmptyExplainableObject()
        self.assertEqual(usage_base.np_compared_with(usage_to_compare, "min").value_as_float_list, [0]*24)

    def test_np_compared_min_with_an_empty_explainable_object_and_usage_negatif(self):
        usage_base = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1] * 24, self.start_date, pint_unit=u.W), "Usage 1")
        expected_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1] * 24, self.start_date, pint_unit=u.W), "Usage 1")
        usage_to_compare = EmptyExplainableObject()
        self.assertEqual(expected_data.value_as_float_list,
                         usage_base.np_compared_with(usage_to_compare, "min").value_as_float_list)

    def test_np_compared_min_with_an_empty_explainable_object_and_usage_mix_pos_neg(self):
        usage_base = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1, 1] * 12, self.start_date, pint_unit=u.W), "Usage 1")
        expected_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1, 0] * 12, self.start_date, pint_unit=u.W), "Usage 1")
        usage_to_compare = EmptyExplainableObject()
        self.assertEqual(expected_data.value_as_float_list,
                         usage_base.np_compared_with(usage_to_compare, "min").value_as_float_list)

    def test_np_compared_max_with_an_empty_explainable_object_and_usage_mix_pos_neg(self):
        usage_base = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([-1, 1] * 12, self.start_date, pint_unit=u.W), "Usage 1")
        expected_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([0, 1] * 12, self.start_date, pint_unit=u.W), "Usage 1")
        usage_to_compare = EmptyExplainableObject()
        self.assertEqual(expected_data.value_as_float_list,
                         usage_base.np_compared_with(usage_to_compare, "max").value_as_float_list)

    def test_copy_with_changes_on_source(self):
        usage_data = [1.5] * 24
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")

        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_data, start_date=start_date, pint_unit=u.GB, ), "test")

        duplicated = hourly_usage_data.copy()
        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list([3] * 24, start_date=start_date, pint_unit=u.GB, ), "test")

        self.assertNotEqual(hourly_usage_data.value_as_float_list, duplicated.value_as_float_list)

    def test_plot_explainable_hourly_quantities(self):
        random_values = [random.randrange(10, 20) for _ in range(24 * 31)]
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        hourly_emission = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(random_values, start_date=start_date, pint_unit=u.kg),
            "Hourly emission of carbon of my test")
        hourly_emission.plot()

    def test_plot_explainable_hourly_quantities_with_xlims(self):
        random_values = [random.randrange(10, 20) for _ in range(24 * 31)]
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        hourly_emission = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(random_values, start_date=start_date, pint_unit=u.kg),
            "Hourly emission of carbon of my test")
        hourly_emission.plot(xlims=[start_date, start_date + timedelta(hours=3)])

    def test_negate(self):
        usage_data = [1.5] * 24
        expected_data = [-1.5] * 24
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")

        hourly_usage_data = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(usage_data, start_date=start_date, pint_unit=u.GB, ), "test")

        self.assertEqual(expected_data, (-hourly_usage_data).value_as_float_list)

    @patch("efootprint.abstract_modeling_classes.explainable_hourly_quantities.ExplainableHourlyQuantities.id",
           new_callable=PropertyMock)
    def test_plot_with_simulation(self, mock_id):
        modeling_obj_container = MagicMock()
        system = MagicMock()
        modeling_obj_container.systems = [system]
        simulation = MagicMock()
        system.simulation = simulation

        value_id = "recomputed_value_id"
        recomputed_value = MagicMock()
        recomputed_value.value = Mock(spec=EmptyExplainableObject)
        recomputed_value.id = value_id
        mock_id.return_value = value_id

        simulation.values_to_recompute = [MagicMock(id=value_id)]
        simulation.recomputed_values = [recomputed_value]
        simulation.simulation_date = self.start_date + timedelta(hours=3)

        ehq = ExplainableHourlyQuantities(
            create_hourly_usage_df_from_list(self.usage1, self.start_date, pint_unit=u.W), "Usage 1")

        ehq.modeling_obj_container = modeling_obj_container

        ehq.plot(cumsum=True)


if __name__ == "__main__":
    unittest.main()
