import unittest
from datetime import datetime, timezone
import pytz

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_recurring_quantities import ExplainableRecurringQuantities
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.constants.units import u


class TestExplainableRecurringQuantities(unittest.TestCase):
    def setUp(self):
        self.recurring_values1 = [1, 2, 3, 4] * 6  # 24 values
        self.recurring_values2 = [2, 4, 6, 8] * 6  # 24 values
        self.recurring_quantity1 = ExplainableRecurringQuantities(
            Quantity(np.array(self.recurring_values1, dtype=np.float32), u.W), "Recurring 1")
        self.recurring_quantity2 = ExplainableRecurringQuantities(
            Quantity(np.array(self.recurring_values2, dtype=np.float32), u.W), "Recurring 2")

    def test_init_with_quantity(self):
        self.assertEqual(self.recurring_quantity1.label, "Recurring 1")
        self.assertEqual(len(self.recurring_quantity1.value), 24)
        self.assertEqual(self.recurring_quantity1.unit, u.W)

    def test_init_with_non_float32_array_logs_conversion(self):
        with self.assertLogs(level='INFO') as log:
            recurring_quantity = ExplainableRecurringQuantities(
                Quantity(np.array([1, 2, 3]), u.W), "Test")
        self.assertIn("converting value Test to float32", log.output[0])

    def test_init_with_invalid_type_raises_error(self):
        with self.assertRaises(ValueError):
            ExplainableRecurringQuantities([1, 2, 3], "Invalid")

    def test_equality_with_non_equal_recurring_quantity(self):
        self.assertFalse(self.recurring_quantity1 == self.recurring_quantity2)

    def test_equality_with_equal_recurring_quantity(self):
        self.assertTrue(self.recurring_quantity1 == self.recurring_quantity1)

    def test_equality_is_false_if_compared_with_other_type(self):
        self.assertTrue(self.recurring_quantity1 != "Recurring 1")

    def test_unit_property(self):
        self.assertEqual(self.recurring_quantity1.unit, u.W)

    def test_magnitude_property(self):
        expected = np.array(self.recurring_values1, dtype=np.float32)
        np.testing.assert_array_equal(self.recurring_quantity1.magnitude, expected)

    def test_value_as_float_list(self):
        self.assertEqual(self.recurring_quantity1.value_as_float_list, self.recurring_values1)

    def test_to_unit_conversion(self):
        original_value = self.recurring_quantity1.value.magnitude.copy()
        result = self.recurring_quantity1.to(u.kW)
        
        self.assertEqual(result.unit, u.kW)
        expected = original_value / 1000
        np.testing.assert_array_almost_equal(result.magnitude, expected)

    def test_copy(self):
        copied = self.recurring_quantity1.copy()
        
        self.assertEqual(copied.label, self.recurring_quantity1.label)
        self.assertEqual(copied.unit, self.recurring_quantity1.unit)
        np.testing.assert_array_equal(copied.magnitude, self.recurring_quantity1.magnitude)
        self.assertIs(copied.left_parent, self.recurring_quantity1)
        self.assertEqual(copied.operator, "duplicate")

    def test_round_method(self):
        values_with_decimals = [1.567, 2.234, 3.891]
        recurring_quantity = ExplainableRecurringQuantities(
            Quantity(np.array(values_with_decimals, dtype=np.float32), u.W), "Test")
        
        result = recurring_quantity.round(1)
        expected = [1.6, 2.2, 3.9]
        
        self.assertAlmostEqual(result.value_as_float_list[0], expected[0], places=1)
        self.assertAlmostEqual(result.value_as_float_list[1], expected[1], places=1)
        self.assertAlmostEqual(result.value_as_float_list[2], expected[2], places=1)

    def test_dunder_round(self):
        values_with_decimals = [1.567, 2.234, 3.891]
        recurring_quantity = ExplainableRecurringQuantities(
            Quantity(np.array(values_with_decimals, dtype=np.float32), u.W), "Test")
        
        result = round(recurring_quantity, 1)
        expected = [1.6, 2.2, 3.9]
        
        self.assertIsInstance(result, ExplainableRecurringQuantities)
        self.assertIs(result.left_parent, recurring_quantity)
        self.assertEqual(result.operator, "rounded to 1 decimals")
        self.assertAlmostEqual(result.value_as_float_list[0], expected[0], places=1)

    def test_generate_explainable_object_with_logical_dependency(self):
        condition = ExplainableQuantity(5 * u.dimensionless, "condition")
        result = self.recurring_quantity1.generate_explainable_object_with_logical_dependency(condition)
        
        self.assertIsInstance(result, ExplainableRecurringQuantities)
        self.assertIs(result.left_parent, self.recurring_quantity1)
        self.assertIs(result.right_parent, condition)
        self.assertEqual(result.operator, "logically dependent on")

    def test_to_json(self):
        json_data = self.recurring_quantity1.to_json()
        
        self.assertIn("recurring_values", json_data)
        self.assertIn("unit", json_data)
        self.assertIn("label", json_data)
        self.assertEqual(json_data["unit"], "watt")
        self.assertEqual(json_data["label"], "Recurring 1")
        np.testing.assert_array_equal(
            json_data["recurring_values"], str([float(elt) for elt in self.recurring_values1]))

    def test_from_json_dict(self):
        json_data = {
            "recurring_values": "[1.0, 2.0, 3.0]",
            "unit": "watt",
            "label": "Test Recurring"
        }
        
        obj = ExplainableObject.from_json_dict(json_data)
        
        self.assertEqual(obj.label, "Test Recurring")
        self.assertEqual(obj.unit, u.W)
        self.assertEqual(obj.value_as_float_list, [1.0, 2.0, 3.0])

    def test_from_json_dict_with_source(self):
        from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
        json_data = {
            "recurring_values": "[1.0, 2.0]",
            "unit": "watt",
            "label": "Test",
            "source": {"name": "test_source", "link": "http://test.com"}
        }
        
        obj = ExplainableObject.from_json_dict(json_data)
        
        self.assertIsInstance(obj.source, Source)
        self.assertEqual(obj.source.name, "test_source")

    def test_str_short_array(self):
        short_values = [1.567, 2.234]
        recurring_quantity = ExplainableRecurringQuantities(
            Quantity(np.array(short_values, dtype=np.float32), u.W), "Test")
        
        str_repr = str(recurring_quantity)
        
        self.assertIn("2 values in W", str_repr)
        self.assertIn("[1.57, 2.23]", str_repr)

    def test_str_long_array(self):
        long_values = list(range(50))
        recurring_quantity = ExplainableRecurringQuantities(
            Quantity(np.array(long_values, dtype=np.float32), u.W), "Test")
        
        str_repr = str(recurring_quantity)
        
        self.assertIn("50 values in W", str_repr)
        self.assertIn("first 10 vals", str_repr)
        self.assertIn("last 10 vals", str_repr)

    def test_str_dimensionless_unit(self):
        recurring_quantity = ExplainableRecurringQuantities(
            Quantity(np.array([1, 2, 3], dtype=np.float32), u.dimensionless), "Test")
        
        str_repr = str(recurring_quantity)
        
        self.assertIn("dimensionless", str_repr)

    def test_repr_equals_str(self):
        self.assertEqual(repr(self.recurring_quantity1), str(self.recurring_quantity1))


