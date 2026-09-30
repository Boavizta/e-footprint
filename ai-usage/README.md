# Local coding-agent usage

Run `python3 ai-usage/usage.py collect`, then `python3 ai-usage/usage.py report` from the repository
root. Full instructions, attribution, pricing semantics, scope and limitations are in
[`specs/agent-tooling.md`](../specs/agent-tooling.md#local-usage-collection).

This is development tooling, not part of the published library or Django runtime. It uses only
Python's standard library. The Claude and Codex adapters provide request and event deduplication,
turn accounting, cache-write tracking, scope controls, durable storage and role attribution.

Run synthetic tests with `python3 -m unittest discover -s ai-usage/tests -v`.
