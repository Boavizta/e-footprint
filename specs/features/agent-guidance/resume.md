# Resuming agent guidance

Agent guidance is on hold until
[Executable modeling documentation](../executable-modeling-documentation/spec.md) is delivered
and reviewed. Do not implement, approve or prepare delivery from the current plan or preview.
Its existing source annotations and planned tests are retained as review context, not moved or
implemented by this spec change.

## Start from the delivered sources

In a fresh session, read the new feature's delivered scenario sources, example registries,
documentation, generation conventions and tests, then this feature's spec, plan and preview.
Use the map to re-ground the work in the current code. Do not assume the new feature kept any
proposed path, tag spelling or generation mechanism from the earlier discussion.

Revise the agent-guidance spec and obtain review of its changed requirements before replanning.
In particular, replace its requirement for one separately authored full mixed reference script
with reuse of the delivered tutorials/examples. Settle which complete examples the default guide
includes and which it offers as lookups, preserving sufficient context for web and edge modeling.
Revisit the exclusion of tutorials from topic lookups.

## Reconcile the existing pieces

- `#canonical-example` and `#executable-doc-examples`: reuse delivered scenario code, runnable
  selections and documentation excerpts. Remove or replace the obsolete reference-system shells,
  source annotations and planned tests when the plan is revised. Do not port `docs_case` into
  another broad model or exclude Boavizta-backed examples to avoid their modeling requests.
- `#python-guidance` and `#modeling-workflow`: inventory what the tutorials now teach about units,
  sources, builders, countries, volumes, editability, public reads/updates and exports. Reuse that
  content; author only remaining explanations in their canonical homes. Keep class/input semantics
  in metadata, and retain the AI collaboration workflow where it is specific to that workflow.
- `#support-results`: keep interpretation prose in methodology and link to the delivered Python
  result-inspection sections. Do not put executable Python recipes in methodology merely to feed
  the guide. Bug-reporting guidance remains in its own canonical documentation.
- `#guide-assembly` and `#canonical-topics`: replace the old source map, heading/region assumptions
  and tutorial exclusion with the delivered selection contract. Regenerate the preview from
  canonical content, check reading order and repetition, and reassess its size after selecting
  complete runnable sequences. Printed lookups must resolve in the installed version.
- `#example-discovery`: consume the delivered catalogue and its actual source, JSON and
  documentation paths, including IoT. Do not register a second reference example or introduce
  another catalogue for the same scenarios. Describe regeneration and user exports accurately.
- `#class-reference`: reuse the delivered example set and supplements for website completeness.
  Retain metadata-only command lookups; neither lookup printing nor class completeness requires
  every tutorial to contain every concrete class.
- `#command`: retain the bare-core, installed-version lookup contract. Printing guidance must not
  import notebook tooling, execute examples or contact external services. Running an example may
  make documented API requests and use documented extras; these are separate operations.
- `#trial-pitfalls`, `#trial-errors`, `#entry-pointers` and `#retire-chat-kit`: re-check their sites
  against the delivered code, keeping still-needed fixes and coverage. Retire the old chat kit
  only when the installed guide provides its useful guidance.

## Return to review

Use `spec-plan` in a fresh planning session after the revised spec is approved. Reconcile every
existing planned site and test with its new owner; remove superseded declarations as part of that
plan revision rather than delivering them accidentally. Preserve the trial briefs and their
stated limitations for the guide's eventual evaluation.

Update `plan.md`, its cross-cutting decisions, the preview and the roadmap together. Render the
pages, run the map/check and obtain approval of the revised plan before `spec-tasks` and delivery.
This hold is not approval of either the old plan or a replacement delivery.
