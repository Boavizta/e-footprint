"""The source index of the Python stack: what `source_index.py` prints for a tree.

The example it conforms to is the index the tools' own tests read, written by hand for three files
(`comprehension_harness/tests/fixtures/shop/`). The rest is what that example does not show.
"""
import json

import pytest

from comprehension_harness.python.tests.conftest import ROOT, run_stack, source_index

SHOP = ROOT / "comprehension_harness/tests/fixtures/shop"

ENGINE = '''
    from narrate import event, narrate, planned
    from .rules import LIMIT


    class Engine:
        retries = LIMIT

        def start(self, load):
            def within(value):
                narrate("The load **stays under** `LIMIT`.", lambda: {"value": value})
                return value < self.retries

            event("The operator starts the engine.")
            return within(load) and self.stop()

        def stop(self):
            planned.remove("quiet-stop#drop-stop", "Stopping **goes** with the engine.")
            return True

        async def later(self):
            narrate("The engine is **tried again** later.", lambda: {"retries": self.retries})


    def run(load):
        return Engine().start(load)
'''
PROJECT = {
    "app/__init__.py": "from .engine import Engine, run\n",
    "app/rules.py": "LIMIT = 3\n",
    "app/engine.py": ENGINE,
    "app/console.py": '''
        import app.engine as engine
        from app import run


        def go(loads):
            return [run(load) for load in loads] + [engine.run(0)]
    ''',
    "checks/test_engine.py": '''
        from app import run
        from declare import narrative, titled


        @narrative.mechanism("The engine starts")
        class TestEngine:
            """It starts under its limit,
            and stops.

            A second paragraph is not the summary."""

            @titled("quiet-stop#drop-stop: the engine starts under its limit")
            def test_start(self):
                assert run(1)
    ''',
    "checks/test_unrelated.py": "def test_nothing():\n    assert True\n",
}


def indexed(root) -> dict:
    done = source_index(root)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_the_example_written_by_hand_is_what_the_command_prints_for_its_source():
    done = source_index(SHOP, source="shop/", tests="tests/", declare="narrate")
    assert done.returncode == 0, done.stderr
    printed, by_hand = json.loads(done.stdout), json.loads((SHOP / "source-index.json").read_text())

    assert printed["looksDeclared"] == by_hand["looksDeclared"]
    assert printed["narratives"] == by_hand["narratives"]
    assert sorted(printed["files"]) == sorted(by_hand["files"])
    for file, tables in by_hand["files"].items():
        assert printed["files"][file] == tables, file


def test_a_function_is_named_as_its_frames_are_and_a_site_says_its_kind_and_its_change(project):
    engine = indexed(project(PROJECT))["files"]["app/engine.py"]

    assert [(f["fn"], f["line"], f["column"], f["endLine"]) for f in engine["functions"]] == [
        ("Engine.start", 8, 9, 14), ("Engine.start.<locals>.within", 9, 13, 11), ("Engine.stop", 16, 9, 18),
        ("Engine.later", 20, 15, 21), ("run", 24, 5, 25)]
    assert [(s["kind"], s["line"], s["column"], s["fn"], s["sentence"]) for s in engine["sites"]] == [
        ("step", 10, 13, "Engine.start.<locals>.within", "The load **stays under** `LIMIT`."),
        ("event", 13, 9, "Engine.start", "The operator starts the engine."),
        ("planned", 17, 9, "Engine.stop", "Stopping **goes** with the engine."),
        ("step", 21, 9, "Engine.later", "The engine is **tried again** later.")]
    assert engine["sites"][2]["planned"] == {
        "feature": "quiet-stop", "slug": "drop-stop", "change": "removed", "signature": None}


