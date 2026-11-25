"""Command class-reference formatting and lookup links, independent of example instances and visualization packages."""
from efootprint.narrate import narrate, planned


# @planned agent-guidance#class-reference Build documentation lookup names from ALL_EFOOTPRINT_CLASSES_DICT plus Source, source-value wrappers and documented timeseries builders, leaving modeling registries unchanged.


def render_lookup_links(text: str, *, target: str = "command") -> str:
    planned("agent-guidance#class-reference:lookup-links", "Resolve class, member, topic and Markdown page links as installed lookup commands or website links.")
    raise NotImplementedError("planned: agent-guidance#class-reference")


def render_class_reference(cls) -> str:
    narrate.planned("class-metadata:read-metadata", "The class supplies its **inherited descriptions, inputs, defaults and computed docstrings** without constructing an example.", changes=("agent-guidance#class-reference:reference-text",))
    narrate.planned("class-metadata:format-reference", "The reference **formats that metadata for the command**, with lookup commands for linked classes and topics.", changes=("agent-guidance#class-reference:reference-text", "agent-guidance#class-reference:lookup-links"))
    planned("agent-guidance#class-reference:reference-text", "Format inherited class metadata, constructor and class defaults, units, choices and computed docstrings for command output through `render_lookup_links`, without constructing objects.")
    raise NotImplementedError("planned: agent-guidance#class-reference")
