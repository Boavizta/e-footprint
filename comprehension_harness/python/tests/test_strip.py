"""The strip of the Python stack (`strip.py`): what the archive of a feature takes off one file.

What is worth fencing: that a `built` statement goes with its lines and its import and nothing else does, that a
title loses its tag and its rule and stays written as it was, that a planned screen goes from the call it stands
in, that a template's tag goes with its library, that another feature's marks stay, and that a call which cannot
go alone is refused.
"""
import json
import textwrap

import pytest

from comprehension_harness.python.strip import strip
from comprehension_harness.python.tests.conftest import run_stack
from comprehension_harness.python.titles import Refusal


def stripped(text: str, file: str = "app/a.py") -> dict:
    return strip(file, textwrap.dedent(text).lstrip("\n"), "demo")


def lines(*some: str) -> str:
    return "\n".join(some)


def test_a_built_call_goes_with_its_line_and_takes_the_import_its_file_no_longer_uses():
    done = stripped('''
        from app.narrate import built
        from app.other import other


        def cut(rows):
            """Cuts."""
            kept = other(rows)

            built("demo#cut:the-cut")

            return kept
    ''')

    assert done["text"] == lines(
        "from app.other import other", "", "", "def cut(rows):", '    """Cuts."""', "    kept = other(rows)", "",
        "    return kept", "")
    assert done["taken"] == [{"line": 9, "kind": "built", "was": 'built("demo#cut:the-cut")'}]


@pytest.mark.parametrize("imported, left", [
    ("from app.narrate import built, narrate, event", "from app.narrate import narrate, event"),
    ("from app.narrate import narrate, built, event", "from app.narrate import narrate, event"),
    ("from app.narrate import narrate, event, built", "from app.narrate import narrate, event"),
    ("from app.narrate import (\n    narrate,\n    built,\n    event,\n)", "from app.narrate import (\n    narrate,\n    event,\n)"),
])
def test_the_other_names_of_its_import_stay_wherever_built_stood_among_them(imported, left):
    body = '\n\n\ndef f():\n    built("demo#cut:the-cut")\n    narrate("a")\n    event("b")\n'

    done = strip("app/a.py", imported + body, "demo")

    assert done["text"] == left + '\n\n\ndef f():\n    narrate("a")\n    event("b")\n'


def test_another_features_call_stays_and_keeps_the_import():
    done = stripped('''
        from app.narrate import built


        def f():
            built("demo#cut:the-cut")
            built("other-demo#cut:the-cut")
            built("demolition#cut:the-cut")
            # built("demo#cut:in-a-comment")
            return "demo#cut:in-a-string"
    ''')

    assert done["text"] == lines(
        "from app.narrate import built", "", "", "def f():", '    built("other-demo#cut:the-cut")',
        '    built("demolition#cut:the-cut")', '    # built("demo#cut:in-a-comment")',
        '    return "demo#cut:in-a-string"', "")
    assert [one["line"] for one in done["taken"]] == [5]


@pytest.mark.parametrize("body, said", [
    ('    return built("demo#cut:the-cut") or rows\n', "app/a.py:2 — built(\"demo#cut:the-cut\") is no statement of a block"),
    ('    if rows:\n        built("demo#cut:the-cut")\n    return rows\n',
     "app/a.py:3 — built(\"demo#cut:the-cut\") is all its block holds"),
    ('    if rows:\n        built("demo#cut:one")\n        built("demo#cut:two")\n    return rows\n',
     "app/a.py:4 — built(\"demo#cut:two\") is all its block holds"),
    ('    built("demo#cut:the-cut"); rows.sort()\n    return rows\n',
     "app/a.py:2 — built(\"demo#cut:the-cut\") shares its line with other code"),
])
def test_a_built_call_that_cannot_go_alone_is_refused_with_its_line(body, said):
    with pytest.raises(Refusal, match=said.replace("(", r"\(").replace(")", r"\)")):
        strip("app/a.py", "def cut(rows):\n" + body, "demo")


