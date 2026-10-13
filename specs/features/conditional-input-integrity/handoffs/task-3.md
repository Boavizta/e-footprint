# Task 3 — Persist the automatic-replacement source

Repositories and implementation ranges: e-footprint `20c7ccda1abcde163b21be28dd9e3102b2356a06..67a83b9003af7f95fc2bbd40e70b85958b973bed`.

## Review pointers

- `_resolve_sentinel_source()` and `build_sources_dict_from_system_dict()` map `automatic_replacement` to the canonical singleton. The loader regression covers inputs-only and cached snapshots, plus the sentinel fallback and existing user-data/hypothesis identities.
- The serialized source payload remains the existing `id`/`name`/`link` shape; no snapshot fields or migration handler were added.

## Design decisions

- [PLAN-UPDATE-05](../plan.html#plan-update-05) defines the stable source identity and reuse during editor saves and upgrades.
