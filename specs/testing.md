# Testing — e-footprint

This is the canonical testing guide. `tests/AGENTS.md` is a thin pointer to this file.

## Test layers

- **Unit tests** (in `tests/`) — individual `ModelingObject` classes in isolation. Focus: calculated attribute update methods (`update_*`), validation logic, error handling.
- **Integration tests** (in `tests/integration_tests/`) — complete system workflows. JSON serialization round-trips. Has its own `tests/integration_tests/AGENTS.md` for layer-specific patterns.
- **Performance tests** (in `tests/performance_tests/`) — large-system benchmarks.

## What NOT to test in unit tests

Things covered by integration tests are duplication:

- Initialization (unless special logic).
- `modeling_objects_whose_attributes_depend_directly_on_me` (unless special logic).
- Container/aggregation properties (unless special logic).
- `default_values` or `calculated_attributes` list contents.

Also don’t test:
- Inheritance or parent class methods.
- Shared base-class behavior already covered elsewhere.
- When a complex test implies simpler tests pass, skip the simpler tests.

Prefer the simplest readable test that proves the class-specific logic.

## What TO test in unit tests

1. **Update methods (`update_*`)** — happy path, error conditions, boundary cases.
2. **Validation logic.**
3. **Custom business logic** not covered by integration tests.

## Standard test file structure

```python
import unittest
from unittest import TestCase

from efootprint.core.path.to.class import ClassName
from efootprint.core.path.to.dependency import DependencyClass
from tests.utils import create_mod_obj_mock


class TestClassName(TestCase):
    def setUp(self):
        self.mock_dependency = create_mod_obj_mock(DependencyClass, "Mock Dependency")
        self.test_object = ClassName("test name", dependency=self.mock_dependency)

    def test_update_attribute_happy_path(self):
        """Test attribute update in normal conditions."""
        self.mock_dependency.value = 100
        self.mock_dependency.other_value = 50
        # Formula: attribute = value * 2 + other_value

        self.test_object.update_attribute()

        expected = 100 * 2 + 50  # 250
        self.assertEqual(expected, self.test_object.attribute)

    def test_update_attribute_invalid_input(self):
        """Test attribute update raises error for invalid input."""
        self.mock_dependency.value = -1

        with self.assertRaises(ValueError) as context:
            self.test_object.update_attribute()

        self.assertIn("must be positive", str(context.exception))


if __name__ == "__main__":
    unittest.main()
```

## Key principles

### Make tests self-contained

When testing update methods, set all input values **in the test itself** (or add a comment with the formula), so developers don't have to navigate back to setUp:

```python
# ✅ All values visible in test
def test_update_total_energy(self):
    """Test total energy calculation."""
    self.mock_component.power = 100  # watts
    self.mock_component.duration = 3600  # seconds
    # Formula: energy = power * duration

    self.test_object.update_total_energy()

    expected = 100 * 3600  # 360000 joules
    self.assertEqual(expected, self.test_object.total_energy)
```

### Use `create_mod_obj_mock` for ModelingObject mocks

Always use `create_mod_obj_mock` from `tests.utils`. It sets `spec`, `name`, `id`, and `explainable_object_dicts_containers` correctly:

```python
from tests.utils import create_mod_obj_mock

# ✅ CORRECT
mock_device = create_mod_obj_mock(EdgeDevice, "My device", power=SourceValue(100 * u.W))
```

If `create_mod_obj_mock` is missing an attribute your test needs, **extend `create_mod_obj_mock`** (in a backwards-compatible way) rather than patching at the test level. This keeps test utility centralized and avoids duplicating setup boilerplate.

Tests must adapt to production interfaces, not the reverse. If a production API changes, update test doubles and helpers to match the real contract — don't add production fallbacks purely to satisfy unrealistic test fixtures.

Prefer compact test setup. If a mocked `ModelingObject` fits cleanly on one line and stays under the 120 character limit, keep it on one line.

### Use real ExplainableObjects, not mocks

```python
# ✅ CORRECT
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.constants.units import u

real_value = ExplainableQuantity(100 * u.GB, "test value")
```

### Setting `modeling_obj_containers`

Cannot set directly (it's a property). Use the utility:

```python
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers

mock_container = create_mod_obj_mock(ContainerClass, "Mock container")
set_modeling_obj_containers(self.test_object, [mock_container])
```

### Mocking properties

Use `new_callable=PropertyMock`:

```python
from unittest.mock import patch, PropertyMock

@patch('module.ClassName.property_name', new_callable=PropertyMock)
def test_something(self, mock_property):
    mock_property.return_value = expected_value
```

When an object relationship property is not the focus of the test and recreating the full object graph would make the test heavier, patch that relationship property instead of rebuilding the whole structure.

### Object IDs in tests

`ModelingObject._use_name_as_id` is set to `True` in `tests/conftest.py`, so object IDs derive from names. This makes IDs predictable in tests but creates bugs when several objects share the same name (IDs are dict keys). **Give each object a unique name in tests, even if the name itself is not important.**

## Test naming and documentation

- **Method names:** `test_<method_or_attribute>_<scenario>`.
- **Docstrings:** always `"""Test <what> <under what conditions>."""`.

## Test isolation

- Make all changes to a test file at once when fixing/editing.
- If a test modifies shared state, either reset it at end or use a patch.
- For shared integration fixtures mutated in place: register a local rollback closure before mutation, run it unconditionally in `finally` or via `cleanup_stack()`.

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

For the common pattern "make a change, assert the impact, roll back, assert baseline restored", `cleanup_stack()` can carry the generic footprint assertions:

```python
with self.cleanup_stack(
    verify_changed_before_cleanup=[self.device],
    verify_unchanged_before_cleanup=[self.server, self.storage],
) as cleanup:
    cleanup.callback(...)
    ...
    self.assertNotEqual(self.system.total_footprint, self.initial_footprint)
```

`cleanup_stack()` always checks after rollback that `system.total_footprint` matches the initial baseline. Opt in to the pre-rollback check with `verify_total_footprint_changed_before_cleanup=True` for mutation tests where the system is expected to differ from baseline before cleanup.

## Matplotlib backend

When running tests that exercise plotting code, prefer:

```bash
MPLBACKEND=Agg poetry run pytest ...
```

In some shell environments, matplotlib tries to use the macOS GUI backend and aborts the Python process instead of failing cleanly.

## Important concepts

- **`default_values`:** parameters can be omitted in `.from_defaults()`, **not** in `__init__`.
- **ExplainableObjects:** without parents should have a label.

## Test impact repartition with non-trivial cases

For impact repartition tests, prefer exercising real share logic instead of only trivial one-need cases. If the code is supposed to split impact across sibling needs, include at least one test where a component has several needs so the proportional split is actually covered.

## When refactors change test shape

When a class is refactored to compute per-source dicts first and totals as sums, simplify tests to match: one focused test for per-source computation, one focused test for summation/property reuse. Don't keep older overlapping end-to-end tests.

## Layer-specific patterns

- `tests/AGENTS.md` — points here.
- `tests/integration_tests/AGENTS.md` — integration test patterns.
