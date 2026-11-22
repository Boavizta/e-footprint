"""The three calls a flow tells itself with: ``narrate``, ``event`` and ``planned``.

- ``narrate(sentence, watch)`` is a step, written at the line it describes.
- ``event(sentence, watch)`` is a cause, written at its handler: the steps that follow answer it.
- ``planned("<feature>#<slug>", sentence)`` is a place a feature's plan changes, written before the code;
  ``planned.remove(…)`` marks a function the piece removes. A shell is a new function whose whole body is the
  ``planned`` call followed by ``raise NotImplementedError("planned: <feature>#<slug>")``.

None of them does anything unless a collector is installed, which only a test run of this project does
(``comprehension_harness/python/collector.py``). Python computes a call's arguments before the call, so the
source index refuses any that is not inert: the sentence is a literal string and the watch a lambda the
collector calls, which nothing calls outside a test. The sentence is markdown-lite: ``**bold**`` for the rule
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
# kind, sentence, watch, the frame of the call, and for a planned call (feature, slug, change).
Collector = Callable[[str, str, Optional[Watch], FrameType, Optional[tuple[str, str, str]]], None]

PLANNED_TAG = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)#([a-z0-9]+(?:-[a-z0-9]+)*)$")

_collector: Optional[Collector] = None


def install_collector(collector: Optional[Collector]) -> None:
    """Test runs only. ``None`` uninstalls."""
    global _collector
    _collector = collector


def _refuse(frame: FrameType, what: str):
    raise TypeError(f"{frame.f_code.co_filename}:{frame.f_lineno} — {what}")


def _record(kind: str, sentence, watch, frame: FrameType, planned_as=None) -> None:
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


def _record_planned(tag, change: str, sentence, watch, frame: FrameType) -> None:
    parsed = PLANNED_TAG.match(tag) if isinstance(tag, str) else None
    if parsed is None:
        _refuse(frame, f"planned: {tag!r} is not <feature>#<slug>, two kebab-case names around one #")
    _record("planned", sentence, watch, frame, (parsed.group(1), parsed.group(2), change))


class _Planned:
    def __call__(self, tag: str, sentence: str, watch: Optional[Watch] = None) -> None:
        """What this place will do once the piece ``tag`` of a feature's plan is built."""
        if _collector is not None:
            _record_planned(tag, "changed", sentence, watch, sys._getframe(1))

    def remove(self, tag: str, sentence: str) -> None:
        """The function this call sits in goes with the piece ``tag``."""
        if _collector is not None:
            _record_planned(tag, "removed", sentence, None, sys._getframe(1))


planned = _Planned()
