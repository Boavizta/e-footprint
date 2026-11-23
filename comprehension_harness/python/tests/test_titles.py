"""The title reader of the Python stack: what `titles.py` prints for a file's text."""
import json
import textwrap

import pytest

from comprehension_harness.python.tests.conftest import run_stack

TEST_FILE = textwrap.dedent('''
    import pytest
    from comprehension_harness.python.declare import narrative, planned_test, titled

    LIMIT = 3


    def helper():
        return LIMIT


    def test_plain():
        assert helper()


    # a comment right above a decorator stands on the test the decorator opens
    @pytest.mark.django_db
    @titled("gift-cards#deduct-the-card: the amount due loses the card's balance [card-first]")
    def test_deduction(client):
        assert client


    @narrative("The customer pays a basket")
    class TestPay:
        """The total is what is charged."""

        @planned_test("gift-cards#refund-to-card: a refund goes back to the card first")
        def test_refund(self):
            """To write."""

        async def test_async(self):
            assert True

        def not_a_test(self):
            pass


    class Helper:
        def test_in_no_test_class(self):
            pass
''').lstrip("\n")


def read(*files: tuple[str, str]) -> list[dict]:
    done = run_stack("titles", stdin=json.dumps([{"file": file, "text": text} for file, text in files]))
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_a_test_is_titled_by_its_name_or_its_decorator_and_planned_when_it_has_no_body():
    [answer] = read(("tests/test_pay.py", TEST_FILE))

    assert answer["file"] == "tests/test_pay.py" and answer["journeyCases"] == []
    assert answer["tests"] == [
        {"title": "test_plain", "line": 11, "column": 5, "planned": False},
        {"title": "gift-cards#deduct-the-card: the amount due loses the card's balance [card-first]",
         "line": 18, "column": 5, "planned": False, "body": answer["tests"][1]["body"]},
        {"title": "gift-cards#refund-to-card: a refund goes back to the card first",
         "line": 27, "column": 9, "planned": True},
        {"title": "test_async", "line": 30, "column": 15, "planned": False},
    ]
    lines = TEST_FILE.split("\n")
    assert all(lines[test["line"] - 1][test["column"] - 1:].startswith("test_") for test in answer["tests"])


def test_a_reproduction_is_a_written_test_declared_to_fail_today():
    text = textwrap.dedent('''
        from comprehension_harness.python.declare import reproduces


        @reproduces("gift-cards#deduct-the-card: a card of zero is charged nothing")
        def test_zero_card():
            assert charge(0) == 0
    ''').lstrip("\n")

    [answer] = read(("tests/test_pay.py", text))

    assert answer["tests"] == [{"title": "gift-cards#deduct-the-card: a card of zero is charged nothing",
                                "line": 5, "column": 5, "planned": False, "reproduction": True,
                                "body": answer["tests"][0]["body"]}]


def test_a_declared_test_carries_its_body_which_its_declaration_and_its_place_do_not_move():
    def body(text: str) -> str:
        [answer] = read(("tests/test_pay.py", textwrap.dedent(text).lstrip("\n")))
        return answer["tests"][0]["body"]

    reproduction = body('''
        @reproduces("gift-cards#deduct-the-card: a card of zero is charged nothing")
        def test_zero_card():
            assert charge(0) == 0
    ''')

    # Declared a written test once it passes, moved down the file and into a class: the same test.
    assert reproduction == body('''
        import pytest


        class TestCards:
            @pytest.mark.django_db
            @titled("gift-cards#deduct-the-card: a card of zero is charged nothing")
            def test_zero_card():
                assert charge(0) == 0
    ''')
    # Asserting something else is another test.
    assert reproduction != body('''
        @titled("gift-cards#deduct-the-card: a card of zero is charged nothing")
        def test_zero_card():
            assert charge(0) >= 0
    ''')


def test_a_stand_is_the_line_that_opens_a_test_a_class_or_a_declaration():
    [answer] = read(("tests/test_pay.py", TEST_FILE))

    stands = {stand["line"]: (stand["label"], stand["test"]) for stand in answer["stands"]}
    assert stands[4] == ("LIMIT", None)
    assert stands[7] == ("helper", None)
    assert stands[11] == ('test "test_plain"', "test_plain")
    # The first decorator opens the test: the line under a comment written above it.
    assert stands[16][1].startswith("gift-cards#deduct-the-card: ") and 18 not in stands
    assert stands[22] == ("TestPay", None)
    assert stands[26][0].startswith('test "gift-cards#refund-to-card: ')
    assert stands[33] == ("not_a_test", None)
    assert stands[38] == ("test_in_no_test_class", None)


