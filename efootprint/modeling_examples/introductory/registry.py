"""Registry of introductory modeling examples shipped with the library."""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


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
