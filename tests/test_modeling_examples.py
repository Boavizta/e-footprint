"""Tests for the ``efootprint.modeling_examples.how_to`` package.

Each test is parametrized over ``HOW_TO_EXAMPLES`` so adding a new example
automatically exercises load, compute, doc cross-references, and round-trip
stability against its authoring script.
"""
import importlib
import inspect
import json
from collections import Counter
from pathlib import Path

import pytest

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.timeseries import (
    ExplainableHourlyQuantitiesFromFormInputs,
    ExplainableRecurrentQuantitiesFromConstant,
)
from efootprint.modeling_examples import load_introductory_example_system, load_example_system
from efootprint.modeling_examples.how_to.registry import (
    HOW_TO_GUIDES, HOW_TO_EXAMPLES, HowToGuide, HowToExample)
from efootprint.modeling_examples.introductory.registry import (
    INTRODUCTORY_EXAMPLES,
    IntroductoryExample,
)

MKDOCS_SOURCEFILES = (
    Path(__file__).resolve().parent.parent / "docs_sources" / "mkdocs_sourcefiles")

# Every loadable scenario a guide may point at: how-to examples plus introductory ones.
LOADABLE_EXAMPLE_IDS = {t.id for t in HOW_TO_EXAMPLES} | {t.id for t in INTRODUCTORY_EXAMPLES}

_example_params = pytest.mark.parametrize(
    "example", HOW_TO_EXAMPLES, ids=lambda t: t.id)
_guide_params = pytest.mark.parametrize(
    "guide", HOW_TO_GUIDES, ids=lambda g: g.id)
_introductory_example_params = pytest.mark.parametrize(
    "example", INTRODUCTORY_EXAMPLES, ids=lambda t: t.id)


def _modeling_object_ids(system_data: dict) -> list[str]:
    metadata_keys = {"efootprint_version", "Sources"}
    return [
        payload["id"]
        for class_key, objects_by_id in system_data.items()
        if class_key not in metadata_keys
        for payload in objects_by_id.values()
    ]


def _assert_input_timeseries_are_editable_builders(system, example_id: str) -> None:
    checked = []
    for obj in [system, *system.all_linked_objects]:
        obj = obj._value if isinstance(obj, ContextualModelingObjectAttribute) else obj
        init_params = inspect.signature(type(obj).__init__).parameters
        for attr_name in init_params:
            if attr_name in ("self", "name") or not hasattr(obj, attr_name):
                continue
            value = getattr(obj, attr_name)
            if isinstance(value, ExplainableHourlyQuantities):
                assert isinstance(value, ExplainableHourlyQuantitiesFromFormInputs), (
                    f"{example_id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableHourlyQuantitiesFromFormInputs so it is editable in the interface.")
                assert value.form_inputs["modeling_duration_value"] == 3
                assert value.form_inputs["modeling_duration_unit"] == "year"
                checked.append((obj, attr_name))
            elif isinstance(value, ExplainableRecurrentQuantities):
                assert isinstance(value, ExplainableRecurrentQuantitiesFromConstant), (
                    f"{example_id}: {type(obj).__name__}.{attr_name} on {obj.name!r} must use "
                    "ExplainableRecurrentQuantitiesFromConstant so it is editable in the interface.")
                checked.append((obj, attr_name))
    assert checked, f"{example_id}: expected at least one input timeseries to validate."


@_example_params
def test_example_json_exists_and_loads(example: HowToExample):
    assert example.json_path.is_file(), f"{example.json_path} does not exist"
    with open(example.json_path) as f:
        json.load(f)


@_example_params
def test_example_modeling_object_ids_are_globally_unique(example: HowToExample):
    with open(example.json_path) as f:
        system_data = json.load(f)
    duplicates = [
        object_id for object_id, count in Counter(_modeling_object_ids(system_data)).items()
        if count > 1
    ]
    assert duplicates == [], (
        f"Example {example.id} has duplicate modeling-object ids: {duplicates}. "
        "Object ids are global in the interface cache, even across different classes.")


@_example_params
def test_example_loads_via_json_to_system(example: HowToExample):
    system = load_example_system(example.id)
    assert system is not None
    assert system.__class__.__name__ == "System"


