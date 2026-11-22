/** Where a source link points on the machine that opened the page, from its relative target
 *  (`data-review-source-href`, e.g. `../../src/x.ts#L42:1`; a link's named alternates in
 *  `data-review-alt-hrefs` carry the same shape and resolve the same way):
 *  - a page opened from the file system knows the absolute path (`{ path }`), which VS Code
 *    opens by itself;
 *  - a served page (PyCharm's "open in browser", any local server) only knows the path from the
 *    repository root (`{ repo }`), which the plan-review-links extension places in the open
 *    workspace.
 *  `repoRootUrl` is the repository root as the page sees it: the folder above this script's own
 *  `specs/`. Null for a target outside the repository or one that is not a source line, so the
 *  committed href stands. */
function reviewSourceLocation(target, pageUrl, repoRootUrl) {
  const file = new URL(target, pageUrl);
  const root = new URL(repoRootUrl).href;
  const bare = file.href.split("#")[0];
  if (file.search || !bare.startsWith(root)) return null;
  const at = /^#L(\d+)(?::(\d+))?$/.exec(file.hash);
  if (file.hash && !at) return null;
  const line = at ? { line: at[1], column: at[2] || "1" } : {};
  if (file.protocol === "file:") return { path: decodeURIComponent(file.pathname), ...line };
  return { repo: decodeURIComponent(bare.slice(root.length)), ...line };
}

/** The location a committed `vscode://file/` href names, for a target the resolver above cannot
 *  place: a file of another checkout, such as a sibling repository a plan links into. Only the
 *  machine that converted the link knows that path, so it is taken as written. Null for any
 *  other href. */
function reviewCommittedLocation(href) {
  if (!href || !href.startsWith("vscode://file/")) return null;
  const file = decodeURIComponent(new URL(href).pathname.slice(1));
  const at = /:(\d+)(?::(\d+))?$/.exec(file);
  return at ? { path: file.slice(0, -at[0].length), line: at[1], column: at[2] || "1" } : { path: file };
}

/** The query every extension route reads: `path` or `repo`, then `line` and `column`. */
function reviewSourceQuery(location) {
  const query = new URLSearchParams(location.path ? { path: location.path } : { repo: location.repo });
  if (location.line) {
    query.set("line", location.line);
    query.set("column", location.column);
  }
  return query;
}

/** What a click opens: VS Code's own file route for an absolute path, the extension's `open`
 *  route for a repository path. */
function reviewSourceHref(location) {
  if (!location.path) return `vscode://local.plan-review-links/open?${reviewSourceQuery(location)}`;
  const at = location.line ? `:${location.line}:${location.column}` : "";
  return `vscode://file/${location.path.split("/").map(encodeURIComponent).join("/")}${at}`;
}

/** Whether the extension's `debug-test` route can run a location: a pytest file (`test_*.py`
 *  under `tests/`), or a vitest file, i.e. a `*.test.*` / `*.spec.*` outside Playwright's
 *  `tests/e2e/`. A Playwright spec gets no debug link: the route would start vitest on it
 *  (`tools/vscode-plan-review-links/vitest-run.js`). */
function reviewDebugs(location) {
  const file = location.path || location.repo;
  if (/(?:^|\/)tests\/(?:.*\/)?test_[^/]*\.py$/.test(file)) return true;
  return /\.(?:test|spec)\.[cm]?[jt]sx?$/.test(file) && !/(?:^|\/)tests\/e2e\//.test(file);
}

/** The extension route that runs the case at a test location under the VS Code debugger,
 *  unmasked, stopping at the breakpoints the reader has set. */
function reviewDebugHref(location) {
  return `vscode://local.plan-review-links/debug-test?${reviewSourceQuery(location)}`;
}

