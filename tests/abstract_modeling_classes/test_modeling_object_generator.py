import unittest
from unittest.mock import MagicMock, patch
from efootprint.abstract_modeling_classes.modeling_object_generator import ModelingObjectGenerator
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ModelingObjectGeneratorForTesting(ModelingObjectGenerator):
    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []

    def generate_mock_object(self, *args, **kwargs):
        return MagicMock(spec=ModelingObject)

    def non_generate_method_that_returns_a_modeling_object(self, *args, **kwargs):
        return MagicMock(spec=ModelingObject)


class TestModelingObjectGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = ModelingObjectGeneratorForTesting(name="TestGenerator")

    def test_initialization(self):
        self.assertEqual(self.generator.name, "TestGenerator")
        self.assertTrue(isinstance(self.generator, ModelingObjectGenerator))
        self.assertEqual(self.generator.generated_objects, {})
        self.assertTrue(self.generator.trigger_modeling_updates)

    def test_getattr_calls_and_tracking(self):
        result = self.generator.generate_mock_object(10, 20)

        self.assertTrue(result.generated_by, self.generator)
        self.assertIn(result, self.generator.generated_objects)
        self.assertEqual(self.generator.generated_objects[result], ["generate_mock_object", (10, 20), {}])

    def test_getattr_raises_error_for_non_generate_methods_that_return_a_modeling_object(self):
        with self.assertRaises(AssertionError):
            self.generator.non_generate_method_that_returns_a_modeling_object(10, 20)

    @patch('efootprint.abstract_modeling_classes.modeling_object_generator.ModelingUpdate')
    @patch('efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate')
    def test_setattr_updates_generated_objects(self, mock_modeling_update_1, mock_modeling_update_2):
        generated_object_1 = self.generator.generate_mock_object(10, 20)
        generated_object_2 = self.generator.generate_mock_object(30)
        generated_object_1.contextual_modeling_obj_containers = [MagicMock(modeling_obj_container=MagicMock())]
        generated_object_2.contextual_modeling_obj_containers = [MagicMock(modeling_obj_container=MagicMock())]

        self.assertDictEqual(self.generator.generated_objects,{
            generated_object_1: ["generate_mock_object", (10, 20), {}],
            generated_object_2: ["generate_mock_object", (30,), {}]
        })

        # Simulate setting an attribute that causes a regeneration of objects
        self.generator.some_attribute = "new_value"

        self.assertNotIn(generated_object_1, self.generator.generated_objects)
        self.assertNotIn(generated_object_2, self.generator.generated_objects)
        self.assertEqual(list(self.generator.generated_objects.values()),
                         [["generate_mock_object", (10, 20), {}], ["generate_mock_object", (30,), {}]])

        mock_modeling_update_1.assert_called_once()
        mock_modeling_update_2.assert_called_once()


if __name__ == "__main__":
    unittest.main()
