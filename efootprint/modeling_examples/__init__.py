"""Public API for the modeling-examples sub-package.

Examples are reference systems that ship with e-footprint and back the
how-to pages in the mkdocs documentation. Each is regenerable from a Python
constructor under ``how_to/_authoring/`` and loadable via ``json_to_system``.

Imports inside ``load_example_system`` are kept lazy so that authoring
scripts (under ``how_to/_authoring/``) can flip ``_use_name_as_id`` on the
``Source`` class before ``api_utils.json_to_system`` triggers
``constants.sources`` to instantiate the source singletons.
"""
from efootprint.modeling_examples.how_to.registry import (
    HOW_TO_GUIDES,
    HOW_TO_EXAMPLES,
    HowToGuide,
    HowToExample,
)
from efootprint.modeling_examples.introductory.registry import (
    INTRODUCTORY_EXAMPLES,
    IntroductoryExample,
)


def list_how_to_examples() -> list[HowToExample]:
    """Return the registered how-to examples with their metadata."""
    return list(HOW_TO_EXAMPLES)


def list_how_to_guides() -> list[HowToGuide]:
    """Return the how-to documentation guides with the example id each one walks through."""
    return list(HOW_TO_GUIDES)


def get_example(example_id: str) -> HowToExample:
    for example in HOW_TO_EXAMPLES:
        if example.id == example_id:
            return example
    raise KeyError(example_id)


def list_introductory_examples() -> list[IntroductoryExample]:
    """Return library-owned introductory examples with their metadata."""
    return list(INTRODUCTORY_EXAMPLES)


def get_introductory_example(example_id: str) -> IntroductoryExample:
    for example in INTRODUCTORY_EXAMPLES:
        if example.id == example_id:
            return example
    raise KeyError(example_id)


def load_example_system(example_id: str):
    import json
    from efootprint.api_utils.json_to_system import json_to_system
    example = get_example(example_id)
    with open(example.json_path) as f:
        class_obj_dict, _, _ = json_to_system(json.load(f))
    return next(iter(class_obj_dict["System"].values()))


def load_introductory_example_system(example_id: str):
    import json
    from efootprint.api_utils.json_to_system import json_to_system
    example = get_introductory_example(example_id)
    with open(example.json_path) as f:
        class_obj_dict, _, _ = json_to_system(json.load(f))
    return next(iter(class_obj_dict["System"].values()))
