# Plan Review Links

A local VS Code extension behind the right-click menu of a plan or narrative page (`specs/review-links.js`), and behind plain clicks on a served one. It has six routes:

| Route | What it does |
|---|---|
| `open` | Opens a file at a line. A plain click from a page served over HTTP goes through it |
| `diff` | **Open diff vs main**: a linked source file's working copy beside its `main` revision. A file absent from `main` is compared against empty content |
| `commit` | Opens a commit, every file it changed in one editor: a page's link on a commit's hash |
| `commits` | Opens several commits as the one diff they come to, each file once: a page's link on the commits of a piece |
| `debug-test` | **Debug this test**, on a link into a test file: starts the one test at the linked line under the debugger of its runner, vitest for a JavaScript or TypeScript file, pytest for a Python one |
| `debug-pytest` | **Debug reproduction**, on a link that names its pytest test itself: starts that test under the Python debugger |

Plain clicks on a page opened as a file need nothing installed: VS Code handles `vscode://file/` itself. A page **served** over HTTP (an IDE's "open in browser", any local server) cannot know its folder on disk, so `specs/review-links.js` sends every route the path from the repository root (`repo=` in place of `path=`), and the extension finds the file in the first open workspace folder that holds it.

No route sets a breakpoint: set your own before clicking. The browser or VS Code may ask once to allow opening these links.

## Install (once per machine)

```bash
cd tools/vscode-plan-review-links
npx --yes @vscode/vsce package --allow-missing-repository
code --install-extension plan-review-links-0.0.14.vsix
```

If `code` is not on your PATH, use `"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"`. `code --list-extensions | grep plan` confirms it: `local.plan-review-links`.

Or run **Extensions: Install from VSIX…** in VS Code and pick the file. Reload VS Code after replacing an installed version: a window keeps the version it started with, and an old one answers a route it does not know with its version number. The `.vsix` is gitignored.

Open the repository in VS Code before using the menu: the extension refuses a file outside the open workspace. The one exception is the pair of sibling checkouts `e-footprint` and `e-footprint-interface`: a file of one opens while only the other is open.

## What `diff` compares

The local `main` commit against the working tree, uncommitted edits included. It never fetches and never changes the checkout.

## What `commit` opens

`vscode://local.plan-review-links/commit?sha=<hash>`, seven hex digits of the hash or more. The link carries no path: the route looks for the commit in each open workspace folder, so the same link works from a page opened as a file and from a served one. It opens VS Code's multi-file diff editor (`vscode.changes`) on every file the commit changed, each as the commit's first parent held it beside what the commit left. A file the commit added or deleted has an empty side, and a rename reads as a file gone and a file come. It never fetches and never changes the checkout.

## What `commits` opens

`vscode://local.plan-review-links/commits?shas=<hash>,<hash>,…`, oldest first, seven hex digits of each hash or more, and optionally `title=`, words that open the editor's title. The repository is the open workspace folder that holds the first commit. The route opens the same editor as `commit`, each file once: as it was before the first of the commits that changed it, beside what the last of them that changed it left. A file the commits leave as it was is not shown.

That diff is the sum of what the commits did, and nothing more, only while no other commit changed one of those files between two of them. The route checks it and opens nothing otherwise, naming the commit and the file; it also refuses a list that is not in the order of the history. A commit that changed another file between them is no obstacle. A page that links several commits this way groups them so that the check holds (`commitBlocks`, `comprehension_harness/plan.ts`): a refusal means the page is older than the branch.

## Debugging a vitest case

On a JavaScript or TypeScript file, `debug-test` reads the `it(` / `test(` / `describe(` / `reproduction(` call at the linked line, or one of the two lines after it, and runs `vitest run <file> -t <name>`; with no case there it runs the whole file. A file under `tests/db/` or `tests/migrations/` runs with `vitest.db.config.ts` or `vitest.migrations.config.ts`. The run sets `REPRO_UNMASK=1`, so a bug-batch reproduction still masked as an expected failure runs plainly and ends on its real assertion or stack. A narrative's **debug this narrative** link is the same route on the narrative's test.

Playwright specs (`tests/e2e/`) have no route: the Node debugger would attach to the Playwright runner, not to the browser the app code runs in. The page offers no debug link on them, and the route refuses one with the terminal command instead.

The case-finding and the arguments are in `vitest-run.js`, which needs no VS Code: a repository's plan-link converter can import it to refuse a button this route could not run.

## Debugging a pytest test

1. Install Microsoft's **Python Debugger** (`ms-python.debugpy`) extension and run `poetry install --with dev` in the repository. The workspace must be trusted.
2. Open a file from a source link and set the breakpoints you want.
3. Click **Debug reproduction**. Without breakpoints the test runs through and prints its failure in the **Terminal** and the **Debug Console**. With breakpoints, inspect **Variables**, **Watch** and the **Call Stack**.

If pausing on raised exceptions is enabled, VS Code may pause with no source breakpoint; disable that option or continue to see the final traceback.

On a Python file, `debug-test` reads the `def test_…` that opens at the linked line or one of the two lines after it, else the test whose body holds the line, and puts its `Test…` class in front; in no test, it runs the whole file. `debug-pytest` takes the selector from the link. Both then do the same.

Each link runs only its pytest function (its parameter cases included) and stops at the first failure. It uses the repository's Poetry interpreter, loads its `.env`, sets `RAISE_EXCEPTIONS=1` and `COMPREHENSION_STORIES=off` (a debug run writes no story: the comprehension pages keep those of the last whole run), and runs with `--runxfail --no-cov -o addopts= -s -vv --tb=long -x`. `PYTEST_ADDOPTS` is cleared for the run, so inherited coverage or parallel execution does not interfere with breakpoints. The Python `poetryPath` setting of VS Code is respected; otherwise the route uses `~/.local/bin/poetry` when present, or `poetry` on the PATH. `justMyCode: false` lets the debugger step into an editable companion library.

A test under `tests/e2e/` gets `--base-url http://localhost:8000 --headed`: start the server there first. Python breakpoints apply to the pytest process; the server process and the browser's JavaScript each need their own debugger attached.

A `debug-pytest` link is a static URL with an absolute test-file `path`, the pytest `test` selector that follows the file's `::`, and optionally a `line` to show:

```text
vscode://local.plan-review-links/debug-pytest?path=%2Fabsolute%2Frepo%2Ftests%2Ftest_example.py&test=TestExample%3A%3Atest_example&line=42
```

In HTML, `&` is written `&amp;`. For both routes the file must be a `.py` under `tests/`.

The test-finding and the arguments are in `pytest-run.js`, which needs no VS Code.

## One copy

One extension id, `local.plan-review-links`, serves every repository on a machine, so the copies must never fork: the folder is one of the shared files of `scripts/sync_agent_tooling.py`. A change is made in one repository, the version in `package.json` is raised, and the sync carries it to the others before anything else changes here.

Each repository tests the routes against its own files: a test of `vitest-run.js` and `pytest-run.js` where vitest runs, a `node --test` file of the `diff` and pytest routes where pytest does. Those tests are not shared.
