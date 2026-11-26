# What a stack gives the tools

The model, the pages, the approval, the lot check and the map are the same in every project and
run under Node. What differs with a language and a test runner is a **stack**: the code that
gives the tools four things. This page is the contract a stack is written to. As types it is
[`stack.ts`](stack.ts), which the tools and a Node stack both import.

| What | Written or answered by |
|---|---|
| **Stories**: what each test crossed, in order, with the call stack | A hook of the test runner, one JSON file per test file |
| **The source index**: every `narrate`, `event` and `planned` call with its function, where a named symbol is declared, each narrative's declaration, who calls what | A reader of the source: a compiler's API, or a script on the language's own parser |
| **Test titles**: planned and written, with the piece and the rule each names | A reader of a test file's text |
| **A journey run**: screens, captures, planned cases. Optional | A helper over the browser tests |

Two of the four are written by a test run: they are files in every stack. The other two are read
from the source at each render. A stack that runs in Node answers them with a module; any other
stack with a command that prints a JSON document, which a reader of this folder turns into the
same interface. Where each one lives is the project's configuration (`config.ts`).

`plan.md`, the `@planned` comments, the approval, the answers and the commits need nothing from a
stack: the comment scanner reads each file's own comment syntax, `#` included.

A parser without a type checker gives names, not identities. A link from a symbol of a sentence
to its declaration, and "Open call", are then found by name through the file's imports; two
methods of the same name on two classes can be taken for each other, and the remedy is the
qualified name in the sentence. A call found in a recorded stack needs no parser and is exact in
every stack.

## Rules the four share

- A path is relative to the repository root, with `/`. Lines and columns start at 1.
- **A site is a file and a line.** One `narrate`, `event`, `planned` or `built` call per line. A template makes the
  calls too, where the stack reads them: there a site is a tag, in no function.
- **A function has one name**: the one the stack's own frames print (V8's in JavaScript,
  `__qualname__` in Python). A story's frame and an indexed function are matched by `file` and
  `fn`.
- **A test has one title.** A story's `test`, a narrative's `firstTest` and the title reader's
  `title` are the same string for the same test.
- A document that does not have the shape below fails the render, naming the file. Nothing is
  skipped.

## 1. Stories: what each test crossed

One JSON array per test file, at `<stories>/<the test file, "/" written "__">.json`, `<stories>`
being `<cache>/stories` of the configuration. A file's run deletes its story file when it starts
and writes it when it ends, so a stale story is never read. A test that crosses no site has no
story, but for a reproduction; a file with no story writes no file. Every test is recorded, in a declared narrative or
not: the tests reaching a site are counted over all of them.

Collectors that observe fixtures mark each hit with its execution phase. Narratives are derived from
`call` hits alone, before step ownership, variants, mechanism links and statistics are derived. Setup and
teardown stay in the recorded story for coverage and plan evidence; a planned hit in setup is not a place
crossed by the narrative. A collector that records the test body alone omits the phase.

| Field | Holds |
|---|---|
| `file`, `test` | The test file and the test's title |
| `narrative` | `{ title, kind, scope? }` of the narrative the test is declared in, `kind` being `product` or `mechanism`; `null` outside one |
| `canonical` | The test marked itself the narrative's reference case |
| `order` | A number growing with the run: variants are told in that order |
| `state`, `durationMs` | Shown on the page, never judged. `xfailed` for a failure the run expected |
| `hits` | The calls crossed, in order |
| `reproduction` | Optional. The test is declared to fail today, for a bug its piece fixes: it has a story whatever it crossed |
| `failure` | Optional. How the test failed, of a failure the run expected too: `{ message, file, line }` |
| `capped` | Optional. `[{ file, line, phase?, kept, omitted }]`: a site keeps its first 50 hits per phase and counts the rest. A `built` call keeps its first hit per phase and counts nothing: one crossing tells where the place lands. Without phases, the limits apply to the test |

A hit:

| Field | Holds |
|---|---|
| `kind` | `step`, `event` or `planned` |
| `phase` | Optional. `setup`, `call` (the test body), or `teardown`; omitted when the collector records the test body alone |
| `planned` | For a `planned` hit: `{ feature, slug, change }`, with `place` where the call's tag names one. A `built` call is a `planned` hit whose change is `built` |
| `expect` | Optional, for a `planned` hit whose site says what it should see: that, at this crossing, a key of the watch each. `{ "error": "…" }` when computing it threw |
| `sentence` | As passed to the call |
| `watch` | The watch's value as plain JSON, or `null`. `{ "error": "…" }` when computing it threw, which never fails the test |
| `site` | The frame of the call: `{ file, line, column, fn }`, `fn` `null` for a function with no name |
| `stack` | The frames above it, nearest first, of the repository's own files only |
| `atMs` | Milliseconds since the phase began, or since the test began when no phase is given |

