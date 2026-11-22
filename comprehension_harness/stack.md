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
- **A site is a file and a line.** One `narrate`, `event` or `planned` call per line.
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
story; a file with no story writes no file. Every test is recorded, in a declared narrative or
not: the tests reaching a site are counted over all of them.

| Field | Holds |
|---|---|
| `file`, `test` | The test file and the test's title |
| `narrative` | `{ title, kind }` of the narrative the test is declared in, `kind` being `product` or `mechanism`; `null` outside one |
| `canonical` | The test marked itself the narrative's reference case |
| `order` | A number growing with the run: variants are told in that order |
| `state`, `durationMs` | Shown on the page, never judged |
| `hits` | The calls crossed, in order |
| `capped` | Optional. `[{ file, line, kept, omitted }]`: a site keeps its first 50 hits of a test and counts the rest |

A hit:

| Field | Holds |
|---|---|
| `kind` | `step`, `event` or `planned` |
| `sentence` | As passed to the call |
| `watch` | The watch's value as plain JSON, or `null`. `{ "error": "…" }` when computing it threw, which never fails the test |
| `site` | The frame of the call: `{ file, line, column, fn }`, `fn` `null` for a function with no name |
| `stack` | The frames above it, nearest first, of the repository's own files only |
| `atMs` | Milliseconds since the test began |

A collector may write fields of its own beside these. The tools read one of them when it is
there: `mappedFn`, a source-mapped name, where `fn` is `null`.

The three calls are inert in production: none does anything unless a collector is installed,
which only a test run does. The watch is passed as a function the collector calls, so nothing
is computed for it outside a test.

## 2. The source index: what the source says without running

What the tools ask (`SourceReader`). The identity of a step (`<file>#<function>#<ordinal>`), and
finding again by its sentence a site whose line moved, are derived by the tools from the first
row.

| Asked | Answered with | How sure |
|---|---|---|
| The sites of a file | Each call: `kind`, `line`, `column`, `fn`, its sentence when it is a literal; for a `planned` call its tag, whether it changes, removes or adds, and a shell's signature | Exact |
| A narrative's declaration | In its test file: the line, the first paragraph of the comment above it, the title of its first test. Also: which test files declare one | Exact |
| Where a name of a sentence is declared, seen from a site | In order: an import of the file, a local of the functions around the call (nearest first), a top-level declaration of the file, one unique across the source. Otherwise the reason, for `--check` | Identities with a type checker, names without |
| The same with no site | For a name `plan.md`, a test title or a page of rules gives: in the files named beside it, else unique across the source, else nearest to the piece's places | Same |
| Where a function uses a symbol | The first line of a function (by `file` and `fn`) referring to the symbol declared at a place: "Open call" | Same |
| The function around a site | The nearest named function, its first and last line, who refers to it and what it calls, each marked as holding a `narrate` or not (`map step`, `map around`) | Candidates in both |

The stack's reader refuses, with the file and the line: a `planned` call whose tag or sentence is
not a literal, a tag that is not `<feature>#<slug>`, a shell that throws anything but
`planned: <tag>`.

The JSON form, for a stack that does not run in Node. The command prints it; it is asked for at
each render. [`json-source.ts`](json-source.ts) answers the interface from it, and
[`tests/fixtures/shop/`](tests/fixtures/shop/README.md) is an index written by hand for three
Python files: the example a stack's own index conforms to, checked line and column against its
source by the test.

```json
{
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

- `files` holds every file of the source folders and every test file that declares a narrative.
- A `planned` site adds `"planned": { "feature", "slug", "change", "signature" }`, `change` being
  `changed`, `removed` or `added`.
- `functions`: every named function, with the line its name is on. A site or a local belongs to
  the functions whose lines hold it.
- `declarations` are the top-level ones; `locals` every other one (a parameter, a variable, an
  inner function, a method, a field).
- `imports` and `uses` give the declaration a name refers to, as far as the stack can tell; a
  reference it cannot place is left out, and so is what stands inside a `narrate`, `event` or
  `planned` call. Callers and callees are read from `uses`.
- The project's configuration names the two commands in place of a module:
  `"stack": { "sourceIndex": ["python3", "…"], "titles": ["python3", "…"] }`.

## 3. Test titles: planned and written

Asked for one file's text, not for the checkout: the lot check reads a test file on both sides of
a commit. The answer:

| Field | Holds |
|---|---|
| `tests` | Every test in file order: `{ title, line, column, planned }`. `planned` is a test declared with no body: `it.todo` in vitest, a function under a marker that carries the title in pytest |
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
| `journey.json` | `{ name, slug, who, wants, now, file, todos }`, `todos` being the planned cases `{ feature, screen, title, line }` |
| `cases/<line, 4 digits>-<case-slug>.json` | One case: `{ journey, title, slug, line, status, screens, after }`. The first case of the file is the reference run |
| `captures/<case-slug>/<nn>-<screen-id>.html` | The screen as a complete HTML document that opens with no server, `data-journey-screen="<journey-slug>#<id>"` on its root, its stylesheet linked under `css/` |

A screen of a case: `{ id, why, url, capture, css, sha, bytes, counts, returnsTo,
identicalToFirstVisit, movedSinceFirstVisit, controls, before, planned }`. `before` is what led
to it, a list of causes: `{ kind, url, type, key, control, on, elapsed, events, steps,
navigations, server }`, `kind` being `open`, `action` or `time`. `events` and `steps` are the
`event` and `narrate` calls crossed between two screens, each with its sentence and its site
`{ file, line, fn }`, wherever that code ran: in the browser for an app that runs there, in the
server process for a page the server renders. `server` lists the server steps a stub answered and
is empty when the journey runs against the real server. The types are `JourneyCase`,
`ScreenRecord` and `Cause` of `stack.ts`.

## Beside the four: a command that keeps the narrative tests running

The local app (`dev.ts`) starts the configuration's `commands.watch` with the narrative test
files after it, and stops when that command exits. A runner with a watch mode is named there as
it is; for one without, the stack brings a small loop that runs the files again at each save.
