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