A collector may write fields of its own beside these. The tools read one of them when it is
there: `mappedFn`, a source-mapped name, where `fn` is `null`.

**A run started for a person writes no story and deletes none.** A debug run of one test would
leave its file's stories with that test alone, worded for a terminal. With
`COMPREHENSION_STORIES=off` in its environment a collector records as ever and leaves the story
files as the last whole run wrote them; the editor extension starts its debug runs so. The tools
run the files that hold a plan's reproductions themselves, whole, before they draw or check a
plan: by `commands.tests`, or by the command `commands.testsUnder` gives the folder a file is
under, so a runner configured apart from the unit tests installs the collector too. A browser's
are left out, and so are those of a folder `testsUnder` gives null.

The three calls are inert in production: none does anything unless a collector is installed,
which only a test run does. The watch is passed as a function the collector calls, so nothing
is computed for it outside a test.

### Intended narrative sequences

A stack can declare a narrative before its reference case runs. The source declaration adds
`intended: { steps: ["<flow>:<step>", …], test: "<reference test title>", planned: true }`;
`kind` on the declaration distinguishes a product narrative from a mechanism without a story.
`SourceReader.narrativeDeclarations()` returns these declarations, including those with no recording.
The ordered IDs come from the reference test, not from source order or a guessed call graph.

A named step adds `narration: { id, planned, changes: ["<feature>#<piece>:<place>", …] }` to its
source site. Its `kind` remains `step`, but a planned declaration never writes a story hit. A
promoted step keeps the ID with `planned: false`; a recorded hit may carry `step: "<flow>:<step>"`.
Planned steps do not establish coverage, step ownership or observed landings. Their change links
are explicit and optional, so a narrative can also describe existing behaviour.

The Python forms are `narrate.planned(id, sentence, changes=(…))`, and `@canonical(steps=(…))`
on the reference test under `@narrative`. A skipped `@planned_test` is intended; a written `@titled`
reference is checked against the first occurrences of its named `narrate(sentence, step=id)` calls
in the test body. Shell detection ignores the planned step declarations. A step ID is two kebab-case
names parted by `:`, independent of the feature whose change places it may link.

A narrative's optional `scope` is `"doc"` for documentation generation and authoring.
Declare it on the narrative, emit it in its story and source declaration, and omit it otherwise.
It is subject-area metadata: ownership, execution and intended/observed status remain unchanged.

## 2. The source index: what the source says without running

What the tools ask (`SourceReader`). The identity of a step (`<file>#<function>#<ordinal>`), and
finding again by its sentence a site whose line moved, are derived by the tools from the first
row.

| Asked | Answered with | How sure |
|---|---|---|
| The sites of a file | Each call: `kind`, `line`, `column`, `fn`, its sentence when it is a literal, and `hasWatch: true` when it declares a watch (omitted otherwise); for a `planned` call its tag, the place it names in it, whether it changes, removes or adds, and a shell's signature; a `built` call is a `planned` site whose change is `built`, with its tag, its place and an empty sentence | Exact |
| A narrative's declaration | In its test file: the line, the first paragraph of the comment above it, the title of its first test. Also: which test files declare one | Exact |
| Where a name of a sentence is declared, seen from a site | In order: an import of the file, a local of the functions around the call (nearest first), a top-level declaration of the file, one unique across the source. Otherwise the reason, for `--check` | Identities with a type checker, names without |
| The same with no site | For a name `plan.md`, a test title or a page of rules gives: in the files named beside it, else unique across the source, else nearest to the piece's places | Same |
| Where a function uses a symbol | The first line of a function (by `file` and `fn`) referring to the symbol declared at a place: "Open call" | Same |
| What a declared name is shaped like | A pattern: a token of a sentence, or of a page of rules, that has that shape and resolves to nothing is flagged | The language's own styles |
| The functions of a file | Each with the line its name is on and its last line. Optional: without it a place of a plan, and a change a lot made, are read by their file, not by their function | From `functions` |
| The function around a site | The nearest named function, its first and last line, who refers to it and what it calls, each marked as holding a `narrate` or not (`map step`, `map around`) | Candidates in both |

