import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.modeling_object_mix import ModelingObjectMix
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

class TestModelingObjectMix(unittest.TestCase):
    def setUp(self):
        self.modeling_object_1 = MagicMock(spec=ModelingObject, id="obj1")
        self.modeling_object_2 = MagicMock(spec=ModelingObject, id="obj2")
        self.modeling_object_1.class_as_simple_str = "Network"
        self.modeling_object_2.class_as_simple_str = "Network"
        self.source_value_1 = SourceValue(0.5 * u.dimensionless)
        self.source_value_2 = SourceValue(0.5 * u.dimensionless)
        self.modeling_object_mix = ModelingObjectMix({
            self.modeling_object_1: self.source_value_1,
            self.modeling_object_2: self.source_value_2
        })

    def test_init_should_set_correct_values(self):
        self.assertEqual(self.modeling_object_mix[self.modeling_object_1], self.source_value_1)
        self.assertEqual(self.modeling_object_mix[self.modeling_object_2], self.source_value_2)

    def test_init_with_wrong_sum_of_weights_should_raise_assertion_error(self):
        modeling_object_3 = MagicMock(spec=ModelingObject, id="obj3")
        modeling_object_3.class_as_simple_str = "Network"
        source_value_3 = SourceValue(0.3 * u.dimensionless)
        with self.assertRaises(PermissionError):
            modeling_object_mix = ModelingObjectMix({
                self.modeling_object_1: self.source_value_1,
                self.modeling_object_2: self.source_value_2,
                modeling_object_3: source_value_3
            })

    def test_sum_of_weights_should_be_one(self):
        self.assertEqual(sum(list(self.modeling_object_mix.values())).value, 1 * u.dimensionless)

    def test_compute_weighted_attr_sum_should_return_correct_sum(self):
        self.modeling_object_1.some_attr = SourceValue(2 * u.dimensionless)
        self.modeling_object_2.some_attr = SourceValue(4 * u.dimensionless)
        result = self.modeling_object_mix.compute_weighted_attr_sum("some_attr")
        self.assertEqual(result.value, 3 * u.dimensionless)

    def test_set_modeling_obj_container_should_update_container(self):
        new_parent = MagicMock(spec=ModelingObject, id="parent")
        self.modeling_object_mix.set_modeling_obj_container(new_parent, "attr_name")
        for key in self.modeling_object_mix.keys():
            key.add_obj_to_modeling_obj_containers.assert_called_once_with(new_parent)
        for value in self.modeling_object_mix.values():
            self.assertEqual(value.modeling_obj_container, new_parent)
            self.assertEqual(value.attr_name_in_mod_obj_container, "attr_name")
        self.modeling_object_mix.set_modeling_obj_container(None, None)
        for key in self.modeling_object_mix.keys():
            key.remove_obj_from_modeling_obj_containers.assert_called_once_with(new_parent)
        for value in self.modeling_object_mix.values():
            self.assertEqual(value.modeling_obj_container, None)
            self.assertEqual(value.attr_name_in_mod_obj_container, None)

    def test_setitem_should_raise_permission_error_when_updates_not_allowed(self):
        self.modeling_object_mix.allow_updates = False
        with self.assertRaises(PermissionError):
            self.modeling_object_mix[self.modeling_object_1] = SourceValue(0.3 * u.dimensionless)

    def test_to_json_should_return_correct_json(self):
        expected_json = {
            "obj1": self.source_value_1.to_json(),
            "obj2": self.source_value_2.to_json()
        }
        self.assertEqual(self.modeling_object_mix.to_json(), expected_json)

    def test_delitem_should_raise_permission_error(self):
        with self.assertRaises(PermissionError):
            del self.modeling_object_mix[self.modeling_object_1]

    def test_pop_should_raise_permission_error(self):
        with self.assertRaises(PermissionError):
            self.modeling_object_mix.pop(self.modeling_object_1)

    def test_popitem_should_raise_permission_error(self):
        with self.assertRaises(PermissionError):
            self.modeling_object_mix.popitem()

    def test_clear_should_raise_permission_error(self):
        with self.assertRaises(PermissionError):
            self.modeling_object_mix.clear()

    def test_update_should_raise_permission_error(self):
        with self.assertRaises(PermissionError):
            self.modeling_object_mix.update({self.modeling_object_1: self.source_value_1})

    def test_copy_should_raise_not_implemented_error(self):
        with self.assertRaises(NotImplementedError):
            self.modeling_object_mix.copy()

    def test_eq_works_only_if_object_is_the_same(self):
        modeling_object_mix_1 = ModelingObjectMix({
            self.modeling_object_1: self.source_value_1,
            self.modeling_object_2: self.source_value_2
        })
        modeling_object_mix_2 = ModelingObjectMix({
            self.modeling_object_1: self.source_value_1,
            self.modeling_object_2: self.source_value_2
        })
        self.assertEqual(modeling_object_mix_2, modeling_object_mix_2)
        self.assertFalse(modeling_object_mix_1 == modeling_object_mix_2)


if __name__ == "__main__":
    unittest.main()