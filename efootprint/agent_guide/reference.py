"""Command class-reference formatting and lookup links, independent of example instances and visualization packages."""
from efootprint.narrate import planned


# @planned agent-guidance#class-reference Build documentation lookup names from ALL_EFOOTPRINT_CLASSES_DICT plus Source, source-value wrappers and documented timeseries builders, leaving modeling registries unchanged.


def render_lookup_links(text: str, *, target: str = "command") -> str:
    planned("agent-guidance#class-reference:lookup-links", "Resolve class, member, topic and Markdown page links as installed lookup commands or website links.")
    raise NotImplementedError("planned: agent-guidance#class-reference")


def render_class_reference(cls) -> str:
    planned("agent-guidance#class-reference:reference-text", "Format inherited class metadata, constructor and class defaults, units, choices and computed docstrings for command output through `render_lookup_links`, without constructing objects.")
    raise NotImplementedError("planned: agent-guidance#class-reference")
