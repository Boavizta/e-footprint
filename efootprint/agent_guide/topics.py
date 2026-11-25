"""Canonical documentation packaged with the library."""
from efootprint.agent_guide.reference import render_lookup_links
from efootprint.narrate import planned


# @planned agent-guidance#canonical-topics Move DOC_TOPICS here, adding all eight specialized topics and the canonical introduction, methodology, Python-modeling, AI-workflow and bug-report pages.


def read_topic(name: str, *, target: str = "command") -> str:
    planned("agent-guidance#canonical-topics:topic-text", "Read packaged Markdown, expand named executable-source snippets and apply `render_lookup_links` for the requested presentation.")
    raise NotImplementedError("planned: agent-guidance#canonical-topics")
