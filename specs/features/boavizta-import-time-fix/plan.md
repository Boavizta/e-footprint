# Boavizta import-time network calls — bug-fix plan

**Status:** Plan — under review. Bug-fix style (no separate spec; this single file is the plan).
**Origin:** EcoScan feedback (interface `user_research/2026-05-19-ecoscan.md`).

## The bug

Importing `BoaviztaCloudServer` performs **N+1 live HTTP calls at module-import time**:
`efootprint/builders/hardware/boavizta_cloud_server.py:19-31` calls the Boavizta API for the provider
list and then once per provider for instance types, because those results populate class-level
`list_values` (provider enum) and `conditional_list_values` (instance-type enum) evaluated when the
class is defined. `all_classes_in_order.py` imports `BoaviztaCloudServer`, and ~19 core modules import
`all_classes_in_order`, so **any real use of the library hits the network at import**. The only cache
is process-local (`boaviztapi_utils.py`, 7-day TTL, in-memory), so every fresh process (each pytest
run, each CLI invocation, each interface worker start) re-fetches. Consequences: slow/flaky imports,
broken offline use, and tests that must mock or tolerate the network.

(The *per-instance* impact call — `update_api_call_response` — is separate and correctly lazy, run
during computation, not import. It stays as-is.)

## Fix: bundle an on-disk snapshot, load it at import instead of the network

Keep the provider/instance enums as class-level attributes (the framework and the interface read them
for validation and dropdowns), but populate them from a **bundled JSON snapshot** shipped with the
package rather than from a network call.

### Changes

1. **New bundled data file** — `efootprint/builders/hardware/boavizta_cloud_instances_snapshot.json`:
   the provider list plus each provider's instance types (the exact data the import-time calls fetch
   today). Add it to the `include`/package-data list in `pyproject.toml` so it ships in the wheel.

2. **`boavizta_cloud_server.py`** — replace the top-level `call_boaviztapi(...)` calls (lines ~19-31)
   with a small loader that reads the bundled JSON and builds `all_boavizta_cloud_providers` and
   `instance_types_conditional_list_values_dict` from it. No network, no `call_boaviztapi`, at import.

3. **Maintainer refresh script** — `scripts/refresh_boavizta_cloud_snapshot.py` (or a `doc_utils`
   helper): calls the live API for providers + instances and rewrites the JSON. Run periodically / at
   release. Document the step in `RELEASE_PROCESS.md`.

4. **Per-instance impact call** — unchanged (lazy, on-demand, with the existing package/offline
   fallback in `boaviztapi_utils.py`).

### Tradeoff to accept (and document)

Validation of `provider` / `instance_type` is then bound to the snapshot: a provider/instance Boavizta
adds *after* the last snapshot refresh won't validate until the snapshot is refreshed (at release).
This is the right trade — deterministic, offline, fast imports beat always-current enums — and refresh
is a documented release step. (Do **not** add a "fall back to live API if not in snapshot" path: it
would re-introduce import-/validation-time network and defeat the fix.)

## Tests

- **No network at import:** a test that patches `requests.get`/`requests.post` (and
  `call_boaviztapi`) to raise, then imports `BoaviztaCloudServer` / `all_classes_in_order` and
  constructs a `BoaviztaCloudServer` — succeeds with enums populated from the snapshot.
- **Snapshot integrity:** the bundled JSON exists, parses, and is non-empty (has providers, and
  instances per provider).
- **Existing tests** that relied on the import-time-fetched lists (e.g.
  `test_raises_error_if_wrong_instance_type` in `tests/builders/hardware/test_boavizta_cloud_server.py`)
  still pass, now sourcing the enum from the snapshot.
- Optional: a test (network-gated / skipped if unreachable, mirroring the existing
  `test_web_api_and_package_dependency_calls_return_same_results`) asserting the snapshot isn't wildly
  stale vs the live API.

## Quality gates

- JSON snapshot included in package data (`pyproject.toml`).
- Full pytest suite green; serialization round-trip unaffected (no `ModelingObject`/schema change).
- `CHANGELOG.md` entry (`[FIX]`).

## Out of scope

- Making the per-instance impact call cached-on-disk (separate; it's already lazy).
- Any change to the in-memory `boaviztapi_utils` cache behaviour.
