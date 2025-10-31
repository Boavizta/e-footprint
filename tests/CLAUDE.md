# Testing Guidelines for e-footprint

Follow these patterns to write tests efficiently without needing to look up other test files or object dependencies.

## Test Organization

**Unit tests** (in `tests/`) test individual ModelingObject classes in isolation, focusing on:
- Calculated attribute update methods (update_* methods)
- Validation logic and error handling

**Integration tests** are in `tests/integration_tests/` - see `tests/integration_tests/CLAUDE.md` for their patterns.

## What NOT to Test in Unit Tests

Don't waste time testing things covered by integration tests:
- Initialization (unless special logic)
- `modeling_objects_whose_attributes_depend_directly_on_me` property (unless special logic)
- Container/aggregation properties (unless special logic)
- `default_values` or `calculated_attributes` list
- Inheritance or parent class methods
- When a complex test implies simpler tests pass, skip the simpler tests

## What TO Test in Unit Tests

Focus on:
1. **Update methods** (update_*) - happy path, error conditions, boundary cases
2. **Validation logic**
3. **Custom business logic** not covered by integration tests

## Standard Test File Structure

```python
import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.core.path.to.class import ClassName
from efootprint.core.path.to.dependency import DependencyClass


class TestClassName(TestCase):
    def setUp(self):
        # Create mocked dependencies with spec and name/id
        self.mock_dependency = MagicMock(spec=DependencyClass)
        self.mock_dependency.name = "Mock Dependency"
        self.mock_dependency.id = "mock_id"

        # Create the object under test
        self.test_object = ClassName("test name", dependency=self.mock_dependency)

    def test_update_attribute_happy_path(self):
        """Test attribute update in normal conditions."""
        # Setup: Set all values used in update function (don't rely on setUp)
        self.mock_dependency.value = 100
        self.mock_dependency.other_value = 50
        # Formula: attribute = value * 2 + other_value

        # Execute
        self.test_object.update_attribute()

        # Assert
        expected = 100 * 2 + 50  # 250
        self.assertEqual(expected, self.test_object.attribute)

    def test_update_attribute_invalid_input(self):
        """Test attribute update raises error for invalid input."""
        # Setup
        self.mock_dependency.value = -1  # Invalid: must be positive

        # Assert
        with self.assertRaises(ValueError) as context:
            self.test_object.update_attribute()

        self.assertIn("must be positive", str(context.exception))


if __name__ == "__main__":
    unittest.main()
```

## Key Principles

### Make Tests Self-Contained
**IMPORTANT**: When testing update methods, set all input values in the test itself (or add a comment with the formula), so developers don't have to go back to setUp to understand the test:

```python
# ✅ GOOD: All values visible in test
def test_update_total_energy(self):
    """Test total energy calculation."""
    self.mock_component.power = 100  # watts
    self.mock_component.duration = 3600  # seconds
    # Formula: energy = power * duration

    self.test_object.update_total_energy()

    expected = 100 * 3600  # 360000 joules
    self.assertEqual(expected, self.test_object.total_energy)

# ❌ BAD: Values hidden in setUp, developer must navigate there
def test_update_total_energy(self):
    """Test total energy calculation."""
    self.test_object.update_total_energy()
    self.assertEqual(360000, self.test_object.total_energy)
```

### Always Use spec Parameter for Mocks
```python
# ✅ CORRECT
mock_device = MagicMock(spec=EdgeDevice)

# ❌ WRONG
mock_device = MagicMock()
```

### Use Real ExplainableObjects, Not Mocks
```python
# ✅ CORRECT
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u

real_value = ExplainableQuantity(100 * u.GB, "test value")

# ❌ WRONG
mock_value = MagicMock(spec=ExplainableQuantity)
```

### Setting modeling_obj_containers
Cannot set directly (it's a property). Use the utility function:

```python
from tests.utils import set_modeling_obj_containers

mock_container = MagicMock(spec=ContainerClass)
set_modeling_obj_containers(self.test_object, [mock_container])
```

### Mocking Properties
Use `new_callable=PropertyMock`:

```python
from unittest.mock import patch, PropertyMock

@patch('module.ClassName.property_name', new_callable=PropertyMock)
def test_something(self, mock_property):
    mock_property.return_value = expected_value
```

## Test Naming and Documentation

- **Method names**: `test_<method_or_attribute>_<scenario>`
- **Docstrings**: Always include: `"""Test <what> <under what conditions>."""`

## Test Isolation

When fixing, adding or editing tests, make all changes at once for a given test file.

If a test modifies shared state, either reset it at test end or use a patch. Shouldn’t be common since unit tests use setUp for fresh state.

## Important Concepts

- **default_values**: Parameters can be omitted in `.from_defaults()`, NOT in `__init__`
- **ExplainableObjects**: Without parents should have a label
