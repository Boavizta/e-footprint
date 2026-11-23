# Shared agent workflow and local usage tooling

This repository is the reference for the files it shares with other projects: the comprehension
tools, the stage skills, the roles' instructions, the method's documents and the review-link
extension; and, with the library, the bug-batch skills and the usage collector. Every project
commits complete copies and works on its own; none installs a package into its product
environment.

What a project is to the shared files, it writes itself, and nothing synchronizes it:
`.agents/repository.md`, `comprehension.config.json`, `ai-usage/config.json`, its settings and
its runtime adapters (`.claude/agents/`, `.codex/agents/`). Skills point at
`.agents/repository.md` for architecture, validation and review-risk details. Both architecture
entry points are `specs/architecture/index.html`.

The method is [`workflow.md`](workflow.md); the forms of a feature's files are
[`workflow-formats.md`](workflow-formats.md); the tools, and how a project installs them, are
[`comprehension_harness/README.md`](../comprehension_harness/README.md).

## Synchronization

`.agent-tooling-sync.json` here is the manifest: lists of shared files, each named explicitly.

| List | Holds | Taken by |
|---|---|---|
| `core` | The comprehension tools and their tests, the stylesheet and the script of the generated pages, the method's two documents, the stage skills, the roles' instructions, the review-link extension, the synchronization script and its test | Every project that uses the method |
| `python` | The Python stack of the comprehension tools, `comprehension_harness/python/`, with its tests: the three calls, the test declarations, the pytest plugin, the source index, the title reader and the watch loop | Every Python project that uses the method |
| `python-journeys` | The journey helper of the Python stack, with its page script and its tests: a journey drawn from a run of a browser test | A Python project whose browser tests run on pytest and Playwright |
| `e-footprint` | The bug-batch skills of the `plan.html` form with their references, their two roles and their link converter, the usage collector, the Codex hooks, this page | The library |

A project that takes lists runs the script from its own checkout, with this one as upstream:

```sh
python3 scripts/sync_agent_tooling.py --upstream ../e-footprint-interface --check
python3 scripts/sync_agent_tooling.py --upstream ../e-footprint-interface
```

Its first run names the lists it takes (`--lists core e-footprint`). The script writes a lock in
that checkout, `.agent-tooling-lock.json`: the lists, the hash of each file at the last sync, and
this repository's address, commit and licence. Nothing is written here but the files themselves.

- A file changed here only is pulled there. A file changed there only is pushed here, where it
  reads as an ordinary diff to review and commit.
- A file changed on both sides is a conflict, and neither side is overwritten. The script shows
  both changes against the last synced version, read here at the locked commit; a person settles
  it by editing one side. Nothing is merged automatically. `--settle here` or `--settle upstream`
  is for a reviewed bootstrap only.
- A push refuses a file that holds one of the lock's `private_words`: what a project does not
  publish never arrives here.
- A path taken off the manifest stays in the other checkout until `--retire` drops it from its
  lock. The script never sweeps a directory and never deletes a file.
- No template expansion: shared instructions read the repository's local reference at run time.
  A difference that lasts goes into the shared file or into `.agents/repository.md`.

To share a new file, add its path to a list here, then synchronize.

The library's checkout still carries the script and the manifest of the time it was the
reference. Do not run that script toward this repository. The library takes the lists in a later
step, with the adjustments its own skills need.

## Agent roles

The runtime agent definitions are the single source of truth for each role's model and effort:
`.codex/agents/<role>.toml` for Codex and `.claude/agents/<role>.md` for Claude Code. They are
each repository's own. Read the selected runtime's agent definition at dispatch time; do not
infer one runtime's settings from the other or copy them into workflow guidance. The configured
roles are `implementer-easy`, `implementer`, `implementer-hard`, `reviewer`, `reviewer-global`
and `light`, with `diagnostician` and `plan-review-guide` for a bug batch.
The supervisor/planning session preferably uses the configured `implementer-hard` settings.
An explicit user model choice overrides that workflow recommendation.

