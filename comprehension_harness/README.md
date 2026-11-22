# comprehension_harness

A project's comprehension harness is the layer between a reader and its code: the narratives the
code tells itself, the plan of a feature read at the places it changes, the pages generated from
both. This package builds and maintains that layer. It is copied into a project and stays editable
there; nothing is installed from a registry.

The method it serves is `specs/workflow.md`; the forms it holds a feature's files to are
`specs/workflow-formats.md`; what a stack must give it is [`stack.md`](stack.md), and as types
`stack.ts`.

## What is copied

| Files | What |
|---|---|
| `comprehension_harness/` | The tools (the renderers, the plan model, the map, the local app) and their tests |
| `comprehension_harness/python/` | The stack of a Python project and its tests. Its own list, `python`: a project in another language leaves it |
| `specs/comprehension_harness/comprehension_harness.css` | The pages' stylesheet |
| `specs/review-links.js` | The script the pages load: it points each source link at this checkout and adds the right-click menu |
| `specs/workflow.md`, `specs/workflow-formats.md` | The method and its forms |
| `.agents/skills/` | `code-map`, `spec-specify`, `spec-plan`, `spec-tasks`, `feature-implement`, `task-implement`, `task-review`, `feature-archive`, `update-constitution` |
| `.agents/roles/` | `implementer`, `implementer-easy`, `implementer-hard`, `reviewer`, `reviewer-global`, `light` |
| `tools/vscode-plan-review-links/` | The editor extension behind the pages' right-click menu and their debug links |
| `scripts/sync_agent_tooling.py`, its test | What keeps a project's copies in step with the reference's: "Keeping the copies in step" below |

They are written for any project. What a project is to them is the three things it writes itself:
`comprehension.config.json`, its stack, and `.agents/repository.md`.

## Installing it in a project

1. **Node, with `tsx` and `typescript` as development dependencies.** The tools are TypeScript
   and run under Node whatever the project's language. They need no `tsconfig.json` and no
   `"type"` in `package.json`. To run the tools' own tests, `vitest`: always with the folder
   (`npx vitest run comprehension_harness`) where the project's other `*.test.*` files belong to
   another runner, which a bare `vitest run` would collect.

2. **`comprehension.config.json` at the repository root.** `config.ts` says what each key means
   and stops, naming the key, when one is missing or of the wrong shape: the project's name, its
   stack, the cache folder, the documents' folder, the name of the page the product narratives
   are drawn on, what a file is by its path, the pages whose entries mark a step, the commands
   that run a tool, the narrative tests and the journeys. Two of the commands are held to more
   than their shape: `tests` is typed with test paths after it, and `watch` must keep running,
   since the local app stops when it exits. A runner with no watch mode needs a small loop of
   the stack's own. One key is optional: `repositories`, the checkout of another repository by
   its name, for a plan that points at a piece planned there.

3. **The stack**, which gives the tools four things ([`stack.md`](stack.md) is its contract):
   - the three calls (`narrate`, `event`, `planned`) in the product's code, inert in production,
     and its own: a project's code imports nothing of this folder;
   - a collector that writes what each test crossed as a story file under `<cache>/stories/`;
   - the source index and the test titles: a module for a stack that runs in Node, or two
     commands that print them as JSON (`json-source.ts`, `json-titles.ts`;
     `tests/fixtures/shop/` is an index written by hand to conform to);
   - optionally, a journey helper that writes screens, captures and cases under
     `<docs>/design/journeys-generated/`. Without it a feature's spec is its `spec.md` alone.

   A Python project that tests with pytest takes `python/` and writes none of the four but the
   journey helper: "The Python stack" below.

   Everything else of this list can be done before the stack exists. The tools then stop and
   name what is missing: the command of the configuration that failed, the narrative tests that
   do not pass, or the stories no run has written.

4. **Four scripts in `package.json`**, under these names: the tools print them in their hints.

   ```json
   "map": "node comprehension_harness/map.mjs",
   "comprehension": "tsx comprehension_harness/dev.ts",
   "comprehension:render": "tsx comprehension_harness/render.ts",
   "journey:render": "tsx comprehension_harness/journey-render.ts"
   ```

5. **What git ignores.** The pages are generated and never committed; their hand-written heads
   are. With `specs` as the documents' folder:

   ```gitignore
   specs/comprehension_harness/narratives/*.html
   specs/comprehension_harness/mechanisms/*.html
   !specs/comprehension_harness/**/*.skeleton.html
   specs/comprehension_harness/plans/
   specs/design/journeys-generated/
   specs/features/*/plan-feedback.json
   ai-usage/.state/
   ```

   Also the cache folder the configuration names, when it is not already under an ignored one,
   and the generated `spec.html` of a feature whose spec is a `spec.md`. `ai-usage/.state/` is
   where the map logs each call, on this machine only.

6. **`.agents/repository.md`**, which the skills and the roles read. They point at these
   sections by name: "Documents", "The stack" (how this stack spells a `planned` call, a shell,
   a planned test, a narrative, a journey; a test's tier; the product's folders), "Commands",
   "Gates", "Planning checks", "Lots", "Review surfaces", "Autonomy", "Sub-agents and the ledger",
   "Archive".

