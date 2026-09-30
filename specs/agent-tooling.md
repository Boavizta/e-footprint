# Shared agent workflow and local usage tooling

The library is the canonical authoring checkout. Both repositories commit complete copies of
shared skills, role instructions, runtime agent definitions, collector code and tests. Each
checkout works on its own; neither installs a new package into the product environment.

Local adaptations live in `.agents/repository.md` and `ai-usage/config.json`. Skills point there
for architecture, validation and review-risk details. Both architecture entry points are
`specs/architecture/index.html`.
Plans link relevant architecture without adding an architecture tutorial.

## Synchronization

From the library root:

```sh
python3 scripts/sync_agent_tooling.py --target ../e-footprint-interface --check
python3 scripts/sync_agent_tooling.py --target ../e-footprint-interface
```

The explicit file list in `.agent-tooling-sync.json` owns only shared files. Local references,
collector configuration, `AGENTS.md`, secrets/local settings, and interface-only skills remain
untouched. The manifest stores the last synchronized hashes: destination edits cause a conflict
instead of being overwritten. Reconcile a useful interface change back into the canonical copy.
`--accept-target-overwrite` is for reviewed bootstrap/reconciliation only. A removed manifest path
requires explicit retirement; the script never sweeps directories or deletes local files.
When invoked from the interface, pass `--source ../e-footprint --target .`.

To add a shared file, add its relative path to the library manifest, then synchronize. No template
expansion: shared instructions read the repository's small local reference at runtime.

## Agent roles

| Role | Codex | Effort | Claude Code equivalent |
|---|---|---|---|
| implementer | gpt-6.1-sol | medium | claude-opus-5-5[1m] |
| implementer-hard | gpt-6-astra | high | claude-fable-5-1[1m] |
| reviewer | gpt-6-astra | high | claude-fable-5-1[1m] |
| diagnostician | gpt-6.1-sol | high | claude-fable-5-1[1m] |
| reviewer-shadow (optional experiment) | gpt-6.1-sol | high | claude-opus-5-5[1m] |

The supervisor/planning session preferably uses Astra/high (Fable/high in Claude). These are
starting configurations, not equivalent capability or effort scales proven across providers.
An explicit user model choice overrides the default workflow recommendation.

Portable role instructions live in `.agents/roles/`; `.codex/agents/*.toml` and
`.claude/agents/*.md` are thin runtime adapters. When a Codex runtime exposes only a generic
spawn tool, pass the configured model/effort explicitly and the role instructions in the brief.
If a runtime cannot apply a requested setting, report it and use the user's permitted alternative;
never claim an unobserved model pin worked. A role description is not a tool permission boundary.
The normal reviewer can apply approved fixes on resume; the shadow must remain read-only.

Use a fresh context for specification → plan → tasks and for each implementation run. This is a
handoff convention, not authority to create new user-owned Codex tasks without a request.
Read independent files in batches. Task preparation stays in one session: the same agent writes
the overview and every brief in dependency order, then presents any plan proposals together.
Implementation remains ordered by task dependencies. Never share stateful test suites or mutable
application databases between parallel agents.

Label delegated work `<feature>--impl-task-N`, `--review-task-N`,
`--diag-<bug>`, `--review-global` or `--gate-full`. In Claude place the label in the description;
use plain unnamed subagents so role effort is not lost to teammate inheritance. Do not transfer
that Claude-specific naming workaround to Codex. Stable session bindings below are preferred
where labels cannot carry the owner, run or runtime identity reliably.

## Implementation review

An authorized feature run completes implementation and reviews autonomously. The plan carries
only consequential choices, tagged `IMPL-DECISION`; task status and unresolved prerequisites stay
in `tasks.md`. Minimal handoffs give agents exact commit ranges and material review pointers.
Routine fixes and successful test results are omitted from review artifacts and reports; required
checks still run, and unresolved failures remain visible. No separate judgement or gate journals.
See `feature-implement` for the decision format and exceptional interruption conditions.

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

Claude SessionStart/SessionEnd hooks collect in the background. Codex workflow sessions should
collect explicitly at stage/run start and before close-out; no unsupported Codex hook is assumed.
Collect again later to include the closing response: close-out usage is always a timed snapshot.
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
are imported and have not been independently verified against provider pricing; refresh them
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
python3 scripts/sync_agent_tooling.py --target ../e-footprint-interface --check
```

The synthetic fixtures exercise both formats, repeated/partial counts, retention, attribution,
pricing and synchronization conflicts without touching a dev server or application database.
Product changes still follow their repository's constitutional gates.
