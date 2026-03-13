from datetime import datetime
import unittest

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u


class TestEmptyExplainableObject(unittest.TestCase):
    def setUp(self):
        self.empty_object = EmptyExplainableObject()
        self.quantity = ExplainableQuantity(2 * u.W, "2W")
        self.hourly_quantities = ExplainableHourlyQuantities(
            Quantity(np.array([1, 2, 3], dtype=np.float32), u.W),
            datetime.strptime("2025-01-01", "%Y-%m-%d"),
            "Hourly usage",
        )

    def test_truediv_with_explainable_quantity(self):
        result = self.empty_object / self.quantity

        self.assertIsInstance(result, EmptyExplainableObject)
        self.assertEqual(self.empty_object, result.left_parent)
        self.assertEqual(self.quantity, result.right_parent)
        self.assertEqual("/", result.operator)

    def test_truediv_with_explainable_hourly_quantities(self):
        result = self.empty_object / self.hourly_quantities

        self.assertIsInstance(result, EmptyExplainableObject)
        self.assertEqual(self.empty_object, result.left_parent)
        self.assertEqual(self.hourly_quantities, result.right_parent)
        self.assertEqual("/", result.operator)
