/# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

e-footprint is a Python toolkit for modeling the environmental impact of digital services, focusing on carbon footprint from all digital services components, from devices to servers and storage, including network. The usage and fabrication phases of the life cycle analysis are taken into account. It uses a declarative modeling approach where objects automatically recalculate when their dependencies change.

## Development Commands

### Testing
```bash
# Run tests with coverage
export PYTHONPATH="./:$PYTHONPATH"
poetry run python -m pytest --cov=tests

# Run specific test
poetry run pytest tests/path/to/test_file.py
```

## Code Architecture

### Core Architecture (efootprint/core/)
- **Usage**: Usage patterns, journeys, and jobs that define how systems are used
- **Hardware**: Physical infrastructure components (servers, storage, networks, devices)
- **System**: Top-level container that manages usage patterns and calculates total environmental footprint

### Builders (efootprint/builders/)
Builder objects inherit from core objects and provide convenient ways to create complex systems with sensible defaults and / or connection to external data sources.

### Abstract Classes (efootprint/abstract_modeling_classes/)
The optimization layer that handles automatic recalculation:
- `ModelingObject`: Base class with dependency tracking and update logic between objects. All e-footprint objects inherit from this class.
- `ExplainableObject`: Base class that manages calculation graph, allowing automatic explanations and recomputation optimization
- `ExplainableQuantity`: Values with units, inherits from ExplainableObject
- `ExplainableHourlyQuantities`: Time-series data, inherits from ExplainableObject
- `ExplainableRecurrentQuantities`: Recurring quantities defined over a typical week period (168 hours), inherits from ExplainableObject.
- `EmptyExplainableObject`: Neutral numerical object, acts like zero or zero-like time-series data.

### API Utils (efootprint/api_utils/)
- `json_to_system.py`/`system_to_json.py`: Serialization for system persistence. Saves system with or without calculated attributes.
- `version_upgrade_handlers.py`: Migration logic for schema changes. The migration should apply to json system files saved without calculated attributes.

## Key Patterns

### Modeling object structure
All modeling objects define a default_values dictionary that specifies default values for numerical attributes, whose units are used for unit consistency checks. Calculated attributes are defined the calculated_attributes property, and each calculated attribute has a corresponding update_<attribute_name> method that implements the calculation logic. The __setattr__ override in ModelingObject ensures that when a numerical or object attribute is changed, all dependent calculated attributes are recomputed. The after_init method is called after the object is initialized to toggle recomputation dynamism and trigger calculations for some objects (notably the System class defined in efootprint/core/system.py, which is the top-level class.).

### Adding objects
New modeling objects (be it builder or core) need to be added to the ALL_EFOOTPRINT_CLASSES variable in efootprint/all_classes_in_order.py to ensure proper serialization and deserialization. In the same module, the CANONICAL_COMPUTATION_ORDER list contains only the top-level core objects that define in which order calculations should be performed when recalculating.

### Object Linking and Dependencies
Objects automatically track dependencies and trigger recalculation when inputs change. Object dependencies are managed through the modeling_objects_whose_attributes_depend_directly_on_me property in the ModelingObject class. When changing a numerical input, the calculation graph managed by ExplainableObject ensures only affected calculations are recomputed.
The ModelingUpdate object in efootprint/abstract_modeling_classes/modeling_update.py module handles all recomputation logic.

### Modeling Refactor Preferences
- When a modeling object needs different attribution rules for fabrication and usage, prefer explicit phase-specific calculated attributes and update methods over compatibility bridges or legacy fallback machinery.
- In `ModelingObject` subclasses that override `calculated_attributes`, prefer `super().calculated_attributes` and append local attributes rather than duplicating base-class-managed names.
- Prefer computing reusable per-pattern quantities once as calculated attributes, then aggregating from them. For example, if usage attribution depends on per-usage-pattern energy footprint, compute `*_per_usage_pattern` first and let totals sum that dict rather than recomputing the same formula in repartition methods.
- For fabrication repartition, do not introduce per-pattern calculated attributes when a simple proportional activity weight is sufficient. Fabrication and usage repartition weights do not need to be coherent with one another; they only need internal coherence within the same phase on the same object.
- Repartition weights do not need local normalization. Use direct proportional weights when possible and let final repartition normalization happen downstream.
- Units of repartition weights do not need to match across phases. They only need to remain Pint-coherent within a given phase/object weight set.
- When a costly aggregate is reused across several repartition calculations, prefer introducing a dedicated calculated attribute on the natural owning object rather than ad hoc helper caching. Example: component-level totals belong on `EdgeComponent`, not in a transient cache inside `EdgeDevice`.
- Prefer phase-specific logic that makes the allocated impact explicit over generic helpers with a `phase` switch when the underlying formula differs materially between fabrication and usage.
- If a structure or parent-level impact is evenly shared across children, keep that logic at the parent object level unless there is a strong ownership reason to move it. Do not pollute child attributes with parent-specific policy if a parent cached attribute can express it cleanly.

### Units and Calculations
All quantities use Pint for unit handling. Custom units are defined in `efootprint/constants/custom_units.txt`. Calculations are explainable with dependency graphs.

### Testing Strategy
- Unit tests for individual components in `tests/`
- Integration tests for complete system workflows in `tests/integration_tests/`
- Performance tests for large systems in `tests/performance_tests/`
- JSON serialization round-trip tests ensure persistence works correctly

## Development Guidelines

### Context gathering
- Developing new objects in e-footprint shouldn’t require deep knowledge of the optimization layer. Avoid gathering context from efootprint/abstract_modeling_classes/ unless absolutely necessary, prefer asking questions directly.
- When in doubt about how to implement a new feature, ask for guidance before starting implementation.
- You don’t necessarily need to understand all upstream and downstream dependencies of a given object to work on it. Focus on the immediate context of the object you are working on unless a broader focus is asked from you, and ask questions if needed.

### CLAUDE.md improvements
- If you notice that CLAUDE.md is missing important information that would allow for less context gathering in developments, please propose improvements so that less tokens can be used in the future but with same or better performance.

### Code Style
- Python 3.12+ required
- Black formatter with 120 character line length. Try to keep the number of lines low. In particular, avoid creating a new line to close a parenthesis.
- Poetry for dependency management
- Type hints encouraged but not strictly enforced. Don’t use forward references in ModelingObject __init__ signatures.
- Only use comments in code if there is a non-intuitive logic at play. If code is easy to understand, don’t comment. 
- Test code preferences are defined in efootprint/tests/CLAUDE.md.

### Testing Requirements  
Always run tests before committing changes. The codebase has comprehensive test coverage including performance benchmarks for large system models.
- When working in `tests/`, also read and follow `tests/AGENTS.md`.
- When working in `tests/integration_tests/`, also read and follow `tests/integration_tests/AGENTS.md`.
- In tests, when mocking e-footprint modeling objects, use `create_mod_obj_mock` from `tests/utils.py` instead of raw `MagicMock(spec=...)`, unless there is a specific reason not to.
- When using `create_mod_obj_mock`, prefer passing mocked attributes directly as keyword arguments at construction time, and keep simple fixture setup compact when readability is not harmed.
- Keep modeling tests focused on the exact code path under test. Avoid populating calculated attributes or fixture state that is no longer consumed by the method being tested.
- For impact repartition tests, prefer exercising real share logic instead of only trivial one-need cases. If the code is supposed to split impact across sibling needs, include at least one test where a component has several needs so the proportional split is actually covered.