7. **The runtime's adapters.** For Claude Code: `.claude/skills` is a link to `../.agents/skills`,
   and each role has a `.claude/agents/<role>.md` holding its description, its model and its
   effort, and one line: "Read `.agents/roles/<role>.md` and `.agents/repository.md` in the
   working repository and follow that role." A role's model is named there and nowhere else.
   Another runtime takes the same facts in its own format. The adapters and the runtime's
   settings are each project's own: they are in no shared list.

8. **Optional: the edit hook.** A `PreToolUse` hook on `Edit|Write` running
   `node comprehension_harness/map-hook.mjs` tells an agent, the first time it edits a file that
   carries a step or sits next to one, which steps and which test tell them. It reads a snapshot,
   speaks once per file per session, and can never fail an edit.

9. **Optional: the editor extension**, once per machine and not per project: package and
   install `tools/vscode-plan-review-links/` as its README says. A plain click on a source link
   of a page opened as a file works without it; the diff against the main branch, the debug
   entries (a vitest case, a pytest test) and a page served over HTTP need it.

## The Python stack

`python/` is the stack of a project in Python tested with pytest, standard library only but for the
plugin and the declarations, which are pytest's.

| File | Gives |
|---|---|
| `narrate.py` | The three calls, as the reference a project copies into its own package |
| `declare.py` | What a test declares: `@narrative`, `@canonical`, `@titled`, `@planned_test` |
| `collector.py` | The pytest plugin that writes the stories |
| `source_index.py`, `titles.py`, `watch.py` | The three commands of the configuration |

What the project writes to use it, the same in every project:

- **Its own copy of the calls**: `cp comprehension_harness/python/narrate.py <its package>/narrate.py`.
  Its code imports `narrate`, `event` and `planned` from that module, by name.
- `pytest_plugins = ["comprehension_harness.python.collector"]` in the conftest of its tests.
- In `comprehension.config.json`, `"stack": { "calls": "<its package>.narrate", "sourceIndex":
  ["python3", "-m", "comprehension_harness.python.source_index"], "titles": ["python3", "-m",
  "comprehension_harness.python.titles"] }` and `"watch": ["python3", "-m",
  "comprehension_harness.python.watch"]` under `commands`.
- `comprehension_harness/python/tests` among the paths its pytest run collects. A run that collects from
  the root takes them without a word, and leaves the tools' fixtures alone.

**A project's code imports nothing of this folder.** The calls are the one thing that runs in
production, and each project holds them in its own package, for two reasons. A published package
then needs nothing beside itself. And two projects compose: a project that depends on another
finds no shared module to clash on, and its test run collects its own calls alone, since each
copy has its own collector and a dependency's stays empty. A narrative never crosses a project.

Four tests hold that the calls cost production nothing. Where no collector is installed a call
returns at once and no watch is called. Their module imports the standard library alone. The
project's copy is the reference, word for word: the reference is edited, then copied. And since
Python computes a call's arguments before the call, the source index refuses a sentence that is
not a literal string and a watch that is not a lambda, in the project's own source at each
pytest run.

## Checking the install

```bash
npx vitest run comprehension_harness              # the tools' own tests, which read no project's file
node comprehension_harness/map.mjs                # the narratives, one line each
npx tsx comprehension_harness/render.ts --check   # every narrative, every plan, what does not hold
```

The first needs Node alone. The other two need the stack and a first narrative: the map runs
the narrative tests when its snapshot is older than the source, and the check reads their
stories.

The first flow to tell is the project's own choice: one `narrate` call per step and a test that
crosses them. The product page needs its hand-written head first, a title and a lede in
`specs/comprehension_harness/narratives/<productPage>.skeleton.html`; the render stops and says
so when it is missing.

## Keeping the copies in step

The reference repository lists the shared files in `.agent-tooling-sync.json`, in named lists;
`core` is this package but for `python/`, which is the list `python`. A project records what it took in `.agent-tooling-lock.json`: the lists,
the hash of each file at the last sync, and the reference's address, commit and licence. The
script is copied by hand once, and its first run brings the rest:

```bash
python3 scripts/sync_agent_tooling.py --upstream <the reference checkout> --lists core   # the first time
python3 scripts/sync_agent_tooling.py --upstream <the reference checkout> --check        # what a sync would do
python3 scripts/sync_agent_tooling.py --upstream <the reference checkout>
```

- A file changed on one side goes to the other, whole. A file changed on both is a conflict:
  the script shows both changes against the last synced version and overwrites neither. A
  person settles it by editing one side; nothing is merged.
- A push refuses a file that holds one of the lock's `private_words`, which is where a project
  writes the names it does not publish.
- After a push, the reference checkout is committed and the sync run again: the lock then names
  the commit that holds what was pushed.
- A file the reference no longer lists stays in the project until `--retire` drops it from the
  lock. No directory is swept and no file is deleted.

`python3 scripts/test_sync_agent_tooling.py` runs the script's tests, on checkouts built in a
temporary folder.
