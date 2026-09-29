# Local coding-agent usage

Run `python3 ai-usage/usage.py collect`, then `python3 ai-usage/usage.py report` from the repository
root. Full instructions, attribution, pricing semantics, scope and limitations are in
[`specs/agent-tooling.md`](../specs/agent-tooling.md#local-usage-collection).

This is development tooling, not part of the published library or Django runtime. It uses only
Python's standard library. The Claude request-deduplication, turn accounting, durable retention
and role attribution design were adapted from Pretext's `ai-usage/` (reviewed 2026-09-29); the
Codex adapter builds on this repo's article extractor while adding event deduplication, cache
writes, scope controls and durable storage. Neither source repository is needed at runtime.

Run synthetic tests with `python3 -m unittest discover -s ai-usage/tests -v`.
