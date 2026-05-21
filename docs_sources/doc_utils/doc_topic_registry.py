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
    "development_process": "development_process.md",
    "ecodesign_strategies": "ecodesign_strategies.md",
    "efootprint_scope": "efootprint_scope.md",
    "explanation_overview": "explanation_overview.md",
    "get_started": "get_started.md",
    "hardware_edge_index": "hardware_edge_index.md",
    "machine_learning_workflow": "machine_learning_workflow.md",
    "methodology": "methodology.md",
    "object_reference": "object_reference.md",
    "only_CO2": "only_CO2.md",
    "server_to_server_interaction": "server_to_server_interaction.md",
    "usage_edge_index": "usage_edge_index.md",
    "web_vs_edge": "web_vs_edge.md",
    "why_efootprint": "why_efootprint.md",
}
