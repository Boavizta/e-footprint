# Plan source links

Apply this convention whenever creating or editing `plan.html`, including `PLAN-UPDATE` proposals, accepted amendments, implementation decisions, and later corrections. Preserve it when editing an existing plan; do not replace its reviewed layout merely to add the menu.

## Reviewer behavior

- A normal click on an existing source-file link opens that file in VS Code. Right-clicking the same link offers **Open file** and **Open diff vs main**. The diff compares the working copy with the local `main` of that file's own repository, including uncommitted edits.
- Give existing source references a static `vscode://file//absolute/path` `href` and a `data-review-source-href` containing the plan-relative path. Add `:line:column` to the VS Code URL and `#Lline:column` to the relative path when pointing to a named function or branch. This relative attribute lets another checkout regenerate its own absolute URL.
- Keep `#` links for plan sections and proposed files that do not exist. Do not turn illustrative pseudocode, UI copy or protocol values into source links.

```html
<a href="vscode://file//absolute/checkout/repo/module/file.py:123:1"
   data-review-source-href="../../../module/file.py#L123:1"><code>function_name()</code></a>
```

## Wiring and refresh

The plan includes `<script src="../../review-links.js" defer></script>` just before `</body>` and the `#review-link-menu` CSS from [the starter](../assets/plan.html). The shared script lives at `specs/review-links.js` in both repositories. It only adds the right-click menu to marked VS Code file links; normal link navigation stays native. The local VS Code extension is in `e-footprint-interface/tools/vscode-plan-review-links/`; install it once using its README. Keep the short click/right-click hint near the changed-file tree. For an older plan, add this wiring without changing unrelated layout or anchors.

After adding or changing file links, run the converter from the driving repository. It converts existing relative links, marks them with `data-review-source-href`, and refreshes absolute URLs already carrying that attribute for the current checkout:

```bash
python3 .agents/skills/feature-implement/scripts/vscode_review_links.py specs/features/<feature>/plan.html --in-place
```

Inspect the changed links, verify each intended file and line exists, and check the page's normal-click and right-click behavior. Keep the marked, static URLs in the plan so local review does not depend on runtime link rewriting. A different checkout can run the same converter to localize the URLs. Do not commit a separate temporary review copy.