Symbol resolution and the static "Open call" lookup accept a source context (`SymbolContext`:
`file`, `line`, `column`, `fn`). Test descriptions use the test's declaration as that context, sharing the
sentence renderer's links and resolving names through the test's imports and local scope.

The stack's reader refuses, with the file and the line: a `planned` call whose tag or sentence is
not a literal, a tag that is not `<feature>#<slug>` or `<feature>#<slug>:<place>`, a place named
on a removing or an evidence call, a `built` call that is not one literal naming its place, a
shell that throws anything but `planned: <feature>#<slug>`.

The JSON form, for a stack that does not run in Node. The command prints it; it is asked for at
each render. [`json-source.ts`](json-source.ts) answers the interface from it, and
[`tests/fixtures/shop/`](tests/fixtures/shop/README.md) is an index written by hand for three
Python files: the example a stack's own index conforms to, checked line and column against its
source by the test.

```json
{
  "looksDeclared": "^(?:[A-Z][A-Za-z0-9]{2,}|_*[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$",
  "narratives": [{ "file": "tests/…", "title": "…", "line": 12, "summary": "…", "firstTest": "…" }],
  "files": {
    "app/importer.py": {
      "sites": [{ "kind": "step", "line": 41, "column": 9, "fn": "Importer.run", "sentence": "…" }],
      "functions": [{ "fn": "Importer.run", "line": 30, "column": 5, "endLine": 58 }],
      "declarations": [{ "name": "Importer", "line": 12, "column": 7 }],
      "imports": [{ "name": "parse_rows", "at": { "file": "app/parse.py", "line": 8, "column": 5 } }],
      "locals": [{ "name": "rows", "line": 33, "column": 9 }],
      "uses": [{ "name": "parse_rows", "line": 40, "column": 16, "at": { "file": "app/parse.py", "line": 8, "column": 5 } }]
    }
  }
}
```

- `looksDeclared` is the shape of a name the language declares, as the source of a regular
  expression its own engine and JavaScript read the same. A backticked token of that shape that
  resolves to nothing fails the check. It is the stack's to say, since the shape is the
  language's: words joined by an underscore are a function in Python, and in TypeScript a
  database column no sentence should be held to. A stack that runs in Node gives it as a
  `RegExp` (`SourceReader.looksDeclared`).
- `files` holds every file of the source folders and every test file that declares a narrative.
- A `planned` site adds `"planned": { "feature", "slug", "change", "signature" }`, `change` being
  `changed`, `removed`, `added`, `evidence` or `built`, and `"place"` where its tag names one. A
  `built` call is such a site, with its place and `"sentence": ""`. Evidence is a place a bug
  shows: it marks no change and goes with the fix. A changed or an evidence site may add `"expect"`: what the place
  should see, a key of its watch each, as the source writes it. It is a literal, or an expression
  computed at each crossing as a watch is, so the same rule keeps it inert; its value is the
  story's, a crossing at a time. Either may add `"distinct"`: the keys of its watch each crossing
  should see a value of its own for, a list of names. It is the source's alone: a bug shows there
  where two crossings of a test saw the same values for them, which the tools tell from the
  watches, and no story holds it.
- A site of a template has `"fn": "(template)"`, in a story too, and its file lists nothing but
  its sites.
- `functions`: every named function, with the line its name is on. A site or a local belongs to
  the functions whose lines hold it.
- `declarations` are the top-level ones; `locals` every other one (a parameter, a variable, an
  inner function, a method, a field).
- `imports` and `uses` give the declaration a name refers to, as far as the stack can tell; a
  reference it cannot place is left out, and so is what stands inside a `narrate`, `event` or
  `planned` call. Callers and callees are read from `uses`.
- The project's configuration names the two commands in place of a module, and optionally a
  third, `strip` ("The strip of an archive" below):
  `"stack": { "sourceIndex": ["python3", "…"], "titles": ["python3", "…"] }`.

## 3. Test titles: planned and written

Asked for one file's text, not for the checkout: the lot check reads a test file on both sides of
a commit. The answer:

| Field | Holds |
|---|---|
| `tests` | Every test in file order: `{ title, line, column, planned }`. `planned` is a test declared with no body: `it.todo` in vitest, a function under a marker that carries the title in pytest. `reproduction: true` is added for a written test declared to fail today, for a bug to fix. `body` is optional: a short hash of a written test's own lines, its declaration left out, so that it is the same once a reproduction is declared a test like another. An approval holds it for each reproduction, and the check lists one edited since |
| `stands` | For each line that opens a test, a group of tests or a declaration: `{ line, label, test }`. A `@planned` comment right above that line stands on it. `label` is what the pages print; `test` is the title when the line opens one test |
| `journeyCases` | The cases a feature will add to a journey, declared in a journey test: `{ feature, journey, screen, title, line, column }` |

