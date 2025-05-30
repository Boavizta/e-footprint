import unittest
from unittest.mock import MagicMock, patch, PropertyMock, Mock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj


class TestObjectLinkedToModelingObj(unittest.TestCase):
    def setUp(self):
        self.mock_modeling_object = MagicMock()
        self.mock_modeling_object.id = "mock_model"
        self.obj = ObjectLinkedToModelingObj()

    def test_set_modeling_obj_container_with_new_parent(self):
        mock_modeling_object = Mock()
        mock_modeling_object.id = 1
        mock_modeling_object.name = "ModelingObject1"

        obj = ObjectLinkedToModelingObj()
        obj.set_modeling_obj_container(mock_modeling_object, "attr_name")

        self.assertEqual(obj.modeling_obj_container, mock_modeling_object)
        self.assertEqual(obj.attr_name_in_mod_obj_container, "attr_name")

    def test_set_modeling_obj_container_with_none_parent_and_non_none_attr_name_raises_error(self):
        obj = ObjectLinkedToModelingObj()

        with self.assertRaises(AssertionError):
            obj.set_modeling_obj_container(None, "attr_name")

    def test_set_modeling_obj_container_with_conflicting_parent(self):
        mock_modeling_object1 = Mock()
        mock_modeling_object1.id = 1
        mock_modeling_object1.name = "ModelingObject1"

        mock_modeling_object2 = Mock()
        mock_modeling_object2.id = 2
        mock_modeling_object2.name = "ModelingObject2"

        obj = ObjectLinkedToModelingObj()
        obj.set_modeling_obj_container(mock_modeling_object1, "attr_name")

        with self.assertRaises(ValueError) as context:
            obj.set_modeling_obj_container(mock_modeling_object2, "new_attr")

        self.assertIn(
            "A ObjectLinkedToModelingObj can’t be attributed to more than one ModelingObject", str(context.exception))

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    def test_replace_when_not_in_dict(self, mock_dict_container):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        mock_dict_container.return_value = None

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)
        new_value.set_modeling_obj_container = MagicMock()

        self.obj.replace_in_mod_obj_container_without_recomputation(new_value)

        self.assertEqual(new_value, getattr(self.mock_modeling_object, "test_attr"))
        new_value.set_modeling_obj_container.assert_called_once_with(self.mock_modeling_object, "test_attr")
        self.assertEqual(None, self.obj.modeling_obj_container)
        self.assertEqual(None, self.obj.attr_name_in_mod_obj_container)

    def test_dict_container(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        self.mock_modeling_object.test_dict = {"test_key": "test_value"}

        self.assertEqual(self.obj.dict_container, self.mock_modeling_object.test_dict)

    def test_key_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        test_key = "test_key"
        self.mock_modeling_object.test_dict = {test_key: self.obj}

        self.assertEqual(self.obj.key_in_dict, test_key)

    def test_key_in_dict_raises_error_if_obj_appears_more_than_once_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        test_key = "test_key"
        self.mock_modeling_object.test_dict = {test_key: self.obj, "another_key": self.obj}

        with self.assertRaises(ValueError):
            _ = self.obj.key_in_dict

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    @patch.object(ObjectLinkedToModelingObj, "key_in_dict", new_callable=PropertyMock)
    def test_replace_when_in_dict(self, mock_key_in_dict, mock_dict_container):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        key = "test_key"
        test_dict =  {key: "old_value"}
        mock_dict_container.return_value = test_dict
        mock_key_in_dict.return_value = key

        self.mock_modeling_object.test_dict = test_dict

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)
        new_value.set_modeling_obj_container = MagicMock()

        self.obj.replace_in_mod_obj_container_without_recomputation(new_value)

        self.assertEqual(self.mock_modeling_object.test_dict[key], new_value)

    def test_replace_with_no_modeling_obj_container(self):
        self.obj.modeling_obj_container = None
        new_value = MagicMock(spec=ObjectLinkedToModelingObj)

        with self.assertRaises(AssertionError):
            self.obj.replace_in_mod_obj_container_without_recomputation(new_value)

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    def test_replace_with_invalid_new_value(self, mock_dict_container):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        mock_dict_container.return_value = None

        new_value = object()  # Invalid, not an ObjectLinkedToModelingObj instance

        with self.assertRaises(AssertionError):
            self.obj.replace_in_mod_obj_container_without_recomputation(new_value)

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    def test_replace_with_object_of_non_related_class_raises_error(self, mock_dict_container):
        class ObjectLinkedToModelingObjChild(ObjectLinkedToModelingObj):
            pass
        class ObjectLinkedToModelingObjChild2(ObjectLinkedToModelingObj):
            pass
        obj = ObjectLinkedToModelingObjChild()
        obj.modeling_obj_container = self.mock_modeling_object
        obj.attr_name_in_mod_obj_container = "test_attr"
        mock_dict_container.return_value = None

        new_value = ObjectLinkedToModelingObjChild2()

        with self.assertRaises(AssertionError):
            obj.replace_in_mod_obj_container_without_recomputation(new_value)

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    def test_replace_with_object_of_related_class_works(self, mock_dict_container):
        class ObjectLinkedToModelingObjChild(ObjectLinkedToModelingObj):
            pass

        class ObjectLinkedToModelingObjChild2(ObjectLinkedToModelingObjChild):
            pass

        obj = ObjectLinkedToModelingObjChild()
        obj.modeling_obj_container = self.mock_modeling_object
        obj.attr_name_in_mod_obj_container = "test_attr"
        mock_dict_container.return_value = None

        new_value = ObjectLinkedToModelingObjChild2()

        obj.replace_in_mod_obj_container_without_recomputation(new_value)

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    def test_replace_with_emptyexplainableobject_works(self, mock_dict_container):
        obj = ObjectLinkedToModelingObj()
        obj.modeling_obj_container = self.mock_modeling_object
        obj.attr_name_in_mod_obj_container = "test_attr"
        mock_dict_container.return_value = None

        new_value = EmptyExplainableObject()

        obj.replace_in_mod_obj_container_without_recomputation(new_value)

    @patch.object(ObjectLinkedToModelingObj, "dict_container", new_callable=PropertyMock)
    @patch.object(ObjectLinkedToModelingObj, "key_in_dict", new_callable=PropertyMock)
    def test_replace_when_key_not_in_dict(self, mock_key_in_dict, mock_dict_container):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_dict"
        key_in_dict = MagicMock(id="test_id")
        test_dict = {}
        mock_dict_container.return_value = test_dict
        mock_key_in_dict.return_value = key_in_dict

        # Simulate dictionary attribute without the key
        self.mock_modeling_object.test_dict = test_dict

        new_value = MagicMock(spec=ObjectLinkedToModelingObj)

        with self.assertRaises(KeyError):
            self.obj.replace_in_mod_obj_container_without_recomputation(new_value)

    def test_id_property_when_no_container(self):
        with self.assertRaises(ValueError) as context:
            _ = self.obj.id
        self.assertIn("doesn’t have a modeling_obj_container", str(context.exception))

    def test_id_property_when_container_is_set(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.assertEqual(self.obj.id, "test_attr-in-mock_model")

    def test_dict_container_returns_none_when_non_dict_object_isnt_contained_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.mock_modeling_object.test_attr = self.obj

        self.assertEqual(self.obj.dict_container, None)

    def test_dict_container_returns_dict_when_object_is_contained_in_dict(self):
        self.obj.modeling_obj_container = self.mock_modeling_object
        self.obj.attr_name_in_mod_obj_container = "test_attr"
        self.mock_modeling_object.test_attr = {"test_key": self.obj}

        self.assertEqual(self.obj.dict_container, {"test_key": self.obj})

    def test_dict_container_returns_non_when_object_is_dict(self):
        dict_obj = ExplainableObjectDict({"test": MagicMock(spec=ExplainableObject)})
        dict_obj.modeling_obj_container = self.mock_modeling_object
        dict_obj.attr_name_in_mod_obj_container = "test_attr"
        self.mock_modeling_object.test_attr = dict_obj

        self.assertEqual(dict_obj.dict_container, None)


if __name__ == "__main__":
    unittest.main()