def test_a_title_loses_its_tag_and_its_rule_and_stays_written_as_it_was():
    done = stripped('''
        from declare import planned_test, reproduces, titled


        @titled("demo#cut: the band\\'s words are cut [first-cut]")
        def test_cut():
            assert True


        @reproduces("demo#cut: a count that is "
                    "one too many [the-count]")
        def test_count():
            assert False


        @titled('other-demo#cut: another feature keeps its tag [first-cut]')
        def test_other():
            assert "demo#cut: no title [first-cut]"


        @planned_test("demo#cut: no rule")
        def test_later():
            """To write."""
    ''', "checks/test_a.py")

    assert done["text"] == lines(
        "from declare import planned_test, reproduces, titled", "", "",
        '@titled("the band\\\'s words are cut")', "def test_cut():", "    assert True", "", "",
        '@reproduces("a count that is "', '            "one too many")', "def test_count():", "    assert False", "", "",
        "@titled('other-demo#cut: another feature keeps its tag [first-cut]')", "def test_other():",
        '    assert "demo#cut: no title [first-cut]"', "", "", '@planned_test("no rule")', "def test_later():",
        '    """To write."""', "")
    assert done["taken"] == [
        {"line": 4, "kind": "title", "was": "demo#cut: the band's words are cut [first-cut]"},
        {"line": 9, "kind": "title", "was": "demo#cut: a count that is one too many [the-count]"},
        {"line": 20, "kind": "title", "was": "demo#cut: no rule"}]


def test_a_planned_screen_goes_from_the_call_it_stands_in():
    done = stripped('''
        FEATURE = "demo"


        def test_reaches(page):
            screen(page, "review-card", why="The card is reached.", planned={"feature": FEATURE, "mockup": "m.html", "what": "A row."})
            screen(
                page,
                "summary",
                why="The summary is reached.",
                planned={"feature": "demo", "mockup": "m.html", "what": "A line."},
            )
            screen(page, "other", why="Another feature\\'s.", planned={"feature": "other", "mockup": "m", "what": "w"})
    ''', "checks/test_journey.py")

    assert done["text"] == lines(
        'FEATURE = "demo"', "", "", "def test_reaches(page):",
        '    screen(page, "review-card", why="The card is reached.")', "    screen(", "        page,",
        '        "summary",', '        why="The summary is reached.",', "    )",
        '    screen(page, "other", why="Another feature\\\'s.", planned={"feature": "other", "mockup": "m", "what": "w"})',
        "")
    assert [(one["line"], one["kind"]) for one in done["taken"]] == [(5, "screen"), (10, "screen")]


def test_a_templates_built_tag_goes_with_its_line_and_the_library_with_its_last_tag():
    template = lines("{% load static narrate %}", "<ul>", '  {% built "demo#row:row-class" %}',
                     '  <li>{% built "demo#row:row-id" %}{{ row }}</li>', "</ul>", "")

    done = strip("app/pages/rows.html", template, "demo")

    assert done["text"] == lines("{% load static %}", "<ul>", "  <li>{{ row }}</li>", "</ul>", "")
    assert done["taken"] == [{"line": 3, "kind": "built", "was": '{% built "demo#row:row-class" %}'},
                             {"line": 4, "kind": "built", "was": '{% built "demo#row:row-id" %}'}]
    # While another tag stands, the library stays; a library loaded alone goes with its line.
    kept = lines("{% load narrate %}", '{% built "demo#row:row-id" %}', '{% narrate "A row is **drawn**." %}', "")
    assert strip("app/t.html", kept, "demo")["text"] == lines("{% load narrate %}", '{% narrate "A row is **drawn**." %}', "")
    alone = lines("{% load narrate %}", '{% built "demo#row:row-id" %}', "<p></p>", "")
    assert strip("app/t.html", alone, "demo")["text"] == lines("<p></p>", "")


def test_a_file_the_stack_does_not_read_and_one_that_names_no_mark_come_back_as_they_are():
    for file, text in [("notes.md", 'built("demo#cut:the-cut")\n'), ("app/a.py", "DEMO = 'demo'\n")]:
        assert strip(file, text, "demo") == {"text": text, "taken": []}


def test_the_command_answers_one_file_and_says_a_refusal_with_its_file_and_line():
    asked = {"file": "app/a.py", "feature": "demo",
             "text": 'from narrate import built\n\n\ndef f(rows):\n    built("demo#cut:the-cut")\n    return rows\n'}

    done = run_stack("strip", stdin=json.dumps(asked))

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"text": "def f(rows):\n    return rows\n",
                                       "taken": [{"line": 5, "kind": "built", "was": 'built("demo#cut:the-cut")'}]}
    refused = run_stack("strip", stdin=json.dumps({**asked, "text": 'def f():\n    return built("demo#cut:the-cut")\n'}))
    assert refused.returncode == 1 and refused.stdout == ""
    assert refused.stderr.startswith('comprehension-strip: app/a.py:2 — built("demo#cut:the-cut") is no statement')
    assert run_stack("strip", stdin="[]").stderr.startswith("comprehension-strip: the input is not {file, text, feature}")
