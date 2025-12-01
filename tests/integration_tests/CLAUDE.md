# Integration tests pattern

Integration tests follow a pattern to make sure that the same tests are run on a system generated with code and the same system read from json.

## Test Structure

- The system from code test module and the system from json test module are defined respectively in `test_integration_[test_name].py` and `test_integration_[test_name]_from_json.py`.
- Both inherit from `IntegrationTest[TestName]BaseClass` defined in `integration_[test_name]_base_class.py`.
- Test methods are **auto-generated** by `AutoTestMethodsMeta` metaclass from `run_test_*` methods in the base class.

## Key Components

### AutoTestMethodsMeta (in integration_test_base_class.py)

A metaclass that auto-generates `test_*` methods from `run_test_*` methods in base classes:

```python
class IntegrationTestSimpleSystem(IntegrationTestSimpleSystemBaseClass, metaclass=AutoTestMethodsMeta):
    """Test methods are auto-generated from run_test_* methods in the base class."""
    pass
```

This eliminates hundreds of lines of boilerplate like:
```python
def test_foo(self): self.run_test_foo()
def test_bar(self): self.run_test_bar()
# ... repeated for every test
```

### SystemTestFixture (in integration_test_base_class.py)

A registry class that auto-discovers objects from a system:

```python
cls.fixture = SystemTestFixture(system)

# Access objects by name
cls.server = cls.fixture.get("Default server")

# Access by class type
all_servers = cls.fixture.get_all(Server)
first_server = cls.fixture.get_first(Server)

# Auto-initialize footprint tracking
(cls.initial_footprint, cls.initial_fab_footprints, cls.initial_energy_footprints,
 cls.initial_system_total_fab_footprint, cls.initial_system_total_energy_footprint) = \
    cls.fixture.initialize_footprints()
```

### Base Class Pattern

Each base class defines:

1. `generate_*_system()` - Static method that creates objects and returns `(system, start_date)`
2. `_setup_from_system(system, start_date)` - Shared setup logic using SystemTestFixture
3. `setUpClass()` - Calls generate then _setup_from_system
4. `run_test_*()` methods - Test implementations (auto-converted to `test_*` by metaclass)

### FromJson Variant

The FromJson variant overrides only `setUpClass()`:

```python
class IntegrationTestSimpleSystemFromJson(IntegrationTestSimpleSystemBaseClass, metaclass=AutoTestMethodsMeta):
    @classmethod
    def setUpClass(cls):
        system, start_date = cls.generate_simple_system()

        # Save to JSON and reload
        cls.system_json_filepath = os.path.join(INTEGRATION_TEST_DIR, "system_with_calculated_attributes.json")
        system_to_json(system, save_calculated_attributes=True, output_filepath=cls.system_json_filepath)
        with open(cls.system_json_filepath, "r") as file:
            system_dict = json.load(file)
        _, flat_obj_dict = json_to_system(system_dict)

        # Reuse the same setup logic
        reloaded_system = flat_obj_dict[system.id]
        cls._setup_from_system(reloaded_system, start_date)
```

## Adding New Objects to Integration Tests

When adding a new modeling class to integration tests:

1. **Add object creation** to `generate_*_system()` in the base class
2. **Add fixture.get() call** to `_setup_from_system()` if you need direct test access:
   ```python
   cls.my_new_object = cls.fixture.get("My Object Name")
   ```
3. **Footprints are auto-tracked** - no manual changes needed if the object has `energy_footprint` or `instances_fabrication_footprint`
4. **FromJson variant requires no changes** - it reuses `_setup_from_system()`
5. **Update `run_test_all_objects_linked_to_system()`** if present - add the new object to the expected list

## Adding New Tests

To add a new test:

1. Add a `run_test_*()` method to the base class
2. The metaclass automatically generates the corresponding `test_*()` method in both code and FromJson variants

No need to manually add `def test_foo(self): self.run_test_foo()` boilerplate.
