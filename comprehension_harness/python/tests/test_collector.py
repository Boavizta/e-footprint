"""The collector of the Python stack: the story `collector.py` writes for a test that crosses a site.

A small project is run by its own pytest process, as a test run is, and its story file is read back.
"""
import json
import os
import subprocess
import sys

import pytest

from comprehension_harness.python.tests.conftest import REFERENCE_CALLS, ROOT, run_stack, source_index

CHECKOUT = '''
    from shop.narrate import event, narrate, planned


    def pay(amount):
        event("The customer presses Pay.")
        planned("gift-cards#deduct-the-card", "The amount due **loses the card's balance**.")
        return charge(amount)


    def charge(amount):
        narrate("The amount **is charged**.",
                lambda: {"amount": amount, "seen": {2, 1}})
        return {"charged": amount}


    def audit(amounts):
        for amount in amounts:
            narrate("Each amount is **audited**.", lambda: {"ratio": 1 / amount})
'''
PROJECT = {
    "comprehension.config.json": '{"cache": "cache", "stack": {"calls": "shop.narrate"}}',
    # A project's calls are its own copy of the reference, in its own package.
    "shop/narrate.py": REFERENCE_CALLS.read_text(),
    "pytest.ini": "[pytest]\n",
    "conftest.py": 'pytest_plugins = ["comprehension_harness.python.collector"]\n',
    "cache/stories/checks__test_quiet.py.json": "[]",
    "shop/checkout.py": CHECKOUT,
    "checks/test_quiet.py": "def test_crosses_nothing():\n    assert True\n",
    "checks/test_checkout.py": '''
        import pytest
        from shop.checkout import audit, pay
        from comprehension_harness.python.declare import canonical, narrative, planned_test, titled


        @narrative("The customer pays a basket")
        class TestPay:
            """The amount is what is charged."""

            def test_crosses_nothing(self):
                assert True

            @canonical
            def test_charges_the_amount(self):
                assert pay(3) == {"charged": 3}

            @pytest.mark.parametrize("amount", [1, 2])
            def test_charges_any_amount(self, amount):
                assert pay(amount)


        @titled("gift-cards#audit: every amount is audited")
        def test_audit():
            audit([0] + [1] * 59)


        @planned_test("gift-cards#refund-to-card: a refund goes back to the card first")
        def test_refund():
            """To write."""
    ''',
}
TEST_FILE = "checks/test_checkout.py"
CALLS, DECLARE = "from shop.narrate import", "from comprehension_harness.python.declare import"


def run_tests(root, *options) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONPATH": str(ROOT)}
    command = [sys.executable, "-m", "pytest", "checks", "-q", "-p", "no:django", "-p", "no:cacheprovider", *options]
    return subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True)


def stories_of(root) -> list[dict]:
    return json.loads((root / "cache/stories/checks__test_checkout.py.json").read_text())


def test_a_story_is_what_its_test_crossed_and_a_test_file_has_one_story_file(project):
    root = project(PROJECT)
    done = run_tests(root)
    assert done.returncode == 0 and "6 passed, 1 skipped" in done.stdout, done.stdout + done.stderr

    # A file with no story writes no file, and the story an earlier run left for it is gone.
    assert sorted(file.name for file in (root / "cache/stories").iterdir()) == ["checks__test_checkout.py.json"]
    stories = stories_of(root)
    assert [story["test"] for story in stories] == [
        "test_charges_the_amount", "test_charges_any_amount[1]", "test_charges_any_amount[2]",
        "gift-cards#audit: every amount is audited"]
    assert [story["order"] for story in stories] == sorted(story["order"] for story in stories)
    assert {(story["file"], story["state"]) for story in stories} == {(TEST_FILE, "passed")}
    assert all(story["durationMs"] >= 0 for story in stories)
    narrative = {"title": "The customer pays a basket", "kind": "product"}
    assert [(story["narrative"], story["canonical"]) for story in stories] == [
        (narrative, True), (narrative, False), (narrative, False), (None, False)]


