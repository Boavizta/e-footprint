"""The reading order of the installed-version modeling guide."""
from efootprint.agent_guide.reference import render_lookup_links
from efootprint.agent_guide.topics import read_topic
from efootprint.narrate import planned


def render_guide(*, target: str = "command") -> str:
    planned("agent-guidance#guide-assembly:default-guide", "Assemble selected canonical sections using `read_topic`, executable snippets and registry-derived lookup catalogues rendered by `render_lookup_links`.")
    raise NotImplementedError("planned: agent-guidance#guide-assembly")
