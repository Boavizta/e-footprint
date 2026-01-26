import unittest
from copy import deepcopy
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u


class TestExplainableQuantity(unittest.TestCase):
    def setUp(self):
        self.a = ExplainableQuantity(1 * u.W, "1 Watt")
        self.b = ExplainableQuantity(2 * u.W, "2 Watt")
        self.c = self.a + self.b
        self.c.set_label("int calc")
        self.d = self.c + self.b
        self.d.set_label("int calc 2")
        self.e = ExplainableQuantity(3 * u.W, "e")
        for index, explainable_quantity in enumerate([self.a, self.b, self.e]):
            explainable_quantity.modeling_obj_container = MagicMock(name="name", id=f"id{index}")
            explainable_quantity.attr_name_in_mod_obj_container = "test_attr"
        self.f = self.a + self.b + self.e

    def test_compute_calculation(self):
        self.assertEqual([self.a, self.b, self.e], self.f.direct_ancestors_with_id)

    def test_init(self):
        self.assertEqual(self.a.value, 1 * u.W)
        self.assertEqual(self.a.label, "1 Watt")
        self.assertEqual(self.a.left_parent, None)
        self.assertEqual(self.a.right_parent, None)
        self.assertEqual(self.a.operator, None)

        self.assertEqual(self.c.value, 3 * u.W)
        self.assertEqual(self.c.label, "int calc")
        self.assertEqual(self.c.left_parent, self.a)
        self.assertEqual(self.c.right_parent, self.b)
        self.assertEqual(self.c.operator, '+')

    def test_operators(self):
        self.assertEqual(self.c.value, 3 * u.W)
        self.assertRaises(ValueError, self.a.__add__, 1)
        self.assertRaises(ValueError, self.a.__gt__, 1)
        self.assertRaises(ValueError, self.a.__lt__, 1)
        self.assertFalse(self.a == 1)

    def test_to(self):
        self.a.to(u.mW)
        self.assertEqual(self.a.value, 1000 * u.mW)

    def test_magnitude(self):
        self.assertEqual(self.a.magnitude, 1)

    def test_add_with_0(self):
        self.assertEqual(self.a, self.a + 0)

    def test_subtract_0(self):
        self.assertEqual(self.a, self.a - 0)

    def test_to_json(self):
        self.assertDictEqual({"label": "1 Watt", "value": 1, "unit": "watt"}, self.a.to_json())

    def test_to_json_with_calculated_attributes_after_init_from_json_doesnt_update_json_data(self):
        json_data = {"label": "1 Watt", "value": 1, "unit": "watt"}
        obj = ExplainableQuantity.from_json_dict(json_data)
        json_output = obj.to_json(save_calculated_attributes=True)
        self.assertIn("direct_ancestors_with_id", json_output)
        self.assertNotIn("direct_ancestors_with_id", obj.json_value_data)
        self.assertNotIn("direct_ancestors_with_id", obj.to_json(save_calculated_attributes=False))

    def test_ceil(self):
        self.a = ExplainableQuantity(1.5 * u.W, "1.5 Watt")
        self.assertEqual(2 * u.W, self.a.ceil().value)

    def test_copy(self):
        copied = self.a.copy()
        self.assertNotEqual(id(self.a), id(copied))
        self.assertEqual(self.a.value, copied.value)
        self.assertEqual(self.a.label, copied.label)
        self.assertEqual(None, copied.modeling_obj_container)
        self.assertEqual(id(self.a), id(copied.left_parent))
