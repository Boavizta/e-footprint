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


def run_tests(root, *options, environment: dict | None = None) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONPATH": str(ROOT), **(environment or {})}
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


REPRODUCTIONS = '''
    from shop.narrate import planned
    from comprehension_harness.python.declare import reproduces


    def due(total, card):
        planned.evidence("gift-cards#deduct-the-card", "The card is **not deducted**.",
                         lambda: {"due": total}, expect=lambda: {"due": total - card})
        planned("gift-cards#deduct-the-card", "The due amount **loses the card**.", expect={"due": 6})
        return total


    @reproduces("gift-cards#deduct-the-card: the amount due loses the card's balance")
    def test_deducts():
        assert due(10, 4) == 6


    @reproduces("gift-cards#deduct-the-card: a refund goes back to the card")
    def test_refunds():
        assert "refund" == "card"
'''


def test_a_reproduction_has_a_story_that_says_how_it_fails_whatever_it_crossed(project):
    around = {file: text for file, text in PROJECT.items() if not file.startswith("checks/")}
    root = project({**around, "checks/test_checkout.py": REPRODUCTIONS})

    done = run_tests(root)

    # A failure a run expects fails no run.
    assert done.returncode == 0 and "2 xfailed" in done.stdout, done.stdout + done.stderr
    deducts, refunds = stories_of(root)
    assert (deducts["state"], deducts["reproduction"]) == ("xfailed", True)
    assert deducts["failure"] == {"message": "assert 10 == 6\n +  where 10 = due(10, 4)", "file": TEST_FILE,
                                  "line": 14}
    hit, change = deducts["hits"]
    assert (hit["kind"], hit["watch"]) == ("planned", {"due": 10})
    assert hit["planned"] == {"feature": "gift-cards", "slug": "deduct-the-card", "change": "evidence"}
    # What a crossing should have seen is its own: computed as the watch is, or said once for the place.
    assert (hit["expect"], change["expect"], change["watch"]) == ({"due": 6}, {"due": 6}, None)
    # It crossed no call: a test that is no reproduction would have no story.
    assert (refunds["hits"], refunds["state"], refunds["failure"]["line"]) == ([], "xfailed", 19)


def test_a_call_a_template_makes_is_a_hit_at_its_tag_under_the_frames_that_rendered_it(project):
    """No frame of Python says where a tag is written: the tag gives its file and its line."""
    around = {file: text for file, text in PROJECT.items() if not file.startswith("checks/")}
    root = project({**around, "shop/pages/rows.html": '<ul>\n  <li>{% narrate "A row is **drawn**." kind=row.kind %}</li>\n</ul>\n',
                    "shop/pages.py": '''
        from pathlib import Path
        from shop.narrate import template_call


        def tag(kind):
            template_call("narrate", str(Path(__file__).parent / "pages/rows.html"), 2, "A row is **drawn**.",
                          lambda: {"kind": kind})


        def render(kind):
            tag(kind)
    ''', "checks/test_checkout.py": "from shop.pages import render\n\n\ndef test_rows():\n    render('card')\n"})

    done = run_tests(root)

    assert done.returncode == 0, done.stdout + done.stderr
    [story] = stories_of(root)
    [hit] = story["hits"]
    assert (hit["kind"], hit["sentence"], hit["watch"]) == ("step", "A row is **drawn**.", {"kind": "card"})
    assert hit["site"] == {"file": "shop/pages/rows.html", "line": 2, "column": 7, "fn": "(template)"}
    # The function that makes the call for the template is no frame of the story: the tag is the site.
    assert [(frame["file"], frame["fn"]) for frame in hit["stack"]] == [
        ("shop/pages.py", "render"), ("checks/test_checkout.py", "test_rows")]


def test_a_run_started_for_a_person_writes_no_story_and_leaves_those_on_file(project):
    """A debug run of one test would leave its file's stories with that test alone."""
    root = project(PROJECT)
    run_tests(root)
    whole = stories_of(root)

    done = run_tests(root, "-k", "test_audit", environment={"COMPREHENSION_STORIES": "off"})

    assert done.returncode == 0 and "1 passed" in done.stdout, done.stdout + done.stderr
    assert stories_of(root) == whole and len(whole) == 4


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
