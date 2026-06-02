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
        id="machine_learning_workflow",
        name="Machine learning workflow",
        description="Training on a GPUServer plus recurrent inference jobs.",
        doc_path="machine_learning_workflow.md",
        json_path=HERE / "machine_learning_workflow.json",
    ),
)
