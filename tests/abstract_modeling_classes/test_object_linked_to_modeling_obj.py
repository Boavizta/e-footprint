import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ObjectLinkedToModelingObj


class TestObjectLinkedToModelingObj(unittest.TestCase):

    def setUp(self):
        self.mock_modeling_object = MagicMock()
        self.mock_modeling_object.id = "mock_model"

        # Create a concrete subclass of ObjectLinkedToModelingObj for testing
        class ConcreteObjectLinkedToModelingObj(ObjectLinkedToModelingObj):
            def set_modeling_obj_container(self, new_parent_modeling_object, attr_name):
                self.modeling_obj_container = new_parent_modeling_object
                self.attr_name_in_mod_obj_container = attr_name

        self.obj = ConcreteObjectLinkedToModelingObj()

    def test_replace_when_not_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.obj.belongs_to_dict = False

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)
        new_value.set_modeling_obj_container = MagicMock()

        self.obj.replace_by_new_value_in_mod_obj_container(new_value)

        self.assertEqual(new_value, getattr(self.mock_modeling_object, "test_attr"))
        new_value.set_modeling_obj_container.assert_called_once_with(self.mock_modeling_object, "test_attr")

    def test_replace_when_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        self.obj.belongs_to_dict = True
        self.obj.key_in_dict = "test_key"

        self.mock_modeling_object.__dict__["test_dict"] = {"test_key": "old_value"}

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)
        new_value.set_modeling_obj_container = MagicMock()

        self.obj.replace_by_new_value_in_mod_obj_container(new_value)

        self.assertEqual(self.mock_modeling_object.__dict__["test_dict"]["test_key"], new_value)
        new_value.set_modeling_obj_container.assert_called_once_with(self.mock_modeling_object, "test_dict")
        self.assertEqual(new_value.belongs_to_dict, True)
        self.assertEqual(new_value.key_in_dict, "test_key")

    def test_replace_with_no_modeling_obj_container(self):
        self.obj.modeling_obj_container = None
        new_value = MagicMock(spec=ObjectLinkedToModelingObj)

        with self.assertRaises(AttributeError):
            self.obj.replace_by_new_value_in_mod_obj_container(new_value)

    def test_replace_with_invalid_new_value(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.obj.belongs_to_dict = False

        new_value = object()  # Invalid, not an ObjectLinkedToModelingObj instance

        with self.assertRaises(AttributeError):
            self.obj.replace_by_new_value_in_mod_obj_container(new_value)

    def test_replace_when_key_not_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        self.obj.belongs_to_dict = True
        self.obj.key_in_dict = "missing_key"

        # Simulate dictionary attribute without the key
        self.mock_modeling_object.__dict__["test_dict"] = {}

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)

        with self.assertRaises(KeyError):
            self.obj.replace_by_new_value_in_mod_obj_container(new_value)

    def test_id_property_when_no_container(self):
        with self.assertRaises(ValueError) as context:
            _ = self.obj.id
        self.assertIn("doesn’t have a modeling_obj_container", str(context.exception))

    def test_id_property_when_container_is_set(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.assertEqual(self.obj.id, "test_attr-in-mock_model")


if __name__ == "__main__":
    unittest.main()
