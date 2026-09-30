"""Registry of how-to modeling content shipped with the library.

Two decoupled concepts:

- ``HowToExample`` — a loadable reference ``System`` (serialized JSON) that backs
  the interface's example picker.
- ``HowToGuide`` — a how-to documentation page. Each guide references the
  ``example_id`` of the scenario it walks through; several guides can share one
  example (the database and server-to-server guides both read the ``ecommerce``
  scenario from different angles), which is why a guide is not the same thing as a
  example.
"""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


@dataclass(frozen=True)
class HowToExample:
    id: str
    name: str
    description: str
    json_path: Path
    category: str = "how_to"


HOW_TO_EXAMPLES: tuple[HowToExample, ...] = (
    HowToExample(
        id="machine_learning_workflow",
        name="Machine learning workflow",
        description="Training on a {class:GPUServer} plus recurrent inference jobs.",
        json_path=HERE / "machine_learning_workflow.json",
    ),
)


@dataclass(frozen=True)
class HowToGuide:
    id: str
    name: str
    doc_path: str
    example_id: str  # the picker example the guide walks through (guides may share one)


HOW_TO_GUIDES: tuple[HowToGuide, ...] = (
    HowToGuide(
        id="machine_learning_workflow",
        name="How to model a machine learning workflow",
        doc_path="machine_learning_workflow.md",
        example_id="machine_learning_workflow",
    ),
    HowToGuide(
        id="database_modeling",
        name="How to model a database",
        doc_path="database_modeling.md",
        example_id="ecommerce",
    ),
    HowToGuide(
        id="server_to_server_interaction",
        name="How to model server-to-server interaction",
        doc_path="server_to_server_interaction.md",
        example_id="ecommerce",
    ),
)