def test_a_hit_is_its_call_as_the_source_index_has_it_with_the_frames_above(project):
    root = project(PROJECT)
    run_tests(root)
    declare = "comprehension_harness.python.declare"
    printed = source_index(root, source="shop/", calls="shop.narrate", declare=declare).stdout
    index = json.loads(printed)
    sites = {site["line"]: site for site in index["files"]["shop/checkout.py"]["sites"]}

    hits = stories_of(root)[0]["hits"]
    assert [hit["kind"] for hit in hits] == ["event", "planned", "step"]
    for hit in hits:
        site = sites[hit["site"]["line"]]
        assert hit["site"] == {"file": "shop/checkout.py", **{key: site[key] for key in ("line", "column", "fn")}}
        assert (hit["kind"], hit["sentence"]) == (site["kind"], site["sentence"]) and hit["atMs"] >= 0
    assert hits[1]["planned"] == {"feature": "gift-cards", "slug": "deduct-the-card", "change": "changed"}
    # The repository's frames above the call, nearest first, named as the index names functions.
    assert hits[2]["watch"] == {"amount": 3, "seen": [1, 2]}
    assert [(frame["file"], frame["line"], frame["fn"]) for frame in hits[2]["stack"]] == [
        ("shop/checkout.py", 7, "pay"), (TEST_FILE, 15, "TestPay.test_charges_the_amount")]
    # One title a test: the story's, the index's first test, the title reader's.
    assert index["narratives"][0]["firstTest"] == "test_crosses_nothing"
    asked = json.dumps([{"file": TEST_FILE, "text": (root / TEST_FILE).read_text()}])
    [titles] = json.loads(run_stack("titles", stdin=asked).stdout)
    assert {story["test"].split("[")[0] for story in stories_of(root)} <= {test["title"] for test in titles["tests"]}


def test_a_watch_that_raises_is_recorded_and_a_site_keeps_its_first_fifty_hits(project):
    root = project(PROJECT)
    run_tests(root)

    audit = stories_of(root)[3]
    assert audit["state"] == "passed"
    assert audit["hits"][0]["watch"] == {"error": "ZeroDivisionError: division by zero"}
    assert audit["hits"][1]["watch"] == {"ratio": 1.0}
    assert len(audit["hits"]) == 50
    assert audit["capped"] == [{"file": "shop/checkout.py", "line": 18, "kept": 50, "omitted": 10}]


def timeless(stories: list[dict]) -> list[dict]:
    """Stories without what differs from a run to the next: when each hit fired, how long the test took."""
    def without_times(fields: dict) -> dict:
        return {key: fields[key] for key in fields if key not in ("atMs", "durationMs")}

    return json.loads(json.dumps(stories), object_hook=without_times)


def test_the_stories_of_a_parallel_run_are_those_of_a_plain_one(project):
    pytest.importorskip("xdist", reason="a project that does not run its tests in parallel has no such run")
    root = project(PROJECT)
    run_tests(root)
    plain = timeless(stories_of(root))

    done = run_tests(root, "-n", "2")

    assert done.returncode == 0, done.stdout + done.stderr
    assert timeless(stories_of(root)) == plain
    assert sorted(file.name for file in (root / "cache/stories").iterdir()) == ["checks__test_checkout.py.json"]


@pytest.mark.parametrize("test_file, said", [
    (f'{DECLARE} narrative\n\n\n@narrative("A flow")\ndef test_x():\n    assert True\n',
     "checks/test_bad.py:4 — a narrative is declared on a test class"),
    (f'{DECLARE} canonical\n\n\n@canonical\ndef test_x():\n    assert True\n',
     "checks/test_bad.py:4 — @canonical marks the reference case of a narrative"),
    (f'{DECLARE} planned_test\n\n\n@planned_test("a#b: c")\ndef test_x():\n    assert True\n',
     "checks/test_bad.py:4 — @planned_test stands on a test with an empty body"),
    (f'{CALLS} narrate\n\n\ndef test_x():\n    narrate("A step.", {{"amount": 3}})\n',
     "checks/test_bad.py:5 — the watch is passed as a function"),
    (f'{CALLS} planned\n\n\ndef test_x():\n    planned("NotATag", "A change.")\n',
     "checks/test_bad.py:5 — planned: 'NotATag' is not <feature>#<slug>"),
])
def test_a_declaration_or_a_call_that_does_not_have_the_shape_fails_the_run_with_its_line(project, test_file, said):
    around = {file: text for file, text in PROJECT.items() if not file.startswith("checks/")}
    root = project({**around, "checks/test_bad.py": test_file})

    done = run_tests(root)

    assert done.returncode != 0
    assert said in done.stdout + done.stderr
