"""Intended sequences are static until their reference test and named steps are written."""
import json

import pytest

from comprehension_harness.python.tests.conftest import REFERENCE_CALLS, source_index
from comprehension_harness.python.tests.test_collector import run_tests


def files(planned=True, order=("checkout:read", "checkout:write")):
    calls = '''
from shop.narrate import event, narrate, planned

def checkout():
    narrate.planned("checkout:read", "The input is **read**.", changes=("checkout#save:input",))
    narrate.planned("checkout:write", "The result is **written**.")
    planned("checkout#save:input", "Read the input before saving.")
    raise NotImplementedError("planned: checkout#save")
'''
    if not planned:
        calls = 'from shop.narrate import event, narrate\n\ndef checkout():\n    event("The customer checks out.")\n'
        calls += ''.join(f'    narrate("The result is processed.", step="{step}")\n' for step in order)
        calls += '    return 3\n'
    reference = '''
from shop.checkout import checkout
from comprehension_harness.python.declare import canonical, narrative, planned_test, titled

@narrative("The customer checks out")
class TestCheckout:
    """The input precedes the saved result."""

    @canonical(steps=("checkout:read", "checkout:write"))
    @planned_test("checkout#save: A checkout reads then writes")
    def test_checkout(self):
        pass
'''
    if not planned:
        reference = reference.replace('@planned_test(', '@titled(').replace('        pass', '        assert checkout() == 3')
    return {
        "comprehension.config.json": '{"cache":"cache","stack":{"calls":"shop.narrate"}}',
        "conftest.py": 'pytest_plugins = ["comprehension_harness.python.collector"]\n',
        "pytest.ini": "[pytest]\n",
        "shop/narrate.py": REFERENCE_CALLS.read_text(),
        "shop/checkout.py": calls,
        "checks/test_checkout.py": reference,
    }


def index(root):
    return source_index(root, source="shop/", tests="checks/", calls="shop.narrate",
                        declare="comprehension_harness.python.declare")


def test_planned_steps_keep_shells_and_the_reference_sequence_without_a_run(project):
    root = project(files())
    done = index(root)
    assert done.returncode == 0, done.stderr
    doc = json.loads(done.stdout)
    steps = doc["files"]["shop/checkout.py"]["sites"]
    assert [s["narration"]["id"] for s in steps[:2]] == ["checkout:read", "checkout:write"]
    assert steps[0]["narration"] == {"id": "checkout:read", "planned": True, "changes": ["checkout#save:input"]}
    assert steps[2]["planned"]["change"] == "added"
    assert steps[2]["planned"]["signature"] == "def checkout():"
    assert doc["narratives"][0]["intended"] == {
        "steps": ["checkout:read", "checkout:write"], "planned": True,
        "test": "checkout#save: A checkout reads then writes"}
    tested = run_tests(root)
    assert tested.returncode == 0 and "1 skipped" in tested.stdout, tested.stdout + tested.stderr
    assert not (root / "cache/stories/checks__test_checkout.py.json").exists()


@pytest.mark.parametrize("order, passes", [
    (("checkout:read", "checkout:write"), True),
    (("checkout:write", "checkout:read"), False),
    (("checkout:read",), False),
])
def test_promoted_reference_enforces_the_observed_sequence(project, order, passes):
    root = project(files(False, order))
    indexed = index(root)
    assert indexed.returncode == 0, indexed.stderr
    assert json.loads(indexed.stdout)["narratives"][0]["intended"]["planned"] is False
    done = run_tests(root)
    assert (done.returncode == 0) is passes, done.stdout + done.stderr
    if not passes:
        assert "Narrative reference sequence differs" in done.stdout
    story = json.loads((root / "cache/stories/checks__test_checkout.py.json").read_text())[0]
    assert [h["step"] for h in story["hits"] if "step" in h] == list(order)


@pytest.mark.parametrize("before, after, message", [
    ('"checkout:read", "The input is **read**."', 'make_id(), "The input is **read**."', 'step id'),
    ('changes=("checkout#save:input",)', 'changes=collect_links()', 'literal tuples'),
    ('changes=("checkout#save:input",)', 'changes=("checkout#save",)', 'change place'),
    ('steps=("checkout:read", "checkout:write")', 'steps=("checkout:read", "checkout:read")', 'not repeated'),
    ('steps=("checkout:read", "checkout:write")', 'steps=()', 'at least one'),
])
def test_the_source_refuses_computed_or_ambiguous_intent(project, before, after, message):
    inputs = {file: text.replace(before, after) for file, text in files().items()}
    done = index(project(inputs))
    assert done.returncode != 0 and message in done.stderr, done.stderr


def test_an_intended_step_records_nothing_even_with_a_collector():
    from comprehension_harness.python.narrate import install_collector, narrate
    hits = []
    install_collector(lambda *args, **kwargs: hits.append(args))
    try:
        narrate.planned("checkout:read", "The input is read.")
        assert hits == []
    finally:
        install_collector(None)


def test_shell_detection_ignores_intended_declarations_on_either_side_of_its_raise(project):
    inputs = files()
    source = inputs["shop/checkout.py"]
    step = '    narrate.planned("checkout:write", "The result is **written**.")\n'
    inputs["shop/checkout.py"] = source.replace(step, '') + step
    done = index(project(inputs))
    assert done.returncode == 0, done.stderr
    sites = json.loads(done.stdout)["files"]["shop/checkout.py"]["sites"]
    assert next(site for site in sites if site["kind"] == "planned")["planned"]["change"] == "added"
