"""Documentation scope survives both source discovery and an actual pytest recording."""
import json

import pytest

from comprehension_harness.python.tests.conftest import REFERENCE_CALLS, source_index
from comprehension_harness.python.tests.test_collector import run_tests


@pytest.mark.parametrize("kind", ("product", "mechanism"))
@pytest.mark.parametrize("scope", (None, "doc"))
def test_narrative_scope_is_discovered_and_recorded_without_changing_the_run(project, kind, scope):
    decorator = "narrative.mechanism" if kind == "mechanism" else "narrative"
    option = ', scope="doc"' if scope else ""
    root = project({
        "comprehension.config.json": '{"cache": "cache", "stack": {"calls": "shop.narrate"}}',
        "pytest.ini": "[pytest]\n",
        "conftest.py": 'pytest_plugins = ["comprehension_harness.python.collector"]\n',
        "shop/narrate.py": REFERENCE_CALLS.read_text(),
        "shop/scenario.py": '''
            from shop.narrate import event, narrate

            def convert():
                event("The author converts a scenario.")
                narrate("Conversion preserves the source order.")
                return ["construction", "results"]
        ''',
        "checks/test_scenario.py": f'''
            from comprehension_harness.python.declare import narrative
            from shop.scenario import convert

            @{decorator}("A scenario is converted"{option})
            class TestScenario:
                """The scenario is the pattern for adding another example."""
                def test_converts(self):
                    assert convert() == ["construction", "results"]
        ''',
    })
    found = source_index(root, source="shop/", calls="shop.narrate",
                         declare="comprehension_harness.python.declare")
    assert found.returncode == 0, found.stderr
    declared = json.loads(found.stdout)["narratives"][0]
    assert declared.get("scope") == scope
    assert ("scope" in declared) == (scope is not None)

    run = run_tests(root)
    assert run.returncode == 0, run.stdout + run.stderr
    [story] = json.loads((root / "cache/stories/checks__test_scenario.py.json").read_text())
    assert story["narrative"] == {"title": "A scenario is converted", "kind": kind,
                                  **({"scope": scope} if scope else {})}
    assert [hit["kind"] for hit in story["hits"]] == ["event", "step"]
    assert story["state"] == "passed"


def test_an_unsupported_scope_is_rejected_by_discovery_and_the_decorator(project):
    root = project({
        "comprehension.config.json": '{"cache": "cache", "stack": {"calls": "shop.narrate"}}',
        "pytest.ini": "[pytest]\n",
        "conftest.py": 'pytest_plugins = ["comprehension_harness.python.collector"]\n',
        "shop/narrate.py": REFERENCE_CALLS.read_text(),
        "checks/test_scenario.py": '''
            from comprehension_harness.python.declare import narrative
            @narrative("A scenario is converted", scope="contributor")
            class TestScenario:
                def test_converts(self):
                    assert True
        ''',
    })
    found = source_index(root, declare="comprehension_harness.python.declare")
    assert found.returncode != 0
    assert 'scope="doc"' in found.stderr

    run = run_tests(root)
    assert run.returncode != 0
    assert 'scope is "doc" or None' in run.stdout + run.stderr
