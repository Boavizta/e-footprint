"""Registry of how-to modeling templates shipped with the library."""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


@dataclass(frozen=True)
class HowToTemplate:
    id: str
    name: str
    description: str
    doc_path: str
    json_path: Path
    category: str = "how_to"


HOW_TO_TEMPLATES: tuple[HowToTemplate, ...] = (
    HowToTemplate(
        id="database_modeling",
        name="Database modeling",
        description="A web service backed by a relational database, modeled as Storage attached to a Server.",
        doc_path="database_modeling.md",
        json_path=HERE / "database_modeling.json",
    ),
    HowToTemplate(
        id="machine_learning_workflow",
        name="Machine learning workflow",
        description="Training on a GPUServer plus recurrent inference jobs.",
        doc_path="machine_learning_workflow.md",
        json_path=HERE / "machine_learning_workflow.json",
    ),
    HowToTemplate(
        id="server_to_server_interaction",
        name="Server-to-server interaction",
        description="An outbound Job from one service triggering a Job on another.",
        doc_path="server_to_server_interaction.md",
        json_path=HERE / "server_to_server_interaction.json",
    ),
)
