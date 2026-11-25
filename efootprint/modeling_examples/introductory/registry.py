"""Registry of introductory modeling examples shipped with the library."""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


# @planned agent-guidance#example-discovery Add names, descriptions and script paths to introductory metadata and register the canonical reference model with its JSON and authoring wrapper.

@dataclass(frozen=True)
class IntroductoryExample:
    id: str
    json_path: Path
    category: str = "introductory"


INTRODUCTORY_EXAMPLES: tuple[IntroductoryExample, ...] = (
    IntroductoryExample(
        id="ecommerce",
        json_path=HERE / "ecommerce.json",
    ),
)
