# Testing Guidelines for e-footprint

Follow these patterns to write tests efficiently without needing to look up other test files or object dependencies.

## Test Organization

**Unit tests** (in `tests/`) test individual ModelingObject classes in isolation, focusing on:
- Calculated attribute update methods (update_* methods)
- Validation logic and error handling

**Integration tests** are in `tests/integration_tests/` - see `tests/integration_tests/AGENTS.md` for their patterns.

## What NOT to Test in Unit Tests

Don't waste time testing things covered by integration tests:
- Initialization (unless special logic)
- `modeling_objects_whose_attributes_depend_directly_on_me` property (unless special logic)
- Container/aggregation properties (unless special logic)
- `default_values` or `calculated_attributes` list
- Inheritance or parent class methods
- Shared base-class behavior already covered elsewhere in unit tests
- When a complex test implies simpler tests pass, skip the simpler tests

Prefer the simplest readable test that proves the class-specific logic. Avoid re-testing generic framework behavior in
every subclass test file.

## What TO Test in Unit Tests

Focus on:
1. **Update methods** (update_*) - happy path, error conditions, boundary cases
2. **Validation logic**
3. **Custom business logic** not covered by integration tests

## Standard Test File Structure

```python
import unittest
from unittest import TestCase

from efootprint.core.path.to.class import ClassName
from efootprint.core.path.to.dependency import DependencyClass
from tests.utils import create_mod_obj_mock


class TestClassName(TestCase):
    def setUp(self):
        # Create mocked ModelingObject dependencies with the shared utility
        self.mock_dependency = create_mod_obj_mock(DependencyClass, "Mock Dependency")

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

### Prefer create_mod_obj_mock for ModelingObject Mocks
When mocking ModelingObject subclasses, always use `create_mod_obj_mock` from `tests.utils` instead of raw `MagicMock`. It sets `spec`, `name`, `id`, and `explainable_object_dicts_containers` correctly:

```python
from tests.utils import create_mod_obj_mock

# ✅ CORRECT
mock_device = create_mod_obj_mock(EdgeDevice, "My device", power=SourceValue(100 * u.W))

# ❌ WRONG
mock_device = MagicMock(spec=EdgeDevice)
mock_device.name = "My device"
mock_device.id = "my-device"
mock_device.explainable_object_dicts_containers = []
mock_device.power = SourceValue(100 * u.W)
```

If `create_mod_obj_mock` is missing an attribute that your test needs, prefer extending `create_mod_obj_mock` (in a backwards-compatible way) rather than patching at the test level. This keeps test utility centralized and avoids duplicating setup boilerplate across tests.

Tests must adapt to production interfaces, not the reverse. If a production API changes, update test doubles and helpers
to match the real contract instead of adding production fallbacks purely to satisfy unrealistic test fixtures.

Prefer compact test setup. If a mocked ModelingObject fits cleanly on one line and stays under the 120 character
limit, keep it on one line.

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
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers

mock_container = create_mod_obj_mock(ContainerClass, "Mock container")
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

When an object relationship property is not the focus of the test and recreating the full object graph would make the
test heavier, patch that relationship property instead of rebuilding the whole structure.

### Object ids in tests
The ModelingObject class has a _use_name_as_id class attribute. It is set to True in tests/conftest.py, so that in a testing context, the id of an object is directly derived from its name. This makes it possible to have predictable ids in tests without needing to set them manually, but it can create bugs when several objects have the same name (because object ids are used as keys in dictionaries). To avoid this, make sure to give each object a unique name in tests, even if the name itself is not important for the test.

## Test Naming and Documentation

- **Method names**: `test_<method_or_attribute>_<scenario>`
- **Docstrings**: Always include: `"""Test <what> <under what conditions>."""`

## Test Isolation

When fixing, adding or editing tests, make all changes at once for a given test file.

If a test modifies shared state, either reset it at test end or use a patch. Shouldn’t be common since unit tests use setUp for fresh state.

When a test does mutate shared fixture state, prefer registering a local rollback closure before the mutation and run it
unconditionally in `finally` or through the integration `cleanup_stack()` helper. This keeps the original failure signal
while preventing unrelated cascade failures in later tests.

Pattern:

```python
def restore_job():
    current_jobs = [job for job in self.step.jobs if job.name == "job 2"]
    restored_job = current_jobs[0] if current_jobs else Job.from_defaults("job 2", server=self.server)
    self.step.jobs = [restored_job]

with self.cleanup_stack() as cleanup:
    cleanup.callback(restore_job)
    self.step.jobs = []
    self.job_2.self_delete()
```

Use this pattern especially when a shared integration fixture is mutated in place and must be restored locally rather
than rebuilt globally. Register the cleanup before the first mutation so it still runs if the test fails halfway
through.

For the common integration pattern "make a change, assert the intended impact, roll back, assert baseline is restored",
prefer pushing the generic footprint assertions into `cleanup_stack()` instead of open-coding them in the test body.

`cleanup_stack()` can assert footprint expectations in the mutated state right before rollback:

```python
with self.cleanup_stack(
    verify_changed_before_cleanup=[self.device],
    verify_unchanged_before_cleanup=[self.server, self.storage],
) as cleanup:
    cleanup.callback(...)
    ...
    self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
```

Use the test body for scenario-specific assertions that cannot be expressed generically. Use `cleanup_stack()` for the
repeated "these objects changed / these others stayed unchanged / everything returns to baseline" checks. Objects listed
in `verify_changed_before_cleanup` or `verify_unchanged_before_cleanup` are automatically checked again after cleanup to
ensure they are back to baseline. `cleanup_stack()` always checks after rollback that `system.total_footprint` matches
the initial baseline. If a test also wants to assert that the final mutated state differs from baseline before
rollback, opt in with `verify_total_footprint_changed_before_cleanup=True`.

In practice this opt-in should be the default choice for most mutation tests: the common pattern is "make a change,
assert that the system changed, then roll it back". Leave it as `False` only for scopes that intentionally end back at
baseline before cleanup, such as validation/error-path tests or multi-step tests that restore the original total
footprint within the body.

## Matplotlib Backend

When running test modules that exercise plotting code, prefer `MPLBACKEND=Agg poetry run pytest ...` in this environment.

Reason: in the current shell environment, `matplotlib` may try to use the macOS GUI backend and abort the Python process instead of failing cleanly.

## Important Concepts

- **default_values**: Parameters can be omitted in `.from_defaults()`, NOT in `__init__`
- **ExplainableObjects**: Without parents should have a label
