import unittest

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_recurring_quantities import ExplainableRecurringQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
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
        np.testing.assert_array_equal(json_data["recurring_values"], self.recurring_quantity1.magnitude)

    def test_from_json_dict(self):
        json_data = {
            "recurring_values": [1.0, 2.0, 3.0],
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
            "recurring_values": [1.0, 2.0],
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


if __name__ == "__main__":
    unittest.main()