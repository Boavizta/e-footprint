import unittest
from unittest.mock import MagicMock, Mock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ModelingObjectForTesting(ModelingObject):
    def __init__(self, name, custom_input=None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input

    def after_init(self):
        self.trigger_modeling_updates = False

    def compute_calculated_attributes(self):
        pass

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []


class TestContextualModObjAttribute(unittest.TestCase):
    def test_contextual_modeling_object_attribute(self):
        custom_input = MagicMock(spec=ObjectLinkedToModelingObj)
        modeling_obj = ModelingObjectForTesting(name="TestObject", custom_input=custom_input)
        modeling_obj_container = ModelingObjectForTesting(name="container")

        contextual_attribute = ContextualModelingObjectAttribute(
            value=modeling_obj, modeling_obj_container=modeling_obj_container, attr_name_in_mod_obj_container="attr")

        self.assertTrue(isinstance(contextual_attribute, ModelingObject))
        self.assertEqual(custom_input, contextual_attribute.custom_input)
        self.assertEqual([], contextual_attribute.systems)

    def test_works_when_setting_attr_to_variable(self):
        custom_input = MagicMock(name="custom_input", spec=ObjectLinkedToModelingObj)
        modeling_obj = ModelingObjectForTesting(name="test", custom_input=custom_input)
        other_modeling_obj = ModelingObjectForTesting(name="other")

        modeling_obj.custom_input = other_modeling_obj

        self.assertTrue(isinstance(modeling_obj.custom_input, ContextualModelingObjectAttribute))
        self.assertEqual(modeling_obj.custom_input.modeling_obj_container, modeling_obj)

    def test_set_modeling_obj_container_with_new_parent(self):
        mock_value = Mock()
        mock_value.remove_obj_from_modeling_obj_containers = Mock()
        mock_value.add_obj_to_modeling_obj_containers = Mock()

        attr = ContextualModelingObjectAttribute(
            value=mock_value,
            modeling_obj_container=None,
            attr_name_in_mod_obj_container=None
        )

        new_mock_modeling_object = Mock()
        attr.set_modeling_obj_container(new_mock_modeling_object, "new_attr")

        mock_value.remove_obj_from_modeling_obj_containers.assert_not_called()
        mock_value.add_obj_to_modeling_obj_containers.assert_called_once_with(new_mock_modeling_object)
        self.assertEqual(attr.modeling_obj_container, new_mock_modeling_object)

    def test_set_modeling_obj_container_with_none_parent(self):
        mock_modeling_object = Mock()
        mock_value = Mock()
        mock_value.remove_obj_from_modeling_obj_containers = Mock()
        mock_value.add_obj_to_modeling_obj_containers = Mock()

        attr = ContextualModelingObjectAttribute(
            value=mock_value,
            modeling_obj_container=mock_modeling_object,
            attr_name_in_mod_obj_container="mock_attr"
        )

        attr.set_modeling_obj_container(None, None)

        mock_value.remove_obj_from_modeling_obj_containers.assert_called_once_with(mock_modeling_object)
        mock_value.add_obj_to_modeling_obj_containers.assert_not_called()
        self.assertIsNone(attr.modeling_obj_container)

    def test_set_modeling_obj_container_with_same_parent(self):
        mock_modeling_object = Mock()
        mock_value = Mock()
        mock_value.remove_obj_from_modeling_obj_containers = Mock()
        mock_value.add_obj_to_modeling_obj_containers = Mock()

        attr = ContextualModelingObjectAttribute(
            value=mock_value,
            modeling_obj_container=mock_modeling_object,
            attr_name_in_mod_obj_container="mock_attr"
        )

        attr.set_modeling_obj_container(mock_modeling_object, "same_attr")

        mock_value.remove_obj_from_modeling_obj_containers.assert_not_called()
        mock_value.add_obj_to_modeling_obj_containers.assert_called_once_with(mock_modeling_object)
        self.assertEqual(attr.modeling_obj_container, mock_modeling_object)