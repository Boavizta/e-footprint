# Plan source links

Apply this convention whenever creating or editing `plan.html`, including `PLAN-UPDATE` proposals, accepted amendments, implementation decisions, and later corrections. Preserve it when editing an existing plan; do not replace its reviewed layout merely to add the menu.

## Reviewer behavior

- A normal click on an existing source-file link opens that file in VS Code. Right-clicking the same link offers **Open file** and **Open diff vs main**. The diff compares the working copy with the local `main` of that file's own repository, including uncommitted edits.
- Give existing source references a static `vscode://file//absolute/path` `href` and a `data-review-source-href` containing the plan-relative path. Add `:line:column` to the VS Code URL and `#Lline:column` to the relative path when pointing to a named function or branch. This relative attribute lets another checkout regenerate its own absolute URL.
- HTML documentation under `specs/`, `docs/`, or `docs_sources/` opens in a new browser tab: use a plan-relative `href`, `target="_blank" rel="noopener"`, and no `data-review-source-href`. Link to an existing section id where useful; `#L123` is a source-line reference, not a browser anchor. Production HTML templates remain VS Code source links.
- Keep `#` links for plan sections and proposed files that do not exist. Do not turn illustrative pseudocode, UI copy or protocol values into source links.

```html
<a href="vscode://file//absolute/checkout/repo/module/file.py:123:1"
   data-review-source-href="../../../module/file.py#L123:1"><code>function_name()</code></a>
```

## Wiring and refresh

The plan includes `<script src="../../review-links.js" defer></script>` just before `</body>` and the `#review-link-menu` CSS from [the starter](../assets/plan.html). The shared script lives at `specs/review-links.js` in both repositories. It only adds the right-click menu to marked VS Code file links; normal link navigation stays native. The local VS Code extension is in `e-footprint-interface/tools/vscode-plan-review-links/`; install it once using its README. Keep the short click/right-click hint near the changed-file tree. For an older plan, add this wiring without changing unrelated layout or anchors.

After adding or changing file links, run the converter from the driving repository. It keeps documentation HTML as browser links (and repairs previously converted documentation links). For source files, it converts existing relative links, marks them with `data-review-source-href`, and refreshes absolute URLs already carrying that attribute for the current checkout:

```bash
python3 .agents/skills/feature-implement/scripts/vscode_review_links.py specs/features/<feature>/plan.html --in-place
```

Inspect the changed links, verify each intended file and line exists, and check the page's normal-click and right-click behavior. Keep the marked, static URLs in the plan so local review does not depend on runtime link rewriting. A different checkout can run the same converter to localize the URLs. Do not commit a separate temporary review copy.

## One-click pytest reproductions

For each task or walkthrough step with an existing, supported pytest reproduction, place a **Debug reproduction** button immediately after its heading, before status chips, file metadata and descriptive prose. Use a native link styled as a button, with the starter's `data-task-actions` and `data-debug-reproduction` attributes and a task-specific accessible label. Keep the breakpoint advice and copyable unmasked command in the detailed debug recipe; an inline debug link there may remain.

Use the local extension's `/debug-pytest` route (version 0.0.8 or later). The URL carries an absolute test-file `path`, the selector after the file's `::` in `test`, and an optional suggested `line`; encode query values and HTML-escape ampersands. Preserve a plan-relative `data-review-pytest` value so the converter above refreshes this checkout's path without changing the debug route. Do not add `data-review-source-href` to debug links.

```html
<p data-task-actions>
  <a data-debug-reproduction aria-label="Debug reproduction for Task N"
     href="vscode://local.plan-review-links/debug-pytest?path=%2Fabsolute%2Frepo%2Ftests%2Ftest_example.py&amp;test=TestExample%3A%3Atest_example&amp;line=42"
     data-review-pytest="../../../tests/test_example.py::TestExample::test_example">Debug reproduction</a>
</p>
```

Replace the example's file, selector, suggested line and accessible label with the actual reproduction; make the relative path resolve from this plan, including across repositories. For an older plan, merge the starter's button styles without changing its reviewed layout. Do not invent a test or add an inactive button where no reproduction exists. For another runner, offer a button only when the extension has a working route that launches and unmasks that runner's reproduction. Otherwise keep the copyable command and state that one-click debugging is unavailable; never point a Jest test at the pytest route.

The launcher uses the repository's Poetry environment and `--runxfail`, disables coverage and inherited parallel options for this run, honors existing breakpoints without adding any, and mirrors output to Terminal and Debug Console. With no breakpoints, reviewers can read the unmasked failure after the run. Their exception-breakpoint settings still apply. Explain near the links that E2E tests need Django at `http://localhost:8000`; Python debugging covers the pytest process, not that separate server or browser JavaScript. See the extension README in the interface repository for installation and the URL format.
