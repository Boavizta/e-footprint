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

### Key Components

#### Hardware Classes
- `Server`/`GPUServer`: Computing infrastructure with CPU/memory specs
- `Storage`: Persistent storage with capacity and type specifications  
- `Network`: Network infrastructure with bandwidth modeling
- `Device`: End-user devices (laptops, phones)

#### Usage Classes
- `UsagePattern`: Defines user behavior patterns over time
- `UsageJourney`: Represents a user's path through system interactions
- `UsageJourneyStep`: Individual interactions within a journey
- `Job`: Computational work executed on infrastructure

#### Services (efootprint/builders/services/)
High-level service builders for common scenarios:
- `WebApplication`: Web app modeling with request patterns
- `VideoStreaming`: Video streaming services with bandwidth modeling
- `GenAIModel`: Generative AI model inference with GPU requirements

### Abstract Classes (efootprint/abstract_modeling_classes/)
The optimization layer that handles automatic recalculation:
- `ModelingObject`: Base class with dependency tracking and update logic between objects
- `ExplainableObject`: Base class that manages calculation graph, allowing automatic explanations and recomputation optimization
- `ExplainableQuantity`: Values with units, inherits from ExplainableObject
- `ExplainableHourlyQuantities`: Time-series data, inherits from ExplainableObject
- `EmptyExplainableObject`: Neutral numerical object, acts like zero or zero-like time-series data.

### API Utils (efootprint/api_utils/)
- `json_to_system.py`/`system_to_json.py`: Serialization for system persistence
- `version_upgrade_handlers.py`: Migration logic for schema changes

## Key Patterns

### Object Linking and Dependencies
Objects automatically track dependencies and trigger recalculation when inputs change. When linking objects (e.g., assigning a server to a usage journey), the system ensures no object is linked to multiple systems simultaneously. The ModelingUpdate object in @efootprint/abstract_modeling_classes/modeling_update.py module handles all recomputation logic.

### Units and Calculations
All quantities use Pint for unit handling. Custom units are defined in `efootprint/constants/custom_units.txt`. Calculations are explainable with dependency graphs.

### Testing Strategy
- Unit tests for individual components in `tests/`
- Integration tests for complete system workflows in `tests/integration_tests/`
- Performance tests for large systems in `tests/performance_tests/`
- JSON serialization round-trip tests ensure persistence works correctly

## Development Guidelines

### Code Style
- Python 3.12+ required
- Black formatter with 120 character line length. Try to keep the number of lines low. In particular, avoid creating a new line to close a parenthesis.
- Poetry for dependency management
- Type hints encouraged but not strictly enforced
- Only use comments in code if there is a non-intuitive logic at play. If code is easy to understand, don’t comment. 

### Testing Requirements  
Always run tests before committing changes. The codebase has comprehensive test coverage including performance benchmarks for large system models.

### Documentation
The project uses MkDocs with generated API documentation. Tutorial notebooks demonstrate usage patterns and generate visualization examples.