def test_an_evidence_site_says_what_the_place_should_see_as_it_is_written(project):
    """A literal, or a lambda where the right value depends on the crossing: its value is a story's."""
    root = project({"app/due.py": f'''{CALLS}def due(total, card):
    planned.evidence("gift-cards#deduct-the-card", "The card is **not deducted**.",
                     lambda: {{"due": total}}, expect=lambda: {{"due": total - card}})
    planned("gift-cards#deduct-the-card", "The due amount **loses the card**.", expect={{"due": 6}})
    planned.evidence("gift-cards#deduct-the-card", "The total is **read as it is**.")
    planned("gift-cards#deduct-the-card", "The row is named **after its card**.", lambda: {{"row": total}},
            distinct="row")
    planned.evidence("gift-cards#deduct-the-card", "Two cards share **one row**.", lambda: {{"row": 1, "of": card}},
                     distinct=("row", "of"))
    return total
'''})

    sites = indexed(root)["files"]["app/due.py"]["sites"]

    piece = {"feature": "gift-cards", "slug": "deduct-the-card", "signature": None}
    # The keys each crossing should see a value of its own for are the source's to say: no run reads them.
    assert [site["planned"] for site in sites] == [
        {**piece, "change": "evidence", "expect": "{'due': total - card}"},
        {**piece, "change": "changed", "expect": "{'due': 6}"},
        {**piece, "change": "evidence"},
        {**piece, "change": "changed", "distinct": ["row"]},
        {**piece, "change": "evidence", "distinct": ["row", "of"]}]


def test_a_place_that_becomes_code_names_itself_and_a_built_call_stands_for_it_once_it_is(project):
    """The id is the site's own within its piece: the `built` call that replaces a `planned` one carries it."""
    root = project({"app/due.py": f'''{CALLS}from narrate import built


def due(total, card):
    planned("gift-cards#deduct-the-card:amount-due", "The due amount **loses the card**.")
    built("gift-cards#deduct-the-card:card-read")
    return total - card


def refund(amount):
    planned("gift-cards#refund-to-card:refund", "A refund goes back to the card first.")
    raise NotImplementedError("planned: gift-cards#refund-to-card")
'''})

    planned, built, shell = indexed(root)["files"]["app/due.py"]["sites"]

    piece = {"feature": "gift-cards", "slug": "deduct-the-card", "signature": None}
    assert planned["planned"] == {**piece, "place": "amount-due", "change": "changed"}
    # A built call is a site of the plan with no clause of its own: the approval holds the place's.
    assert (built["kind"], built["line"], built["column"], built["fn"], built["sentence"]) == ("planned", 7, 5, "due", "")
    assert built["planned"] == {**piece, "place": "card-read", "change": "built"}
    # A shell raises its piece, whatever place its call names.
    assert shell["planned"] == {"feature": "gift-cards", "slug": "refund-to-card", "place": "refund",
                                "change": "added", "signature": "def refund(amount):"}


TEMPLATE = '''<ul>
  {% for row in rows %}
    {% narrate "A row is **drawn**." kind=row.kind %}
    {% if row.card %}{% planned "gift-cards#card-row:balance" "The row shows the card\'s balance." %}{% endif %}
    {% evidence "gift-cards#card-row" "A card is drawn **as a plain row**." drawn_as="row" expect drawn_as=row.kind|lower %}
    {% planned "gift-cards#card-row" "The row\'s id is the card\'s." id=row.kind of=row.card distinct id %}
    {% built "gift-cards#card-row:row-class" %}
  {% endfor %}
</ul>
'''


