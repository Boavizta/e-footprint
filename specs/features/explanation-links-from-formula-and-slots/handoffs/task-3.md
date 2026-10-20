# Task 3 — Schema 27 and interface adoption
Repositories and implementation ranges: e-footprint `336abf8f..2a62fd83` (single commit `2a62fd83`);
e-footprint-interface `667c0bf4..0e8ebe17` (single commit `0e8ebe17`, documentation only: one `rendering.html` item and
one `CHANGELOG.md` Unreleased entry). The brief's interface start `170d7931` is an ancestor of `667c0bf4`, the
interface HEAD when this run began.

## Review pointers
- `upgrade_version_26_to_27` (`efootprint/api_utils/version_upgrade_handlers.py`): walks only the efootprint class
  blocks (the registry, as the 25→26 handler does). The interface's saved files also carry a non-efootprint
  top-level `interface_config` block (sankey settings, lists inside), so the handler must not walk unknown keys;
  the handler test includes such a key. Within a class block it pops `direct_ancestors_with_id` from each attribute
  dict and from that dict's dict-valued entries, without recursing: `explain_nested_tuples` and the calculation
  graph are untouched.
- Fixtures: only the five inputs-only fixtures under `tests/integration_tests/`, the two modeling examples, and the
  version strings changed. The `*_with_calculated_attributes.json` fixtures still say `26.0.1` (and
  `simple_system_with_calculated_attributes.json` says `21.1.6`): they carry stored ancestors and are outside the
  brief's list. Loading them now runs the 26→27 handler, which drops those keys.
- Load test `test_version_26_file_with_stored_direct_ancestors_loads_and_saves_without_them`
  (`tests/api_utils_tests/test_json_to_system.py`) injects the key into a stored value of a `26.0.1` snapshot.

## Open concerns
- Interface reference data declares `efootprint_version` `26.0.1`: `model_builder/domain/reference_data/default_system_data.json`
  and the three introductory examples (`ai_chatbot`, `genai_video`, `iot_industrial`). Under the editable 27.0.0 library,
  `tests/integration/test_efootprint_version.py` and the three `test_scenario_constructor_round_trips_to_committed_json`
  cases fail. The only difference in the examples is that version string (checked on the ai_chatbot pytest diff).
  The interface suite is green at 26.0.1 (1049 passed with a library at `336abf8f`). Refreshing these strings
  (and re-running `python -m scripts.build_intro_examples`) belongs to the pin-move step after PyPI publication,
  not to this commit, since the pin is still 26.0.1.
- Interface suite under the editable library: 1045 passed, 4 failed (the reference-data version cases above).
- Pre-existing, out of scope, unchanged: `test_boavizta_cloud_instances_snapshot::test_snapshot_matches_live_boaviztapi_data`
  and `test_boavizta_utils::...same_results` fail on the full library suite (live Boavizta data, parked guard).
- Not run: the manual GenAI video browser check (Veo instances footprint, CDN use footprint, system total calculus
  graph). The supervisor owns it.
- Usage registration was not bound: no agent ID was exposed to this run.