A lot's difficulty (`easy`, `standard` or `hard`; for a bug-batch task, its `Implementation:`
line) selects the corresponding implementer role, by the
[difficulty rules](../.agents/skills/spec-tasks/SKILL.md#difficulty). Standard is the default;
easy covers well-defined transformations and known-cause fixes, including broad mechanical
renames. Review depth and required checks remain independent.

Portable role instructions live in `.agents/roles/`; `.codex/agents/*.toml` and
`.claude/agents/*.md` are runtime adapters. When a Codex runtime exposes only a generic
spawn tool, read the chosen `.codex/agents/<role>.toml` and pass its model/effort explicitly
with the role instructions in the brief.
If a runtime cannot apply a requested setting, report it and use the user's permitted alternative;
never claim an unobserved model pin worked. A role description is not a tool permission boundary.
The `reviewer` role reads one lot's commits, or one task of a bug batch; `reviewer-global` reads
the whole delivery once its last lot is reviewed. Both can apply approved fixes. `light` runs a
suite or a lookup and reports the evidence.
The plan-review-guide role performs the final documentation pass of a bug batch after global review and corrections;
it preserves the approved plan and adds implementation evidence. The supervisor owns consequential
decisions and checks changed claims. Substantial unresolved tracing escalates to the standard
implementer; see [the skill](../.agents/skills/plan-review-guide/SKILL.md). Adjust its agent
definition when observed correction effort warrants a different model or effort.

Use a fresh context for each of specification, plan and tasks, and for each implementation run. This is a
handoff convention, not authority to create new user-owned Codex tasks without a request.
Read independent files in batches.
Implementation follows the delivery's order of lots. Never share stateful test suites or mutable
application databases between parallel agents.

Label delegated work `<feature>--impl-lot-<lot>`, `--review-lot-<lot>`, `--review-global` or
`--gate-full`, `<lot>` being the lot's slug; for a bug batch `--impl-task-N`, `--review-task-N`,
`--diag-<bug>` or `--plan-review-guide`. In Claude place the label in the description;
use plain unnamed subagents so role effort is not lost to teammate inheritance. Do not transfer
that Claude-specific naming workaround to Codex. Stable session bindings below are preferred
where labels cannot carry the owner, run or runtime identity reliably. A lot's label gives the
ledger the feature and the role; only a task's label carries a number it records.

## Implementation review

An authorized `feature-implement` run delivers one lot, then stops for the reviewer
([`workflow.md`](workflow.md) § 4). A decision is written into the plan and nowhere else: a
`Changed:` paragraph for what changes a line of it, a `Note:` for a choice the next lot stands
on. What only the user can do goes to the feature's gates file. A bug batch keeps its
`tasks.md`, and records a consequential choice as an `IMPL-DECISION` callout of its `plan.html`.
Routine fixes and successful test results are omitted from review artifacts and reports; required
checks still run, and unresolved failures remain visible. No separate judgement or gate journals.

The retired Astra/Sol shadow-review comparison and its early-stop decision are recorded in the
library's `specs/features/workflow-improvements/shadow-review.md`.

## Local usage collection

```sh
python3 ai-usage/usage.py collect
python3 ai-usage/usage.py report
python3 ai-usage/usage.py report --surface credits
python3 ai-usage/usage.py report --owner e-footprint-interface --feature feature-slug --run A --json
```

The collector reads local Claude Code and Codex JSONL transcripts. It selects only this repo,
its configured sibling, their Git worktrees, and the shared workspace root when both siblings
exist. Standalone clones collect their own repo. Other projects are excluded. No network calls,
API credentials, prompt bodies or tool outputs enter the ledger.

Each checkout defaults to its MAIN checkout's `ai-usage/.local/ledger.sqlite3`; ephemeral
worktrees therefore do not strand history. This directory is gitignored, including hook logs.
Set `AI_USAGE_DATA_DIR` or `--data-dir` (before the command) to use an existing private backed-up
location. Back up the ledger deliberately: local disk alone is not durable across machine loss.
SQLite transactions serialize concurrent collectors. Existing requests survive source deletion;
`collect --full` re-parses retained sources, reconciling their previous observations without
clearing history from sources that no longer exist. Changed source facts can therefore be corrected.

The two repo copies may see the same sessions. Request identities deduplicate them when reporting
across ledgers:

```sh
python3 ai-usage/usage.py report --ledger ../e-footprint-interface/ai-usage/.local/ledger.sqlite3
```

Claude (`.claude/settings.json`) and Codex CLI/desktop (`.codex/hooks.json`) SessionStart/SessionEnd
hooks collect in the background. Codex runs project hooks only after they are trusted (desktop "Review
hooks" prompt or CLI `/hooks`), again after each change. Its SessionEnd fires on archive, normal exit or 30 minutes idle
and is capped at 3 s, so it detaches the collector. Workflow stages still collect explicitly at
start and close-out; collect again later to include the closing response: close-out usage is always
a timed snapshot.
Failures are recorded and surfaced, never a reason to abandon otherwise authorized product work.

### Attribute current work

Register the actual provider session ID, not a display title. For Claude subagents the ID is
`<parent-session>/<agent-id>`; for Codex it is the native subagent thread ID.
Codex normally exposes the current thread ID as `$CODEX_THREAD_ID`; use the returned native ID
for delegated agents rather than the supervisor's environment variable.

```sh
python3 ai-usage/usage.py bind --provider codex --session SESSION_ID \
  --owner e-footprint-interface --feature feature-slug --stage implement --run A --role supervisor
python3 ai-usage/usage.py bind --provider codex --session CHILD_ID \
  --owner e-footprint-interface --feature feature-slug --stage implement --run A --task 2 --role implementer
```

Bind at the beginning of the work. For a child that already started, supply `--since` with its
known start timestamp; the default is now so a reused session is not retroactively attributed
in full. Each binding **replaces** the previous local attribution from that timestamp onward:
repeat the fields you want to retain; omitted task/run fields do not leak into the next feature.
Children inherit owner/feature/run/stage from their recorded parent **at child creation**, when
available, but role/task belong to the child. A child's omitted scope fields use that inherited
scope. Supply a full binding when the runtime does not record the parent.
Bindings are private metadata, and can be added before or after collection. Inferred labels and
skill invocations are fallbacks; unknown attribution stays visible. Cross-repo tasks use the
DRIVING repo as owner and retain the execution project independently.

### Accounting and limitations

- Claude repeated content blocks share one request identity; partial counters use their maxima.
- Codex repeated cumulative snapshots count once, including unchanged totals at turn boundaries.
  The collector reads last-request usage, never
  sums cumulative counters, and deduplicates copied fork prefixes by event identity.
- Input is normalized into uncached input, cache reads and cache writes. Output already includes
  reasoning: never add reasoning again. Unknown cache-write counts remain unknown.
- Initial subagent work is turn 0; resumed work is follow-up, which can include questions as well
  as fixes. Active spans exclude idle waits after completion where transcript boundaries exist;
  main-session durations can still include human idle time.
- First edit is the first explicit Edit/Write/apply_patch tool. Shell-mediated edits are not
  classified, so these fields are a partial exploration-time measure, not a universal productivity
  score. Missing evidence stays null.
- Reports retain task owner/feature/run/task identity, initial/follow-up amounts, models/efforts,
  attempts and active durations. Durations include only fully attributed turns; a turn split across
  tasks/filters is counted as partial instead of charging its entire duration to each task.
  Compare complete feature cost including planning, briefs,
  supervision and global review alongside actual accepted findings, parked tasks and regressions.
  A lower token total alone is not a quality improvement.
- Parsing follows internal local formats, not a stable billing API. A malformed interior record
  or invalid numeric usage fails that source visibly; a partial last line is retried next time.
  CLI/extractor versions remain in run records. Source absence and unpriced usage are not zero.
  Reports retain the last collection errors/warnings and registered intervals without measurements.
  They cannot detect agents that were neither registered nor present in local transcripts.

`prices.json` is a dated factor set. Reports explicitly revalue usage at that factor date, not at
an invented historical price. Retain old cards if historical comparisons matter and select one
with `report --prices PATH`. Models match exact IDs after only documented decorations are removed;
unknown prices produce an incomplete subtotal with counts/reasons, never a complete-looking zero.

The 2026-09-30 OpenAI rate card includes [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
and [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), including recorded automatic approval-review usage,
using [API pricing](https://developers.openai.com/api/docs/pricing) and
[Codex credits](https://learn.chatgpt.com/docs/pricing). Earlier model IDs retain separate rates
for recorded usage. API-equivalent token pricing applies context bands (>272K), cache writes and
Fast/Batch/Flex multipliers. Codex credits have no separate cache-write charge. Their Fast multiplier
is 2× for purchased credits and Enterprise pay-as-you-go; the 2.5× included-subscription usage
multiplier is not a credit rate. Fast multipliers are stored separately for each pricing surface.
When processing mode is absent, reports
assume Standard and count those assumptions explicitly; the observed Codex logs do not expose
this setting. Known unsupported regional conditions remain unpriced. API-equivalent reports omit
provider-side tool charges and are not invoices or subscription quota measurements. Claude factors
are imported and have not been independently verified against provider pricing, except Claude Haiku 5.5: its two rate cards (split at a 100K-token prompt, stored as
`long_prompt` in `prices.json`) follow the published input/output rates and cache multipliers. Claude Fable 5.2
likewise follows the published pricing page, including its fast-mode multiplier. Refresh them
before relying on a new model's estimate. No cost or carbon estimate is
stored as a raw fact. Environmental factors and uncertainty belong in a separately documented
model over these measurements.

An optional aggregate export is deliberate and contains no prompts:

```sh
python3 ai-usage/usage.py export --output /tmp/usage-daily.csv
```

Do not automatically stage private ledgers or exports into public commits.

## Validation

```sh
python3 -m unittest discover -s ai-usage/tests -v
python3 scripts/test_sync_agent_tooling.py
npx vitest run comprehension_harness
node --test tools/vscode-plan-review-links/extension.test.js
```

The synthetic fixtures exercise both transcript formats, repeated/partial counts, retention,
attribution and pricing; the synchronization tests build their checkouts in a temporary folder;
the tools' tests read no file of the project. None touches a dev server or an application
database. Product changes still follow their repository's constitutional gates.
