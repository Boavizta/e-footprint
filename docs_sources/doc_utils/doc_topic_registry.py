"""Topic-id → mkdocs source filename mapping for the ``{doc:topic}`` placeholder.

Keys are the stable topic ids used in description strings; values are the
files under ``docs_sources/mkdocs_sourcefiles/``. Update this dict when
a topic is added, renamed, or removed — ``tests/test_descriptions.py``
validates that every key resolves to an existing file and that every
``{doc:}`` placeholder in library description strings targets a registered
topic.
"""

DOC_TOPICS: dict[str, str] = {
    "database_modeling": "database_modeling.md",
    "methodology": "methodology.md",
    "server_to_server_interaction": "server_to_server_interaction.md",
    "usage_edge_index": "usage_edge_index.md",
    "web_vs_edge": "web_vs_edge.md",
    "why_efootprint": "why_efootprint.md",
}
