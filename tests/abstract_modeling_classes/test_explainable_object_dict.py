import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_objects import EmptyExplainableObject


class TestExplainableObjectDict(unittest.TestCase):

    def setUp(self):
        self.mock_modeling_obj = MagicMock()
        self.mock_modeling_obj.id = "mock_id"
        self.mock_modeling_obj.name = "mock_modeling_obj"

        self.mock_explainable_obj = MagicMock(spec=ExplainableObject)
        self.mock_explainable_obj.id = "mock_explainable_id"
        self.mock_explainable_obj.to_json.return_value = {"key": "value"}

        self.mock_empty_obj = MagicMock(spec=EmptyExplainableObject)
        self.mock_empty_obj.id = "empty_obj_id"

        self.dict_obj = ExplainableObjectDict()

    def test_initialization(self):
        self.assertIsNone(self.dict_obj.modeling_obj_container)
        self.assertIsNone(self.dict_obj.attr_name_in_mod_obj_container)
        self.assertEqual(len(self.dict_obj), 0)

    def test_set_modeling_obj_container(self):
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")

        self.assertEqual(self.dict_obj.modeling_obj_container, self.mock_modeling_obj)
        self.assertEqual(self.dict_obj.attr_name_in_mod_obj_container, "attr_name")

        # Test setting a conflicting modeling object
        other_mock_modeling_obj = MagicMock()
        other_mock_modeling_obj.id = "other_mock_id"
        other_mock_modeling_obj.name = "other_mock_modeling_obj"

        with self.assertRaises(ValueError):
            self.dict_obj.set_modeling_obj_container(other_mock_modeling_obj, "another_attr")

    def test_all_ancestors_with_id(self):
        child_obj = MagicMock(spec=ExplainableObject)
        child_obj.all_ancestors_with_id = [MagicMock(id="ancestor_1"), MagicMock(id="ancestor_2")]
        child_obj2 = MagicMock(spec=ExplainableObject)
        child_obj2.all_ancestors_with_id = [MagicMock(id="ancestor_1"), MagicMock(id="ancestor_3")]
        self.dict_obj["child"] = child_obj
        self.dict_obj["child2"] = child_obj2

        ancestors = self.dict_obj.all_ancestors_with_id
        self.assertEqual(len(ancestors), 3)
        self.assertEqual(["ancestor_1", "ancestor_2", "ancestor_3"], [a.id for a in ancestors])

    def test_setitem_with_valid_value(self):
        self.dict_obj.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.dict_obj["key"] = self.mock_explainable_obj

        self.assertIn("key", self.dict_obj)
        self.mock_explainable_obj.set_modeling_obj_container.assert_called_with(
            new_modeling_obj_container=self.mock_modeling_obj, attr_name="attr_name"
        )

    def test_setitem_with_invalid_value(self):
        with self.assertRaises(ValueError):
            self.dict_obj["key"] = "Invalid value"

    def test_to_json(self):
        self.dict_obj[self.mock_explainable_obj] = self.mock_explainable_obj
        json_output = self.dict_obj.to_json()
        self.assertEqual(json_output, {"mock_explainable_id": {"key": "value"}})

    def test_repr(self):
        self.dict_obj[self.mock_explainable_obj] = self.mock_explainable_obj
        repr_output = repr(self.dict_obj)
        self.assertTrue("mock_explainable_id" in repr_output)
        self.assertTrue("key" in repr_output)

    def test_str(self):
        self.dict_obj[self.mock_explainable_obj] = self.mock_explainable_obj
        str_output = str(self.dict_obj)
        self.assertTrue("mock_explainable_id" in str_output)

if __name__ == "__main__":
    unittest.main()
