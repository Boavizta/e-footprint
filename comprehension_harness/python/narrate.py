"""The three calls a flow tells itself with: ``narrate``, ``event`` and ``planned``.

- ``narrate(sentence, watch)`` is a step, written at the line it describes.
- ``event(sentence, watch)`` is a cause, written at its handler: the steps that follow answer it.
- ``planned("<feature>#<slug>", sentence)`` is a place a feature's plan changes, written before the code;
  ``planned.remove(…)`` marks a function the piece removes. A shell is a new function whose whole body is the
  ``planned`` call followed by ``raise NotImplementedError("planned: <feature>#<slug>")``.
- ``planned.evidence("<feature>#<slug>", sentence, watch, expect={…})`` is a place a bug shows, written while it
  is diagnosed: what is seen there today, the watch giving the values. It marks no change and goes with the fix.
  ``expect`` says, a key of the watch each, the value the place should see, which the plan's page sets against
  what the reproduction saw: a literal dict, or a lambda where the right value depends on the crossing (a line
  crossed for many rows, each with its own). ``distinct`` names the keys of the watch that each crossing
  should see a value of its own for: the bug shows where two crossings of a test saw the same. It is read from
  the source alone, and a run does nothing with it. ``planned`` takes both too.

A template makes the same calls through ``template_call``, which the tag library of the project's web
framework calls with the template's file and the line of the tag: no frame of Python says where a tag is written.

None of them does anything unless a collector is installed, which only a test run of this project does
(``comprehension_harness/python/collector.py``). Python computes a call's arguments before the call, so the
source index refuses any that is not inert: the sentence is a literal string, the watch a lambda the
collector calls, which nothing calls outside a test, ``expect`` a literal dict or another such lambda, and
``distinct`` a literal string or a literal tuple of them. The sentence is markdown-lite: ``**bold**`` for the rule
the step enacts, backticks for a symbol of the code.

Every project keeps this file inside its own package and imports the calls from there, so that its code
imports nothing of the harness, in production or from a published package, and so that a test run of one
project never receives the calls of another it depends on: each copy has its own collector. The reference is
``comprehension_harness/python/narrate.py``, and ``stack.calls`` of ``comprehension.config.json`` names the
copy. Edit the reference, then copy it: a test of the stack fails while the two differ.

Standard library only. The contract these calls are written to is ``comprehension_harness/stack.md``.
"""
import re
import sys
from types import FrameType
from typing import Any, Callable, Optional

Watch = Callable[[], Any]


class Place:
    """Where a call is written when no frame says it: a template's file and the line of its tag, and the frame
    the template was rendered from."""
    __slots__ = ("file", "line", "above")

    def __init__(self, file: str, line: int, above: Optional[FrameType]):
        self.file, self.line, self.above = file, line, above


# What a place should see: a dict, or a function the collector calls as it calls a watch.
Expect = Any
# The keys of the watch each crossing should see a value of its own for: one, or a tuple of them. The source
# index reads it where it is written; no run does.
Distinct = Any
# kind, sentence, watch, the frame of the call or the place a template says, and for a planned call (feature,
# slug, change, expect).
Collector = Callable[[str, str, Optional[Watch], "FrameType | Place", Optional[tuple[str, str, str, Expect]]], None]

PLANNED_TAG = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)#([a-z0-9]+(?:-[a-z0-9]+)*)$")

_collector: Optional[Collector] = None


def install_collector(collector: Optional[Collector]) -> None:
    """Test runs only. ``None`` uninstalls."""
    global _collector
    _collector = collector


def _refuse(frame, what: str):
    where = (frame.file, frame.line) if isinstance(frame, Place) else (frame.f_code.co_filename, frame.f_lineno)
    raise TypeError(f"{where[0]}:{where[1]} — {what}")


def _record(kind: str, sentence, watch, frame, planned_as=None) -> None:
    if not isinstance(sentence, str):
        _refuse(frame, f"the sentence of a {kind} call is a string, not {type(sentence).__name__}")
    if watch is not None and not callable(watch):
        _refuse(frame, f"the watch is passed as a function (lambda: {{…}}), not as {type(watch).__name__}")
    _collector(kind, sentence, watch, frame, planned_as)


def narrate(sentence: str, watch: Optional[Watch] = None) -> None:
    """A narrative step: what happens here, at the line it happens."""
    if _collector is not None:
        _record("step", sentence, watch, sys._getframe(1))


def event(sentence: str, watch: Optional[Watch] = None) -> None:
    """A cause: the action or the outside event the steps that follow answer."""
    if _collector is not None:
        _record("event", sentence, watch, sys._getframe(1))


def _record_planned(tag, change: str, sentence, watch, frame, expect=None) -> None:
    parsed = PLANNED_TAG.match(tag) if isinstance(tag, str) else None
    if parsed is None:
        _refuse(frame, f"planned: {tag!r} is not <feature>#<slug>, two kebab-case names around one #")
    if expect is not None and not isinstance(expect, dict) and not callable(expect):
        _refuse(frame, f"expect is a dict or a function (lambda: {{…}}), not {type(expect).__name__}")
    _record("planned", sentence, watch, frame, (parsed.group(1), parsed.group(2), change, expect))


class _Planned:
    def __call__(self, tag: str, sentence: str, watch: Optional[Watch] = None, expect: Expect = None,
                 distinct: Distinct = None) -> None:
        """What this place will do once the piece ``tag`` of a feature's plan is built."""
        if _collector is not None:
            _record_planned(tag, "changed", sentence, watch, sys._getframe(1), expect)

    def remove(self, tag: str, sentence: str) -> None:
        """The function this call sits in goes with the piece ``tag``."""
        if _collector is not None:
            _record_planned(tag, "removed", sentence, None, sys._getframe(1))

    def evidence(self, tag: str, sentence: str, watch: Optional[Watch] = None, expect: Expect = None,
                 distinct: Distinct = None) -> None:
        """What the bug the piece ``tag`` fixes shows at this place today. The call goes with the fix."""
        if _collector is not None:
            _record_planned(tag, "evidence", sentence, watch, sys._getframe(1), expect)


planned = _Planned()

_TEMPLATE_CALLS = {"narrate": "step", "event": "event", "planned": "changed", "evidence": "evidence"}


def template_call(call: str, file: str, line: int, sentence: str, watch: Optional[Watch] = None,
                  tag: Optional[str] = None, expect: Expect = None) -> None:
    """A call written as a tag of a template: ``call`` is ``narrate``, ``event``, ``planned`` or ``evidence``, the
    last two with their ``tag``. Called by the tag as it renders, with where the tag is written."""
    if _collector is None:
        return
    place = Place(file, line, sys._getframe(1).f_back)
    said = _TEMPLATE_CALLS.get(call)
    if said is None:
        _refuse(place, f"{call!r} is no call a template makes: narrate, event, planned or evidence")
    if said in ("step", "event"):
        _record(said, sentence, watch, place)
    else:
        _record_planned(tag, said, sentence, watch, place, expect)