def test_a_template_makes_the_calls_as_tags_and_each_is_a_site_of_it_in_no_function(project):
    root = project({"app/x.py": "LIMIT = 3\n", "app/pages/rows.html": TEMPLATE, "app/pages/plain.html": "<p>{{ x }}</p>\n"})

    files = indexed(root)["files"]

    # A template is listed for its sites alone.
    assert "app/pages/plain.html" not in files
    rows = files["app/pages/rows.html"]
    assert {table: rows[table] for table in rows if table != "sites"} == {
        "functions": [], "declarations": [], "imports": [], "locals": [], "uses": []}
    piece = {"feature": "gift-cards", "slug": "card-row", "signature": None}
    assert rows["sites"] == [
        {"kind": "step", "line": 3, "column": 5, "fn": "(template)", "hasWatch": True, "sentence": "A row is **drawn**."},
        {"kind": "planned", "line": 4, "column": 22, "fn": "(template)", "sentence": "The row shows the card's balance.",
         "planned": {**piece, "place": "balance", "change": "changed"}},
        {"kind": "planned", "line": 5, "column": 5, "fn": "(template)", "hasWatch": True, "sentence": "A card is drawn **as a plain row**.",
         "planned": {**piece, "change": "evidence", "expect": "drawn_as=row.kind|lower"}},
        {"kind": "planned", "line": 6, "column": 5, "fn": "(template)", "hasWatch": True, "sentence": "The row's id is the card's.",
         "planned": {**piece, "change": "changed", "distinct": ["id"]}},
        {"kind": "planned", "line": 7, "column": 5, "fn": "(template)", "sentence": "",
         "planned": {**piece, "place": "row-class", "change": "built"}}]


@pytest.mark.parametrize("tag, said", [
    ("{% narrate sentence %}", "app/t.html:1 — {% narrate %} opens with its sentence, in double quotes"),
    ('{% planned "a#b" %}', "app/t.html:1 — {% planned %} opens with its tag and its sentence, in double quotes"),
    ('{% planned "NotATag" "A change." %}', 'app/t.html:1 — "NotATag" is not <feature>#<slug>'),
    ('{% narrate "A step." %}{% event "A cause." %}', "app/t.html:1 — one narrate, event, planned, evidence or built "
                                                      "tag a line"),
    ('{% planned "a#b:Place" "A change." %}', 'app/t.html:1 — "a#b:Place" is not <feature>#<slug> or '
                                              '<feature>#<slug>:<place>'),
    ('{% evidence "a#b:c" "A bug." %}', 'app/t.html:1 — "a#b:c" names a place, and only a place that becomes code '
                                        'has one'),
    ('{% built "a#b" %}', 'app/t.html:1 — a built call takes one literal, "<feature>#<slug>:<place>", and "a#b" names '
                          'no place'),
    ('{% built "a#b:c" "A change." %}', 'app/t.html:1 — {% built %} takes one literal, "<feature>#<slug>:<place>"'),
    ("{% built place %}", 'app/t.html:1 — {% built %} takes one literal, "<feature>#<slug>:<place>"'),
    ('{% evidence "a#b" "A bug." kind %}', "app/t.html:1 — after the sentence a tag gives key=value pairs"),
    ('{% evidence "a#b" "A bug." kind=row.kind expect %}', "app/t.html:1 — after the sentence a tag gives key=value pairs"),
    ('{% narrate "A step." expect kind="card" %}', "app/t.html:1 — expect and distinct are said of a planned or an "
                                                   "evidence tag"),
    ('{% planned "a#b" "A change." id=row.id distinct %}', "app/t.html:1 — after the word distinct a tag names keys"),
    ('{% planned "a#b" "A change." id=row.id distinct kind %}', "app/t.html:1 — after the word distinct a tag names "
                                                               "keys of its watch"),
])
def test_a_tag_that_does_not_have_the_shape_is_refused_with_its_file_and_line(project, tag, said):
    done = source_index(project({"app/x.py": "LIMIT = 3\n", "app/t.html": f"{tag}\n"}))

    assert done.returncode == 1 and done.stdout == ""
    assert f"comprehension-source: {said}" in done.stderr


