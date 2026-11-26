"""Registry of introductory modeling examples shipped with the library."""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


# @planned agent-guidance#example-discovery Add names, descriptions and script paths to introductory metadata and register the canonical reference model with its JSON and authoring wrapper.

@dataclass(frozen=True)
# @planned executable-modeling-documentation#catalogue Add names, descriptions, source_path, reading_path and doc_path to introductory entries while retaining their existing ids and JSON lookup.
class IntroductoryExample:
    id: str
    json_path: Path
    category: str = "introductory"


INTRODUCTORY_EXAMPLES: tuple[IntroductoryExample, ...] = (
    # @planned executable-modeling-documentation#edge-tutorial Register iot_industrial with its library-owned source, generated JSON and reading, and tutorial_edge.md as its tutorial destination.

    # @planned executable-modeling-documentation#ecommerce-tutorial Publish the e-commerce tutorial as tutorial.md, retaining the existing scenario id and packaged model lookup.

    IntroductoryExample(
        id="ecommerce",
        json_path=HERE / "ecommerce.json",
    ),
)
