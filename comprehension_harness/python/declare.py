"""What a test declares to the comprehension tools (``comprehension_harness/stack.md``).

- ``@narrative("<title>")`` on a test class declares a product narrative, ``@narrative.mechanism("<title>")``
  a mechanism one. The class docstring's first paragraph is its summary; its first test is the reference case
  unless one is marked ``@canonical``; the others are variants.
- ``@planned_test("<feature>#<slug>: <title> [<rule>]")`` on a test function with an empty body is a test to
  write. It is skipped by a run and listed by the plan.
- ``@titled("<feature>#<slug>: <title> [<rule>]")`` gives a written test the title a function name cannot hold.
  A test without it is titled by its function's name.
- ``@canonical(steps=("<flow>:<step>", …))`` declares an intended reference order. Its sentences live in
  ``narrate.planned`` calls beside the code. A written test keeps this order and promotes those calls to
  ``narrate(sentence, step="<flow>:<step>")``; its test-body first crossings must match the declared order.
- ``@reproduces("<feature>#<slug>: <title> [<rule>]")`` is a written test that fails today, for the bug its piece
  fixes: it asserts what should be. A run expects its failure, strictly: the fix cannot land without the
  declaration becoming ``@titled``, under the same title. Its story is the bug's evidence, so it observes
  everything it has to and asserts once, at its end: a story stops where its test fails. It is one test, not
  one a case: it reads its cases itself (``titles.py`` refuses a parametrized one).

All five are pytest markers. ``collector.py`` reads them when it writes a test's story; ``source_index.py``
and ``titles.py`` read them from the source.
"""
import dis

import pytest

# What the bytecode of a body that is a docstring, ``pass`` or ``...`` is made of, across Python versions.
_EMPTY_BODY = {"RESUME", "RETURN_CONST", "LOAD_CONST", "RETURN_VALUE", "NOP"}


def has_empty_body(function) -> bool:
    """A body that is a docstring, ``pass`` or ``...`` and nothing else: a test to write."""
    return {instruction.opname for instruction in dis.get_instructions(function.__code__)} <= _EMPTY_BODY


def _title(decorator: str, title) -> str:
    if not isinstance(title, str) or not title.strip():
        raise TypeError(f"@{decorator}(…) takes the test's title, a string, not {title!r}")
    return title


class _Narrative:
    def __call__(self, title: str, *, scope: str | None = None):
        if scope not in (None, "doc"):
            raise ValueError('a narrative scope is "doc" or None')
        return pytest.mark.narrative(_title("narrative", title), kind="product", **({"scope": scope} if scope else {}))

    def mechanism(self, title: str, *, scope: str | None = None):
        if scope not in (None, "doc"):
            raise ValueError('a narrative scope is "doc" or None')
        return pytest.mark.narrative(_title("narrative.mechanism", title), kind="mechanism", **({"scope": scope} if scope else {}))


narrative = _Narrative()

canonical = pytest.mark.canonical


def titled(title: str):
    return pytest.mark.titled(_title("titled", title))


def reproduces(title: str):
    _title("reproduces", title)

    def declare(function):
        expected = pytest.mark.xfail(strict=True, reason=f"reproduces: {title}")
        return expected(pytest.mark.reproduces(title)(function))

    return declare


def planned_test(title: str):
    _title("planned_test", title)

    def declare(function):
        code = function.__code__
        if not has_empty_body(function):
            raise TypeError(
                f"{code.co_filename}:{code.co_firstlineno} — @planned_test stands on a test with an empty body; "
                f"a written test carries its title with @titled(…)")
        return pytest.mark.skip(reason=f"planned: {title}")(pytest.mark.planned_test(title)(function))

    return declare