def test_a_reference_is_placed_where_python_binds_the_name(project):
    files = indexed(project(PROJECT))["files"]
    at = lambda file, line, column: {"file": file, "line": line, "column": column}  # noqa: E731

    engine = {(use["name"], use["line"]): use["at"] for use in files["app/engine.py"]["uses"]}
    assert engine == {
        ("LIMIT", 6): at("app/rules.py", 1, 1),             # an import, read in a class body
        ("retries", 11): at("app/engine.py", 6, 5),         # self.<field> of the class around
        ("within", 14): at("app/engine.py", 9, 13),         # a function of the enclosing function
        ("stop", 14): at("app/engine.py", 16, 9),           # self.<method>
        ("Engine", 25): at("app/engine.py", 5, 7),
    }  # and no `retries` at line 21: what stands inside a narrate call, its watch included, is no use
    # A name a package re-exports is followed to the file that declares it, and so is `module.name`.
    assert files["app/console.py"]["imports"] == [{"name": "run", "at": at("app/engine.py", 24, 5)}]
    assert [(use["name"], use["line"], use["column"], use["at"]) for use in files["app/console.py"]["uses"]] == [
        ("run", 6, 13, at("app/engine.py", 24, 5)), ("run", 6, 52, at("app/engine.py", 24, 5))]
    package = files["app/__init__.py"]
    assert package["declarations"] == [] and [imported["name"] for imported in package["imports"]] == ["Engine", "run"]


def test_a_narrative_is_a_test_class_with_its_summary_and_its_first_test(project):
    index = indexed(project(PROJECT))

    assert index["narratives"] == [{
        "file": "checks/test_engine.py", "title": "The engine starts", "line": 5, "kind": "mechanism",
        "summary": "It starts under its limit, and stops.",
        "firstTest": "quiet-stop#drop-stop: the engine starts under its limit"}]
    # A test file is in the index when it declares a narrative or holds a site, and only then.
    assert sorted(index["files"]) == [
        "app/__init__.py", "app/console.py", "app/engine.py", "app/rules.py", "checks/test_engine.py"]


def test_a_shell_is_a_function_whose_body_is_the_call_and_the_raise_of_its_tag(project):
    shell = '''
        from narrate import planned


        def refund(
            amount: float,
        ) -> dict:
            """What it will do."""
            planned("gift-cards#refund-to-card", "A refund goes back to the card first.")
            raise NotImplementedError("planned: gift-cards#refund-to-card")
    '''
    [site] = indexed(project({"app/shell.py": shell}))["files"]["app/shell.py"]["sites"]

    assert site["planned"] == {"feature": "gift-cards", "slug": "refund-to-card", "change": "added",
                               "signature": "def refund( amount: float, ) -> dict:"}


CALLS = "from narrate import event, narrate, planned\n"
BUILT = "from narrate import built\n"
DECLARE = "from declare import narrative\n"