def test_a_batch_is_answered_in_order_and_a_file_that_is_not_python_holds_nothing():
    page, script = ("specs/workflow.md", "# A page\n"), ("theme/x.js", "test('a', () => {})")
    answers = read(page, ("tests/test_pay.py", TEST_FILE), script)

    assert [answer["file"] for answer in answers] == ["specs/workflow.md", "tests/test_pay.py", "theme/x.js"]
    assert [len(answer["tests"]) for answer in answers] == [0, 4, 0]
    assert answers[0] == {"file": "specs/workflow.md", "tests": [], "stands": [], "journeyCases": []}


@pytest.mark.parametrize("source, said", [
    ('@planned_test("a#b: c")\ndef test_x():\n    assert True\n',
     "t.py:1 — @planned_test stands on a test with an empty body"),
    ('TITLE = "a#b: c"\n\n@titled(TITLE)\ndef test_x():\n    pass\n',
     "t.py:3 — @titled(…) takes the test's title as one literal string"),
    ('@titled("a")\n@planned_test("b")\ndef test_x():\n    pass\n', "t.py:1 — a test has one title"),
    ('@reproduces("a#b: c")\ndef test_x():\n    pass\n', "t.py:1 — @reproduces stands on a written test"),
    ('@titled("a")\ndef check_x():\n    pass\n', "t.py:1 — @titled(…) stands on a test function"),
    ("def test_x(:\n    pass\n", "t.py:1 — the Python parser refuses the file"),
])
def test_a_file_that_does_not_have_the_shape_is_refused_with_its_line(source, said):
    done = run_stack("titles", stdin=json.dumps([{"file": "t.py", "text": source}]))

    assert done.returncode == 1 and done.stdout == ""
    assert f"comprehension-titles: {said}" in done.stderr


@pytest.mark.parametrize("stdin, said", [
    ("not json", "the input is not JSON"), ('[{"file": "t.py"}]', "the input is not [{file, text}]")])
def test_an_input_of_another_shape_is_refused(stdin, said):
    done = run_stack("titles", stdin=stdin)

    assert done.returncode == 1 and said in done.stderr


JOURNEY_FILE = textwrap.dedent('''
    from comprehension_harness.python.declare import titled
    from comprehension_harness.python.journey import journey, planned_case, screen

    FEATURE = "gift-cards"


    @journey("Fill a basket", who="A customer", wants="Their articles", now="2026-01-15T10:00:00Z")
    class TestFillABasket:
        @titled("adds an article")
        def test_adds_an_article(self, page):
            screen(page, "basket", why="The basket opens empty.")

        @planned_case(FEATURE, "basket", "a gift card shows its balance")
        def test_gift_card(self):
            """To write."""

        @planned_case("loyalty", "checkout", "the points earned are shown")
        def test_points(self):
            ...
''').lstrip("\n")


def test_a_journey_case_is_a_planned_case_of_a_journey_class_and_no_test_until_written():
    [answer] = read(("tests/e2e/journeys/test_basket.py", JOURNEY_FILE))

    case = {"journey": "Fill a basket", "file": "tests/e2e/journeys/test_basket.py"}
    assert answer["journeyCases"] == [
        {**case, "feature": "gift-cards", "screen": "basket", "title": "a gift card shows its balance",
         "line": 13, "column": 6},
        {**case, "feature": "loyalty", "screen": "checkout", "title": "the points earned are shown",
         "line": 17, "column": 6},
    ]
    assert [test["title"] for test in answer["tests"]] == ["adds an article"]
    stands = {stand["line"]: (stand["label"], stand["test"]) for stand in answer["stands"]}
    assert stands[13] == ('case "a gift card shows its balance"', None)


@pytest.mark.parametrize("source, said", [
    ('@planned_case("a", "b", "c")\ndef test_x():\n    pass\n',
     't.py:1 — @planned_case stands on a test of a class under @journey("<name>", …)'),
    ('@journey("J", who="a", wants="b", now="c")\nclass TestJ:\n    @planned_case("a", "b")\n    def test_x(self):\n'
     '        pass\n', "t.py:3 — @planned_case(feature, screen, title) takes three strings"),
    ('@journey("J", who="a", wants="b", now="c")\nclass TestJ:\n    @planned_case("a", "b", "c")\n'
     '    def test_x(self):\n        assert True\n', "t.py:3 — @planned_case stands on a test with an empty body"),
    ('@journey("J", who="a", wants="b", now="c")\nclass TestJ:\n    @planned_case("a", "b", "c")\n    @titled("c")\n'
     '    def test_x(self):\n        pass\n', "t.py:3 — @planned_case stands on a test with an empty body"),
    ('@journey("J", who="a", wants="b", now="c")\nclass TestJ:\n    @planned_case("a", "b", "c")\n'
     '    def check_x(self):\n        pass\n', "t.py:3 — @planned_case stands on a test function"),
])
def test_a_planned_case_that_does_not_have_the_shape_is_refused_with_its_line(source, said):
    done = run_stack("titles", stdin=json.dumps([{"file": "t.py", "text": source}]))

    assert done.returncode == 1 and done.stdout == ""
    assert f"comprehension-titles: {said}" in done.stderr
