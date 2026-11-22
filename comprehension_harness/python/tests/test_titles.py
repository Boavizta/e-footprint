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
         "line": 18, "column": 5, "planned": False},
        {"title": "gift-cards#refund-to-card: a refund goes back to the card first",
         "line": 27, "column": 9, "planned": True},
        {"title": "test_async", "line": 30, "column": 15, "planned": False},
    ]
    lines = TEST_FILE.split("\n")
    assert all(lines[test["line"] - 1][test["column"] - 1:].startswith("test_") for test in answer["tests"])


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