@_example_params
def test_example_computes_total_footprint(example: HowToExample):
    system = load_example_system(example.id)
    assert not isinstance(system.total_footprint, EmptyExplainableObject), (
        f"Example {example.id} produced an empty total_footprint")


@_example_params
def test_example_input_timeseries_are_editable_builders(example: HowToExample):
    _assert_input_timeseries_are_editable_builders(load_example_system(example.id), example.id)


@_example_params
def test_authoring_script_round_trips_to_committed_json(example: HowToExample):
    authoring = importlib.import_module(
        f"efootprint.modeling_examples.how_to._authoring.{example.id}")
    freshly_built = system_to_json(
        authoring.build_system(), save_computed_state=False)
    with open(example.json_path) as f:
        committed = json.load(f)
    assert freshly_built == committed, (
        f"Example {example.id} JSON does not match the output of build_system(); "
        f"re-run `python -m efootprint.modeling_examples.how_to._authoring.{example.id}` "
        f"and commit the regenerated JSON.")


def test_example_metadata_schema():
    ids_seen: set[str] = set()
    for example in HOW_TO_EXAMPLES:
        for field in ("id", "name", "description"):
            value = getattr(example, field)
            assert isinstance(value, str) and value.strip(), (
                f"{example.id}.{field} must be a non-empty string")
        assert example.category == "how_to", f"{example.id} category must be 'how_to'"
        assert example.id not in ids_seen, f"Duplicate example id {example.id}"
        ids_seen.add(example.id)


def test_guide_metadata_schema():
    ids_seen: set[str] = set()
    for guide in HOW_TO_GUIDES:
        for field in ("id", "name", "doc_path", "example_id"):
            value = getattr(guide, field)
            assert isinstance(value, str) and value.strip(), (
                f"{guide.id}.{field} must be a non-empty string")
        assert guide.id not in ids_seen, f"Duplicate guide id {guide.id}"
        ids_seen.add(guide.id)


@_guide_params
def test_guide_example_id_resolves_to_a_loadable_example(guide: HowToGuide):
    assert guide.example_id in LOADABLE_EXAMPLE_IDS, (
        f"Guide {guide.id} points at example {guide.example_id!r}, which is neither a how-to "
        f"nor an introductory example; the interface would 404 its 'Load this scenario' link.")


@_guide_params
def test_guide_doc_path_exists(guide: HowToGuide):
    target = MKDOCS_SOURCEFILES / guide.doc_path
    assert target.is_file(), (
        f"Guide {guide.id} doc_path {target} does not exist; "
        f"the prose track must land the matching How-to page.")


@_guide_params
def test_how_to_page_references_its_example(guide: HowToGuide):
    """The How-to page must deep-link to the picker example it walks through."""
    text = (MKDOCS_SOURCEFILES / guide.doc_path).read_text()
    assert "interface_base_url" in text and f"/example/{guide.example_id}/" in text, (
        f"How-to page {guide.doc_path} does not link to example {guide.example_id} via "
        f"the interface_base_url /example/<id>/ deep link.")


@_introductory_example_params
def test_introductory_example_json_exists_and_loads(example: IntroductoryExample):
    assert example.json_path.is_file(), f"{example.json_path} does not exist"
    with open(example.json_path) as f:
        json.load(f)


@_introductory_example_params
def test_introductory_example_loads_via_json_to_system(example: IntroductoryExample):
    system = load_introductory_example_system(example.id)
    assert system is not None
    assert system.__class__.__name__ == "System"


@_introductory_example_params
def test_introductory_example_input_timeseries_are_editable_builders(example: IntroductoryExample):
    _assert_input_timeseries_are_editable_builders(load_introductory_example_system(example.id), example.id)


@_introductory_example_params
def test_introductory_authoring_script_round_trips_to_committed_json(example: IntroductoryExample):
    authoring = importlib.import_module(
        f"efootprint.modeling_examples.introductory._authoring.{example.id}")
    freshly_built = system_to_json(
        authoring.build_system(), save_computed_state=False)
    with open(example.json_path) as f:
        committed = json.load(f)
    assert freshly_built == committed, (
        f"Introductory example {example.id} JSON does not match the output of build_system(); "
        f"re-run `python -m efootprint.modeling_examples.introductory._authoring.{example.id}` "
        f"and commit the regenerated JSON.")
