# Task 6 — Upgrade historical video inputs to version 26

Repositories and implementation ranges:
- e-footprint: `859a12b3dc22afb3006d293be5aee056350abd65..51833ac2`.
- e-footprint-interface: baseline `bf37139bb0fc6d1e1c9f1d5435c61be8f781cce3`; no implementation changes.

## Review pointers
- `upgrade_version_25_to_26()` queries the supplied video-job class with `allowed_values()` and edits only incompatible serialized resolutions, including disconnected jobs. Its provenance note mirrors the editor's history fields, with a migration-specific reason.
- The loader retains its original-file-version cache rule; the import regression checks both snapshot modes, preserved historical totals, fresh recalculation and current-version migration bypass.
- Seven golden serialization fixtures have only their version header advanced to 26.0.0; their complete regenerated payloads matched before those edits.

## Open concerns
- The supervisor verified PyPI currently exposes efootprint 25.0.0 and has no 26.0.0 release. A publishable version-26 interface requirement and resolved lock remain prerequisites for coordinated merge. Both repositories' pre-existing lockfile changes and the interface's editable dependency are preserved; publication is outside this task.
- Final interface unit/integration, Jest and focused browser validation remain part of the global cross-repository close-out.
