import unittest
from unittest.mock import MagicMock, patch, Mock

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object_generator import ModelingObjectGenerator
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ModelingObjectGeneratorForTesting(ModelingObjectGenerator):
    def __init__(self, name: str, custom_input=None, depending_input=None):
        super().__init__(name)
        self.custom_input = custom_input
        self.depending_input = depending_input

    @classmethod
    def list_values(cls):
        return {
            "custom_input": ["val1", "val2"],
            "custom_arg": ["val3"]
        }

    @classmethod
    def conditional_list_values(cls):
        return {
            "depending_input": {
                "depends_on": "custom_input",
                "conditional_list_values": {
                    "val1": ["cond_val1", "cond_val2"],
                    "val2": ["cond_val3"]
                }
            }
        }

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return []

    @property
    def systems(self):
        return []

    def generate_mock_object(self, custom_arg, *args, **kwargs):
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
        result = self.generator.generate_mock_object("val3", 20)

        self.assertTrue(result.generated_by, self.generator)
        self.assertIn(result, self.generator.generated_objects)
        self.assertEqual(self.generator.generated_objects[result], ["generate_mock_object", ("val3", 20), {}])

    def test_getattr_raises_error_for_non_generate_methods_that_return_a_modeling_object(self):
        with self.assertRaises(AssertionError):
            self.generator.non_generate_method_that_returns_a_modeling_object("val3", 20)

    @patch('efootprint.abstract_modeling_classes.modeling_object_generator.ModelingUpdate')
    @patch('efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate')
    def test_setattr_updates_generated_objects(self, mock_modeling_update_1, mock_modeling_update_2):
        generated_object_1 = self.generator.generate_mock_object("val3", 20)
        generated_object_2 = self.generator.generate_mock_object(30)
        generated_object_1.contextual_modeling_obj_containers = [MagicMock(modeling_obj_container=MagicMock())]
        generated_object_2.contextual_modeling_obj_containers = [MagicMock(modeling_obj_container=MagicMock())]

        self.assertDictEqual(self.generator.generated_objects,{
            generated_object_1: ["generate_mock_object", ("val3", 20), {}],
            generated_object_2: ["generate_mock_object", (30,), {}]
        })

        # Simulate setting an attribute that causes a regeneration of objects
        self.generator.some_attribute = "new_value"

        self.assertNotIn(generated_object_1, self.generator.generated_objects)
        self.assertNotIn(generated_object_2, self.generator.generated_objects)
        self.assertEqual(list(self.generator.generated_objects.values()),
                         [["generate_mock_object", ("val3", 20), {}], ["generate_mock_object", (30,), {}]])

        mock_modeling_update_1.assert_called_once()
        mock_modeling_update_2.assert_called_once()

    def test_valid_static_value(self):
        mock_input = Mock(spec=ExplainableObject)
        mock_input.value = "val1"
        generator = ModelingObjectGeneratorForTesting(name="TestGenerator", custom_input=mock_input)

        self.assertEqual(generator.custom_input.value, "val1")

    def test_invalid_static_value(self):
        with self.assertRaises(ValueError) as context:
            mock_input = Mock(spec=ExplainableObject)
            mock_input.value = "valX"
            ModelingObjectGeneratorForTesting(name="TestGenerator", custom_input=mock_input)
        self.assertIn("is not in the list of possible values", str(context.exception))

    def test_conditional_dep_not_set_raises_error(self):
        with self.assertRaises(ValueError) as context:
            mock_input = Mock(spec=ExplainableObject)
            mock_input.value = "cond_val1"
            ModelingObjectGeneratorForTesting(name="TestGenerator", custom_input=mock_input)
        self.assertIn("is not in the list of possible values", str(context.exception))

    def test_valid_conditional_value(self):
        mock_input = Mock(spec=ExplainableObject)
        mock_input.value = "val1"
        depending_input = Mock(spec=ExplainableObject)
        depending_input.value = "cond_val1"

        generator = ModelingObjectGeneratorForTesting(
            name="TestGenerator", custom_input=mock_input, depending_input=depending_input)

        self.assertEqual(generator.depending_input.value, "cond_val1")

    def test_invalid_conditional_value(self):
        mock_input = Mock(spec=ExplainableObject)
        mock_input.value = "val1"
        depending_input = Mock(spec=ExplainableObject)
        depending_input.value = "invalid_value"

        with self.assertRaises(ValueError) as context:
            generator = ModelingObjectGeneratorForTesting(
                name="TestGenerator", custom_input=mock_input, depending_input=depending_input)

        self.assertIn("is not in the list of possible values for custom_input val1", str(context.exception))

    def test_generate_doesnt_work_with_invalid_arg(self):
        with self.assertRaises(ValueError):
            self.generator.generate_mock_object("invalid_value", 20)

    def test_generate_doesnt_work_with_invalid_kwarg(self):
        with self.assertRaises(ValueError):
            self.generator.generate_mock_object(custom_arg="invalid_value", arg1=20)

if __name__ == "__main__":
    unittest.main()