// The unit test evaluates this file with no DOM, for the resolver above alone.
if (typeof document !== "undefined") (() => {
  const selector = "a[data-review-source-href]";
  const script = document.currentScript || document.querySelector('script[src$="review-links.js"]');
  const repoRoot = new URL("../", script.src).href;

  /** A committed `vscode://` href names the absolute path of whichever checkout last converted
   *  the page's links; every source link of this repository is re-pointed at this machine's
   *  file, and a link into another checkout keeps its committed path. */
  const locations = new Map();
  for (const link of document.querySelectorAll(selector)) {
    const location = reviewSourceLocation(link.dataset.reviewSourceHref, document.baseURI, repoRoot)
      || reviewCommittedLocation(link.getAttribute("href"));
    if (!location) continue;
    locations.set(link, location);
    // A task's Debug reproduction button runs its test; every other source link opens its file.
    link.href = link.hasAttribute("data-debug-reproduction") && reviewDebugs(location)
      ? reviewDebugHref(location)
      : reviewSourceHref(location);
  }
  const menu = document.createElement("div");
  menu.id = "review-link-menu";
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", "Open source file");
  menu.hidden = true;

  const openFile = document.createElement("a");
  openFile.textContent = "Open file";
  openFile.setAttribute("role", "menuitem");
  const openDiff = document.createElement("a");
  openDiff.textContent = "Open diff vs main";
  openDiff.setAttribute("role", "menuitem");
  const debugTest = document.createElement("a");
  debugTest.textContent = "Debug this test";
  debugTest.setAttribute("role", "menuitem");
  menu.append(openFile, openDiff, debugTest);
  document.body.append(menu);

  let sourceLink = null;
  /** The named alternates of the link the menu is open on (`data-review-alt-hrefs`, JSON
   *  `[{ label, href }]`): each a target resolved like the primary, listed under "Open file". */
  const alternates = [];

  function closeMenu() {
    menu.hidden = true;
    sourceLink = null;
    for (const item of alternates) item.remove();
    alternates.length = 0;
  }

  function alternatesOf(link) {
    const raw = link.dataset.reviewAltHrefs;
    if (!raw) return [];
    return JSON.parse(raw)
      .map((alt) => ({ label: alt.label, location: reviewSourceLocation(alt.href, document.baseURI, repoRoot) }))
      .filter((alt) => alt.location);
  }

  /** The menu's items in order, the hidden ones skipped — for the arrow keys. */
  function menuItems() {
    return [...menu.querySelectorAll("a")].filter((item) => !item.hidden);
  }

  function diffUrl(link) {
    return `vscode://local.plan-review-links/diff?${reviewSourceQuery(locations.get(link))}`;
  }

  /** A test file's link also offers to run that case under the VS Code debugger, stopping at
   *  whatever breakpoints are set; the extension reads the test at the linked line (an `it(` or
   *  a `reproduction(`, a `def test_…`) and starts its runner on that one name. */
  function debugUrl(link) {
    const location = locations.get(link);
    return reviewDebugs(location) ? reviewDebugHref(location) : null;
  }

  /** A narrative (`[data-narrative]`) that names its test (`[data-narrative-test]`)
   *  gets one "debug this narrative" link that runs that test under the debugger; the
   *  reader sets breakpoints at the watch points they want first. */
  for (const narrative of document.querySelectorAll("[data-narrative]")) {
    const test = narrative.querySelector(selector.replace("a[", "a[data-narrative-test]["));
    if (!locations.has(test) || !reviewDebugs(locations.get(test))) continue;
    const run = document.createElement("a");
    run.className = "debug-narrative";
    run.href = reviewDebugHref(locations.get(test));
    run.textContent = "▶ debug this narrative";
    run.title = "Run the narrative's test under the VS Code debugger, stopping at your breakpoints";
    (narrative.querySelector("header") || narrative).append(run);
  }

  document.addEventListener("contextmenu", (event) => {
    const link = event.target.closest(selector);
    if (!link || !locations.has(link)) {
      closeMenu();
      return;
    }

    event.preventDefault();
    closeMenu();
    sourceLink = link;
    openFile.href = link.href;
    for (const alt of alternatesOf(link)) {
      const item = document.createElement("a");
      item.textContent = alt.label;
      item.setAttribute("role", "menuitem");
      item.href = reviewSourceHref(alt.location);
      menu.insertBefore(item, openDiff);
      alternates.push(item);
    }
    openDiff.href = diffUrl(link);
    const debug = debugUrl(link);
    debugTest.hidden = !debug;
    if (debug) debugTest.href = debug;
    menu.hidden = false;

    const bounds = link.getBoundingClientRect();
    const x = event.clientX || bounds.left;
    const y = event.clientY || bounds.bottom;
    menu.style.left = `${Math.max(8, Math.min(x, window.innerWidth - menu.offsetWidth - 8))}px`;
    menu.style.top = `${Math.max(8, Math.min(y, window.innerHeight - menu.offsetHeight - 8))}px`;
    openDiff.focus();
  });

  document.addEventListener("pointerdown", (event) => {
    if (!menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (menu.hidden) return;
    if (event.key === "Escape") {
      const link = sourceLink;
      closeMenu();
      link?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const items = menuItems();
      const index = items.indexOf(document.activeElement);
      const next = event.key === "ArrowDown" ? (index + 1) % items.length : (index - 1 + items.length) % items.length;
      items[next].focus();
    }
  });
  window.addEventListener("scroll", closeMenu, true);
  window.addEventListener("resize", closeMenu);
  menu.addEventListener("click", closeMenu);
})();