A test of a plan carries its piece in its title, planned or written:
`<feature>#<slug>: <title> [<rule-slug>]`, the rule optional. The tools take the title apart.
Where a stack keeps such a title when a function name cannot hold it is the stack's own choice,
under the rule above: a test has one title, the same in its story.

The JSON form: the command reads `[{ file, text }]` on its input and prints
`[{ file, tests, stands, journeyCases }]` in the same order, one process for the whole batch
([`json-titles.ts`](json-titles.ts): a render says at once which files it will ask for).

Which files are test files, and which tier a test file is (narrative, server, unit), is
configuration, not the stack's.

## 4. A journey run: screens, captures, planned cases

Optional: without it a feature's spec is `spec.md` and the journey pages are not drawn. One
folder per journey, `<journeys>/<journey-slug>/`, `<journeys>` being
`<docs>/design/journeys-generated` of the configuration. A run rewrites its `cases/` and
`captures/` from nothing:

| File | Holds |
|---|---|
| `journey.json` | `{ name, slug, who, wants, now, viewport, file, todos }`, `todos` being the planned cases `{ feature, screen, title, line }` and `viewport` the `{ width, height }` the captures were taken at, left out for a phone's 400 × 800 |
| `cases/<line, 4 digits>-<case-slug>.json` | One case: `{ journey, title, slug, line, status, screens, after }`. The first case of the file is the reference run |
| `captures/<case-slug>/<nn>-<screen-id>.html` | The screen as a complete HTML document that opens with no server, `data-journey-screen="<journey-slug>#<id>"` on its root, its stylesheet linked under `css/` |

A screen of a case: `{ id, why, url, capture, css, sha, bytes, counts, returnsTo,
identicalToFirstVisit, movedSinceFirstVisit, controls, before, planned }`. `before` is what led
to it, a list of causes: `{ kind, url, type, key, control, on, elapsed, events, steps,
navigations, server }`, `kind` being `open`, `action` or `time`. `events` and `steps` are the
`event` and `narrate` calls crossed between two screens, each with its sentence and its site
`{ file, line, fn }`, wherever that code ran: in the browser for an app that runs there, in the
server process for a page the server renders. `server` lists the server steps a stub answered and
is empty when the journey runs against the real server. For a page the server renders, the run
has to see what the server crossed and which action it answers: the helper says how (the Python
stack serves the app from the test process, and each request carries the number of the action
before it). The types are `JourneyCase`,
`ScreenRecord` and `Cause` of `stack.ts`.

## Beside the four: the strip of an archive

Optional. `strip(file, text, feature)` of a Node stack gives one file's text with what the archive
of a feature takes off it, and the list of what went, each with its line:

- each `built` call of the feature, with the line it stands on and the import the file no longer
  uses;
- the tag and the rule of each test titled `<feature>#<slug>: <title> [<rule-slug>]`, which
  leaves `<title>`, the title's own escapes kept;
- each planned screen of a journey that names the feature.

A file the stack does not read comes back as it is. A `built` call that cannot go without
changing the code around it (an expression's operand, the only body of a branch, a line shared
with other code) is refused, with the file and the line. The strip reads the code and never a
pattern over the text: another feature's marks, and a tag written in a comment or a string that
is no title, stay. The tools choose the files, hold the strip to the archive gate, write the
result and read what still names the feature (`render.ts --strip`). The type is `Stripped` of
`stack.ts`. A stack that gives no strip has its marks listed, to take off by hand.

A stack that does not run in Node gives its strip as a command, `"strip": [command…]` beside
`sourceIndex` and `titles` in the configuration ([`json-strip.ts`](json-strip.ts)). It reads
`{ "file", "text", "feature" }` on its input and prints
`{ "text", "taken": [{ "line", "kind", "was" }] }`, `kind` being `built`, `title` or `screen`:
one process a file. It refuses by failing, the file and the line on its error output, which
the tools say as it is.

## Beside the four: a command that keeps the narrative tests running

The local app (`dev.ts`) starts the configuration's `commands.watch` with the narrative test
files after it, and stops when that command exits. A runner with a watch mode is named there as
it is; for one without, the stack brings a small loop that runs the files again at each save.