@pytest.mark.parametrize("source, said", [
    (CALLS + 'def f():\n    narrate("a"); narrate("b")\n', "app/x.py:3 — one narrate, event, planned or built call a "
                                                            "line"),
    (CALLS + 'def f():\n    planned.remove("a#b:c", "d")\n', 'app/x.py:3 — "a#b:c" names a place, and only a place '
                                                             'that becomes code has one'),
    (CALLS + 'def f():\n    planned.evidence("a#b:c", "d")\n', 'app/x.py:3 — "a#b:c" names a place'),
    (CALLS + 'def f():\n    planned("a#b:c:d", "e")\n', 'app/x.py:3 — "a#b:c:d" is not <feature>#<slug> or '
                                                        '<feature>#<slug>:<place>'),
    (BUILT + 'def f():\n    built("a#b")\n', 'app/x.py:3 — a built call takes one literal, "<feature>#<slug>:<place>", '
                                             'and "a#b" names no place'),
    (BUILT + 'TAG = "a#b:c"\ndef f():\n    built(TAG)\n', 'app/x.py:4 — built(…) takes one literal'),
    (BUILT + 'def f():\n    built("a#b:c", "A change.")\n', 'app/x.py:3 — built(…) takes one literal'),
    (BUILT + 'def f(n):\n    built("a#b:c", watch=lambda: n)\n', 'app/x.py:3 — built(…) takes one literal'),
    (CALLS + 'def f():\n    planned("a#b:c", "d")\n    raise NotImplementedError("planned: a#other")\n',
     'app/x.py:4 — the shell must raise NotImplementedError("planned: a#b")'),
    (CALLS + 'TAG = "a#b"\ndef f():\n    planned(TAG, "c")\n', "app/x.py:4 — planned(…) needs a literal"),
    (CALLS + 'def f():\n    planned("NotATag", "c")\n', 'app/x.py:3 — "NotATag" is not <feature>#<slug>'),
    ("import narrate\ndef f():\n    narrate.narrate('a')\n", "app/x.py:3 — the calls are imported by name"),
    ("from comprehension_harness.python.narrate import narrate\ndef f():\n    narrate('a')\n",
     "app/x.py:3 — the calls are imported from this project's copy, narrate, not from the reference"),
    (CALLS + 'def f():\n    planned("a#b", "c")\n    raise ValueError("later")\n',
     'app/x.py:4 — the shell must raise NotImplementedError("planned: a#b")'),
    (DECLARE + "@narrative('n')\ndef test_x():\n    pass\n", "app/x.py:3 — a narrative is declared on a test class"),
    (DECLARE + "TITLE = 'n'\n@narrative(TITLE)\nclass TestX:\n    pass\n",
     "app/x.py:3 — a narrative is declared under one literal title"),
    ("def f(:\n    pass\n", "app/x.py:1 — the Python parser refuses the file"),
])
def test_a_source_that_does_not_have_the_shape_is_refused_with_its_file_and_line(project, source, said):
    done = source_index(project({"app/x.py": source}))

    assert done.returncode == 1 and done.stdout == ""
    assert f"comprehension-source: {said}" in done.stderr


@pytest.mark.parametrize("call, said", [
    ('narrate(f"The {n} lines are added.")', "app/x.py:3 — the sentence of a narrate or event call is a literal"),
    ('event("The basket " + str(n))', "app/x.py:3 — the sentence of a narrate or event call is a literal string"),
    ('narrate("The lines are added.", {"count": n})', "app/x.py:3 — the watch is a lambda"),
    ('event("The customer pays.", watch=dict(count=n))', "app/x.py:3 — the watch is a lambda"),
    ('planned("a#b", "The lines are added.", sorted(n))', "app/x.py:3 — the watch is a lambda"),
    ('narrate("The lines are added.", *n)', "app/x.py:3 — the watch is a lambda"),
    ('planned.evidence("a#b", "A bug shows.", expect={"count": n})', "app/x.py:3 — expect is a literal dict"),
    ('planned.evidence("a#b", "A bug shows.", expect=["count"])', "app/x.py:3 — expect is a literal dict"),
    ('planned("a#b", "A change.", expect=dict(count=n))', "app/x.py:3 — expect is a literal dict"),
    ('planned("a#b", "A change.", distinct=n)', "app/x.py:3 — distinct names keys of the watch, as a literal string"),
    ('planned("a#b", "A change.", distinct=())', "app/x.py:3 — distinct names keys of the watch"),
    ('narrate("A step.", distinct="count")', "app/x.py:3 — the watch is a lambda"),
])
def test_an_argument_python_would_compute_in_production_is_refused(project, call, said):
    """A call does nothing in production, and Python computes its arguments before it all the same."""
    done = source_index(project({"app/x.py": f"{CALLS}def f(n):\n    {call}\n"}))

    assert done.returncode == 1 and done.stdout == ""
    assert f"comprehension-source: {said}" in done.stderr


def test_the_source_of_this_repository_is_one_the_index_reads():
    """Every pytest run holds the product's own calls to the index's refusals, the inert arguments among them."""
    done = run_stack("source_index")

    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("watch", ["", ", lambda: None", ", watch=lambda: {}", ", lambda: []"])
def test_watch_declaration_is_independent_of_its_value(project, watch):
    root = project({"app/x.py": CALLS + f'def f():\n    narrate("A step."{watch})\n'})
    [site] = indexed(root)["files"]["app/x.py"]["sites"]
    assert site.get("hasWatch", False) == bool(watch)
