import unittest
from unittest.mock import MagicMock

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObjBase
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from tests.utils import create_mod_obj_mock


class ModelingObjectForTesting(ModelingObject):
    default_values =  {}

    def __init__(self, name, custom_input: ObjectLinkedToModelingObjBase = None, mod_obj_input: ModelingObject = None):
        super().__init__(name)
        if custom_input is not None:
            self.custom_input = custom_input
        if mod_obj_input is not None:
            self.mod_obj_input = mod_obj_input

    @property
    def systems(self):
        return []


class OtherModelingObjectForTesting(ModelingObject):

    @property
    def systems(self):
        return []


class TestContextualModObjAttribute(unittest.TestCase):
    def test_contextual_modeling_object_attribute(self):
        custom_input = MagicMock(spec=ObjectLinkedToModelingObjBase)
        modeling_obj = ModelingObjectForTesting(name="TestObject", custom_input=custom_input)
        modeling_obj_container = ModelingObjectForTesting(name="container")

        contextual_attribute = ContextualModelingObjectAttribute(
            value=modeling_obj, modeling_obj_container=modeling_obj_container, attr_name_in_mod_obj_container="attr")

        self.assertTrue(isinstance(contextual_attribute, ModelingObject))
        self.assertEqual(custom_input, contextual_attribute.custom_input)
        self.assertEqual([], contextual_attribute.systems)

    def test_works_when_setting_attr_to_variable(self):
        custom_input = create_mod_obj_mock(ModelingObject, "mod obj input")
        modeling_obj = ModelingObjectForTesting(name="test", mod_obj_input=custom_input)
        other_modeling_obj = ModelingObjectForTesting(name="other")

        modeling_obj.mod_obj_input = other_modeling_obj

        self.assertTrue(isinstance(modeling_obj.mod_obj_input, ContextualModelingObjectAttribute))
        self.assertEqual(modeling_obj.mod_obj_input.modeling_obj_container, modeling_obj)

    def test_contextual_modeling_object_attribute_behaves_like_its_value_with_regards_to_isinstance(self):
        custom_input = MagicMock(spec=ObjectLinkedToModelingObjBase)
        modeling_obj = ModelingObjectForTesting(name="TestObject", custom_input=custom_input)
        contextual_attribute = ContextualModelingObjectAttribute(value=modeling_obj)

        self.assertTrue(isinstance(contextual_attribute, ModelingObject))
        self.assertTrue(isinstance(contextual_attribute, ContextualModelingObjectAttribute))
        self.assertTrue(isinstance(contextual_attribute, ObjectLinkedToModelingObjBase))
        self.assertFalse(isinstance(contextual_attribute, OtherModelingObjectForTesting))
