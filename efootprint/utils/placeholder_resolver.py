"""Cross-reference placeholder syntax used in description metadata.

Placeholders have the form ``{kind:target}`` and live inside class docstrings,
``param_descriptions`` values, ``update_<attr>`` docstrings, ``disambiguation``,
``pitfalls``, ``interactions``, and ``param_interactions`` values.

Consumers (mkdocs generator, the e-footprint-interface adapter, the test suite)
register a handler per kind and resolve placeholders at render or validation
time.
"""
import re
from typing import Callable, List, Tuple


PLACEHOLDER_PATTERN = re.compile(r"\{(\w+):([^}]+)\}")


def extract_placeholders(text: str) -> List[Tuple[str, str]]:
    """Return all ``(kind, target)`` pairs found in ``text``."""
    return PLACEHOLDER_PATTERN.findall(text)


def resolve_placeholders(text: str, handlers: dict[str, Callable[[str], str]]) -> str:
    """Replace every ``{kind:target}`` token in ``text`` using ``handlers``.

    Each handler receives the raw target string and must return the rendered
    replacement. An unknown ``kind`` raises ``ValueError`` so callers can opt in
    to which kinds they support (e.g. mkdocs accepts ``class``/``param``/
    ``calc``/``doc``; library-side tests reject ``ui``).
    """
    def replacer(match: re.Match) -> str:
        kind, target = match.group(1), match.group(2)
        handler = handlers.get(kind)
        if handler is None:
            raise ValueError(f"Unknown placeholder kind: {kind!r} in {match.group(0)!r}")
        return handler(target)

    return PLACEHOLDER_PATTERN.sub(replacer, text)