class TestGenerateExplainableHourlyQuantityOverTimespan(unittest.TestCase):
    def setUp(self):
        # Create a canonical week pattern (168 hours = 7 days * 24 hours)
        # Pattern: Monday=10, Tuesday=20, ..., Sunday=70, then repeat hourly pattern within each day
        week_values = []
        for day in range(7):  # 0=Monday, 6=Sunday
            for hour in range(24):
                # Simple pattern: base value (day+1)*10 + hour offset
                week_values.append((day + 1) * 10 + hour % 4)
        
        self.weekly_recurring_pattern = ExplainableRecurringQuantities(
            Quantity(np.array(week_values, dtype=np.float32), u.W), 
            "Weekly Pattern"
        )
        
        # Create timezone objects for testing
        self.utc_timezone = ExplainableTimezone(pytz.UTC, "UTC")
        self.paris_timezone = ExplainableTimezone(pytz.timezone('Europe/Paris'), "Paris")

    def test_generate_over_one_week_monday_start_and_calculation_dependencies_are_tracked(self):
        # Start on Monday 2025-01-06 00:00:00 local time (which is a Monday)
        start_date_local = datetime(2025, 1, 6, 0, 0, 0)  # naive datetime in local timezone
        timespan_values = Quantity(np.ones(168, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        local_expanded_result = result.left_parent
        
        # Should exactly match the pattern since we start on Monday at hour 0 in UTC
        np.testing.assert_array_equal(result.magnitude, self.weekly_recurring_pattern.magnitude)
        self.assertEqual(result.start_date, datetime(2025, 1, 6, 0, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(result.unit, self.weekly_recurring_pattern.unit)
        self.assertIs(local_expanded_result.left_parent, self.weekly_recurring_pattern)
        self.assertIs(local_expanded_result.right_parent, timespan_hourly)
        self.assertEqual(local_expanded_result.operator, "expanded over timespan")
        self.assertEqual(result.operator, "converted to UTC from")
        self.assertEqual(result.label, "Weekly Pattern expanded over test timespan timespan (UTC)")

    def test_generate_over_one_week_wednesday_start(self):
        # Start on Wednesday 2025-01-08 00:00:00 local time (which is a Wednesday)
        start_date_local = datetime(2025, 1, 8, 0, 0, 0)  # Wednesday = weekday 2
        timespan_values = Quantity(np.ones(168, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        
        # Should start from Wednesday's pattern (index 2*24 = 48)
        expected_values = np.concatenate([
            self.weekly_recurring_pattern.magnitude[48:],  # Wed-Sun
            self.weekly_recurring_pattern.magnitude[:48]   # Mon-Tue
        ])
        
        np.testing.assert_array_equal(result.magnitude, expected_values)
        self.assertEqual(result.start_date, datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc))

    def test_generate_over_partial_week_with_hour_offset(self):
        # Start on Tuesday 2025-01-07 15:00:00 local time (Tuesday at 3 PM)
        start_date_local = datetime(2025, 1, 7, 15, 0, 0)  # Tuesday=1, hour=15
        timespan_values = Quantity(np.ones(25, dtype=np.float32), u.dimensionless)  # 25 hours
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        
        # Should start from Tuesday hour 15 (index 1*24 + 15 = 39)
        expected_start_index = 1 * 24 + 15  # Tuesday at 3 PM
        expected_values = []
        for i in range(25):
            week_index = (expected_start_index + i) % 168
            expected_values.append(self.weekly_recurring_pattern.magnitude[week_index])
        
        np.testing.assert_array_equal(result.magnitude, expected_values)
        self.assertEqual(len(result.value), 25)

    def test_generate_over_multiple_weeks(self):
        # Start on Monday and span 2.5 weeks (420 hours)
        start_date_local = datetime(2025, 1, 6, 0, 0, 0)
        timespan_values = Quantity(np.ones(420, dtype=np.float32), u.dimensionless)  # 2.5 weeks
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        
        # Pattern should repeat 2.5 times
        expected_values = np.tile(self.weekly_recurring_pattern.magnitude, 3)[:420]  # 2.5 weeks
        
        np.testing.assert_array_equal(result.magnitude, expected_values)
        self.assertEqual(len(result.value), 420)

    def test_invalid_recurring_pattern_length_raises_error(self):
        # Create pattern with wrong length (not 168)
        short_pattern = ExplainableRecurringQuantities(
            Quantity(np.array([1, 2, 3], dtype=np.float32), u.W), "Short"
        )
        
        start_date_local = datetime(2025, 1, 6, 0, 0, 0)
        timespan_values = Quantity(np.ones(24, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        with self.assertRaises(ValueError) as cm:
            short_pattern.generate_hourly_quantities_over_timespan(timespan_hourly, self.utc_timezone)
        
        self.assertIn("must have exactly 168 values", str(cm.exception))

    def test_with_timezone_aware_start_date_raises_assertion_error(self):
        start_date_utc_aware = datetime(2025, 1, 6, 0, 0, 0, tzinfo=timezone.utc)  # UTC timezone
        timespan_values = Quantity(np.ones(24, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_utc_aware, "test timespan")

        with self.assertRaises(AssertionError):
            _ = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
                timespan_hourly, self.utc_timezone)

    def test_edge_case_single_hour_timespan(self):
        # Test with single hour timespan
        start_date_local = datetime(2025, 1, 7, 10, 0, 0)  # Tuesday 10 AM
        timespan_values = Quantity(np.ones(1, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        
        # Should get value from Tuesday (weekday=1) hour 10: index = 1*24 + 10 = 34
        expected_index = 1 * 24 + 10
        expected_value = self.weekly_recurring_pattern.magnitude[expected_index]
        
        self.assertEqual(len(result.value), 1)
        self.assertEqual(result.magnitude[0], expected_value)

    def test_cross_week_boundary_alignment(self):
        # Start near end of week and cross into next week
        start_date_local = datetime(2025, 1, 12, 22, 0, 0)  # Sunday 10 PM
        timespan_values = Quantity(np.ones(10, dtype=np.float32), u.dimensionless)  # 10 hours
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.utc_timezone)
        
        # Sunday is weekday 6, so index starts at 6*24 + 22 = 166
        expected_values = []
        for i in range(10):
            week_index = (166 + i) % 168
            expected_values.append(self.weekly_recurring_pattern.magnitude[week_index])
        
        np.testing.assert_array_equal(result.magnitude, expected_values)

    def test_with_different_timezone_alignment(self):
        # Test with Paris timezone (UTC+1 in winter)
        # Start on Monday 2025-01-06 02:00:00 Paris time (which is 01:00:00 UTC)
        start_date_local = datetime(2025, 1, 6, 2, 0, 0)  # 2 AM Paris time
        timespan_values = Quantity(np.ones(24, dtype=np.float32), u.dimensionless)
        timespan_hourly = ExplainableHourlyQuantities(timespan_values, start_date_local, "test timespan")
        
        result = self.weekly_recurring_pattern.generate_hourly_quantities_over_timespan(
            timespan_hourly, self.paris_timezone)
        
        # Should start from Monday hour 2 in the local week pattern (index = 0*24 + 2 = 2)
        expected_start_index = 0 * 24 + 2  # Monday at 2 AM
        expected_values = []
        for i in range(24):
            week_index = (expected_start_index + i) % 168
            expected_values.append(self.weekly_recurring_pattern.magnitude[week_index])
        
        np.testing.assert_array_equal(result.magnitude, expected_values)
        # Output should be in UTC (1 AM UTC = 2 AM Paris time)
        self.assertEqual(result.start_date, datetime(2025, 1, 6, 1, 0, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()