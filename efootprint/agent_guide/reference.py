"""Shared textual reference rendering, independent of example instances and visualization packages."""
from efootprint.narrate import planned


# @planned agent-guidance#class-reference Extend the existing class registry with Source, source values and timeseries builders needed by documentation lookups.


def render_lookup_links(text: str, *, target: str = "command") -> str:
    planned("agent-guidance#class-reference:lookup-links", "Resolve class, member, topic and Markdown page links as installed lookup commands or website links.")
    raise NotImplementedError("planned: agent-guidance#class-reference")


def render_class_reference(cls, *, target: str = "command") -> str:
    planned("agent-guidance#class-reference:reference-text", "Render inherited class metadata, constructor defaults, units, choices and computed docstrings through `render_lookup_links`, without constructing objects.")
    raise NotImplementedError("planned: agent-guidance#class-reference")
