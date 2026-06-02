"""Registry of introductory modeling templates shipped with the library."""
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


@dataclass(frozen=True)
class IntroductoryTemplate:
    id: str
    json_path: Path
    category: str = "introductory"


INTRODUCTORY_TEMPLATES: tuple[IntroductoryTemplate, ...] = (
    IntroductoryTemplate(
        id="ecommerce",
        json_path=HERE / "ecommerce.json",
    ),
)
