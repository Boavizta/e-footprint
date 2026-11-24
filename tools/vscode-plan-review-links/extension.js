const path = require("node:path");
const os = require("node:os");
const { promisify } = require("node:util");
const { execFile } = require("node:child_process");
const fs = require("node:fs/promises");
const vscode = require("vscode");
const { testNameAt, vitestArgs } = require("./vitest-run");
const { TEST_ID, isPytestFile, pytestIdAt, pytestArgs } = require("./pytest-run");

const git = promisify(execFile);
const originalScheme = "plan-main";

function isAllowedFile(file, repoRoot) {
  if (vscode.workspace.getWorkspaceFolder(file)) return true;

  const repositoryNames = new Set(["e-footprint", "e-footprint-interface"]);
  return (vscode.workspace.workspaceFolders || []).some(({ uri }) =>
    repositoryNames.has(path.basename(uri.fsPath))
    && repositoryNames.has(path.basename(repoRoot))
    && path.dirname(uri.fsPath) === path.dirname(repoRoot)
  );
}

/** The absolute file a route's query names: `path` as given, or `repo` — a path from the
 *  repository root, sent by a served page (PyCharm's "open in browser") that cannot know its
 *  folder on disk — in the first open workspace folder that holds it. */
async function fileFromQuery(query) {
  const filePath = query.get("path");
  if (filePath) {
    if (!path.isAbsolute(filePath)) throw new Error("The link does not contain an absolute file path.");
    return filePath;
  }
  const repoPath = query.get("repo");
  if (!repoPath || path.isAbsolute(repoPath) || repoPath.split("/").includes("..")) {
    throw new Error("The link does not name a file.");
  }
  for (const { uri } of vscode.workspace.workspaceFolders || []) {
    const candidate = path.join(uri.fsPath, repoPath);
    if (await fs.stat(candidate).then((s) => s.isFile(), () => false)) return candidate;
  }
  throw new Error(`No open workspace folder holds ${repoPath}; open the repository in VS Code first.`);
}

/** The cursor position a route's `line` / `column` ask for, if any. */
function selectionAt(query) {
  const line = Number(query.get("line"));
  const column = Number(query.get("column") || 1);
  return Number.isInteger(line) && line > 0 && Number.isInteger(column) && column > 0
    ? new vscode.Range(line - 1, column - 1, line - 1, column - 1)
    : undefined;
}

/** A plain click from a served page: open the file at the line, as `vscode://file/` does for an
 *  absolute path. */
async function handleOpen(uri) {
  if (uri.path !== "/open") return false;
  const query = new URLSearchParams(uri.query);
  await vscode.window.showTextDocument(vscode.Uri.file(await fileFromQuery(query)), { selection: selectionAt(query) });
  return true;
}

async function handleDiff(uri) {
  if (uri.path !== "/diff") {
    const { version } = require("./package.json");
    throw new Error(`unknown route "${uri.path}" (extension ${version}); reload the window if it was just updated.`);
  }

  const query = new URLSearchParams(uri.query);
  const filePath = await fileFromQuery(query);

  const file = vscode.Uri.file(filePath);
  if (!(await fs.stat(filePath)).isFile()) {
    throw new Error("The linked path is not a file.");
  }

  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  const relativePath = path.relative(repoRoot, filePath);
  if (!relativePath || relativePath.startsWith(`..${path.sep}`) || path.isAbsolute(relativePath)) {
    throw new Error("The linked file is outside its Git repository.");
  }
  if (!isAllowedFile(file, repoRoot)) {
    throw new Error("Open e-footprint-interface, e-footprint, or their shared workspace in VS Code first.");
  }
  await git("git", ["-C", repoRoot, "rev-parse", "--verify", "main^{commit}"]);

  let existsOnMain = true;
  try {
    await git("git", ["-C", repoRoot, "cat-file", "-e", `main:${relativePath}`]);
  } catch {
    existsOnMain = false;
  }
  const original = file.with({
    scheme: originalScheme,
    query: JSON.stringify({ repoRoot, relativePath, existsOnMain }),
  });

  const selection = selectionAt(query);
  const options = selection ? { selection } : undefined;
  await vscode.commands.executeCommand(
    "vscode.diff",
    original,
    file,
    `${path.basename(filePath)} (main ↔ working tree)`,
    options,
  );
}

/** The repository of an open workspace folder that holds a commit, and the commit's whole hash:
 *  a link names a commit by its hash alone, so a page needs no path to it, served or not. */
async function repositoryHolding(sha) {
  for (const { uri } of vscode.workspace.workspaceFolders || []) {
    try {
      const { stdout } = await git("git", ["-C", uri.fsPath, "rev-parse", "--show-toplevel", "--verify", `${sha}^{commit}`]);
      const [repoRoot, commit] = stdout.trim().split("\n");
      return { repoRoot, commit };
    } catch {
      // Not a repository, or one that does not hold the commit: the next folder may.
    }
  }
  throw new Error(`No open workspace folder holds the commit ${sha}; open its repository in VS Code first.`);
}

/** A commit's first parent, null for a root commit, and the files it changed from it: each with
 *  its status letter. A rename reads as a file gone and a file come. */
async function changedBy(repoRoot, commit) {
  const parent = await git("git", ["-C", repoRoot, "rev-parse", "--verify", "--quiet", `${commit}^1^{commit}`])
    .then(({ stdout }) => stdout.trim(), () => null);
  // A root commit has no parent: every file it holds came with it.
  const listed = parent
    ? await git("git", ["-C", repoRoot, "diff", "--name-status", "--no-renames", "-z", parent, commit], { maxBuffer: 10 * 1024 * 1024 })
    : await git("git", ["-C", repoRoot, "diff-tree", "--root", "--no-commit-id", "-r", "--name-status", "--no-renames", "-z", commit], { maxBuffer: 10 * 1024 * 1024 });
  const fields = listed.stdout.split("\0").filter(Boolean);
  const files = [];
  for (let i = 0; i + 1 < fields.length; i += 2) files.push({ status: fields[i], relativePath: fields[i + 1] });
  return { parent, files };
}

/** The changes editor on files of a repository, each between two revisions: a side is empty where
 *  its revision is null, the file not being there. */
async function openChanges(repoRoot, title, changes) {
  const resources = changes.map(({ relativePath, was, now }) => {
    const file = vscode.Uri.file(path.join(repoRoot, relativePath));
    const at = (ref) => file.with({ scheme: originalScheme, query: JSON.stringify({ repoRoot, relativePath, ref }) });
    return [file, at(was), at(now)];
  });
  await vscode.commands.executeCommand("vscode.changes", title.length > 90 ? `${title.slice(0, 89)}…` : title, resources);
}

/** A commit, every file it changed in one editor: each file as it was at the commit's first
 *  parent beside what the commit left, a side empty where the file is not. */
async function handleCommit(uri) {
  if (uri.path !== "/commit") return false;
  const sha = new URLSearchParams(uri.query).get("sha") || "";
  if (!/^[0-9a-f]{7,40}$/.test(sha)) throw new Error("The link names a commit by seven hex digits of its hash or more.");
  const { repoRoot, commit } = await repositoryHolding(sha);
  const { parent, files } = await changedBy(repoRoot, commit);
  if (files.length === 0) throw new Error(`The commit ${sha} changed no file.`);
  const { stdout: subject } = await git("git", ["-C", repoRoot, "show", "-s", "--format=%s", commit]);
  await openChanges(repoRoot, `${commit.slice(0, 8)} · ${subject.trim()}`, files.map(({ status, relativePath }) => (
    { relativePath, was: status === "A" ? null : parent, now: status === "D" ? null : commit }
  )));
  return true;
}

/** Several commits as the one diff they come to, each file once: from before the first of them
 *  that changed it to what the last that changed it left. That is the sum of what they did and
 *  nothing more only while no other commit changed the file between them, so the route refuses
 *  a list where one did, naming it, and a list that is not in the order of the history. A file
 *  they leave as it was is not shown. */
async function handleCommits(uri) {
  if (uri.path !== "/commits") return false;
  const query = new URLSearchParams(uri.query);
  const shas = (query.get("shas") || "").split(",");
  if (!shas.every((sha) => /^[0-9a-f]{7,40}$/.test(sha))) {
    throw new Error("The link names its commits by seven hex digits of each hash or more, parted by commas.");
  }
  const { repoRoot } = await repositoryHolding(shas[0]);
  const commits = [];
  for (const sha of shas) {
    const { stdout } = await git("git", ["-C", repoRoot, "rev-parse", "--verify", `${sha}^{commit}`])
      .catch(() => { throw new Error(`The repository of ${shas[0]} holds no commit ${sha}.`); });
    commits.push(stdout.trim());
  }
  const short = (commit) => commit.slice(0, 8);
  for (let i = 1; i < commits.length; i += 1) {
    const follows = commits[i] !== commits[i - 1]
      && await git("git", ["-C", repoRoot, "merge-base", "--is-ancestor", commits[i - 1], commits[i]]).then(() => true, () => false);
    if (!follows) throw new Error(`The link's commits are not in the order of the history: ${short(commits[i])} does not come after ${short(commits[i - 1])}.`);
  }

  // Each file, with the first and the last of the commits that changed it.
  const spans = new Map();
  for (const commit of commits) {
    const { parent, files } = await changedBy(repoRoot, commit);
    for (const { status, relativePath } of files) {
      const end = { commit, parent, status };
      const span = spans.get(relativePath);
      if (span) span.last = end;
      else spans.set(relativePath, { first: end, last: end });
    }
  }
  const listed = new Set(commits);
  const blob = (ref, relativePath) => (ref === null ? null
    : git("git", ["-C", repoRoot, "rev-parse", "--verify", "--quiet", `${ref}:${relativePath}`]).then(({ stdout }) => stdout.trim(), () => null));
  const changes = [];
  for (const [relativePath, { first, last }] of [...spans].sort(([a], [b]) => (a < b ? -1 : 1))) {
    if (first.commit !== last.commit) {
      const { stdout } = await git("git", ["-C", repoRoot, "log", "--format=%H", `${first.commit}..${last.commit}`, "--", relativePath], { maxBuffer: 10 * 1024 * 1024 });
      const other = stdout.split("\n").filter(Boolean).reverse().find((commit) => !listed.has(commit));
      if (other) {
        throw new Error(`These commits do not read as one diff: ${short(other)}, which is not one of them, changed ${relativePath} between ${short(first.commit)} and ${short(last.commit)}. Render the page again, or open them one at a time.`);
      }
    }
    const was = first.status === "A" ? null : first.parent;
    const now = last.status === "D" ? null : last.commit;
    if (await blob(was, relativePath) !== await blob(now, relativePath)) changes.push({ relativePath, was, now });
  }
  if (changes.length === 0) throw new Error("These commits leave every file as it was: what one did, another undid.");
  const range = commits.length === 1 ? short(commits[0]) : `${short(commits[0])} → ${short(commits[commits.length - 1])}`;
  const named = query.get("title");
  await openChanges(repoRoot, `${named ? `${named} · ` : ""}${commits.length} commit${commits.length === 1 ? "" : "s"} · ${range}`, changes);
  return true;
}

/** One link shape for every stack, a test file and a line: the file says which runner the line
 *  belongs to. */
async function handleDebugTest(uri) {
  if (uri.path !== "/debug-test") return false;

  const query = new URLSearchParams(uri.query);
  const filePath = await fileFromQuery(query);
  const line = Number(query.get("line"));
  const lineGiven = Number.isInteger(line) && line > 0;
  if (filePath.endsWith(".py")) {
    await debugPytest(query, async (file) => (lineGiven ? pytestIdAt(await fs.readFile(file, "utf8"), line) : null));
    return true;
  }
  const file = vscode.Uri.file(filePath);
  const folder = vscode.workspace.getWorkspaceFolder(file);
  if (!folder) throw new Error("Open the repository in VS Code first.");

  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  const relativePath = path.relative(repoRoot, filePath).split(path.sep).join("/");
  const source = await fs.readFile(filePath, "utf8");
  const name = lineGiven ? testNameAt(source, line) : null;
  const args = vitestArgs(relativePath, name);

  await vscode.window.showTextDocument(file, {
    selection: name ? new vscode.Range(line - 1, 0, line - 1, 0) : undefined,
    preserveFocus: true,
  });
  // Breakpoints are the reader's own: the route sets none.
  const started = await vscode.debug.startDebugging(folder, {
    type: "node",
    request: "launch",
    name: name ? `vitest · ${name}` : `vitest · ${relativePath}`,
    program: path.join(repoRoot, "node_modules", "vitest", "vitest.mjs"),
    args,
    cwd: repoRoot,
    // A bug-fixes reproduction runs as `it.fails` until its fix: unmasked, the debug run ends on
    // the real assertion or stack instead of an expected-failure pass. No effect on other tests.
    // A debug run is for the person: the comprehension collector writes no story from it.
    env: { REPRO_UNMASK: "1", COMPREHENSION_STORIES: "off" },
    console: "integratedTerminal",
    autoAttachChildProcesses: true,
    smartStep: true,
    skipFiles: ["<node_internals>/**", "**/node_modules/**"],
  });
  if (!started) throw new Error("VS Code could not start the debugger.");
  return true;
}

/** A link that names its pytest test itself (`test=`), as a plan's Debug reproduction button
 *  does. `/debug-test` reaches the same run from a line. */
async function handleDebugPytest(uri) {
  if (uri.path !== "/debug-pytest") return false;
  const query = new URLSearchParams(uri.query);
  await debugPytest(query, () => {
    const test = query.get("test");
    if (!test || !TEST_ID.test(test)) {
      throw new Error("The link must name its pytest test id, as `test_name` or `TestClass::test_name`.");
    }
    return test;
  });
  return true;
}

/** Starts pytest under the Python debugger on the file a query names: on the test `testOf`
 *  answers for it, or on the whole file when it answers null. */
async function debugPytest(query, testOf) {
  if (!vscode.workspace.isTrusted) throw new Error("Trust the workspace before running a test.");

  const filePath = await fs.realpath(await fileFromQuery(query));
  const file = vscode.Uri.file(filePath);
  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  if (!isAllowedFile(file, repoRoot)) {
    throw new Error("Open e-footprint-interface, e-footprint, or their shared workspace in VS Code first.");
  }
  const relativePath = path.relative(repoRoot, filePath).split(path.sep).join("/");
  if (!isPytestFile(relativePath)) throw new Error("The link must name a Python test file under tests/.");
  const test = await testOf(filePath);
  const debuggerExtension = vscode.extensions.getExtension("ms-python.debugpy");
  if (!debuggerExtension) throw new Error("Install the Python Debugger extension (ms-python.debugpy) first.");
  await debuggerExtension.activate();

  // Resolve Poetry in this repository even when the parent workspace or library is open.
  const configuredPoetry = vscode.workspace.getConfiguration("python", file).get("poetryPath", "poetry");
  const localPoetry = path.join(os.homedir(), ".local", "bin", "poetry");
  const poetry = configuredPoetry === "poetry" && await fs.stat(localPoetry).then((s) => s.isFile(), () => false)
    ? localPoetry : configuredPoetry;
  const environment = await git(poetry, ["env", "info", "--executable"], { cwd: repoRoot });
  const python = environment.stdout.trim();
  if (!path.isAbsolute(python)) throw new Error("No Poetry environment found; run poetry install in the repository first.");

  await vscode.window.showTextDocument(file, { selection: selectionAt(query), preserveFocus: true });
  const started = await vscode.debug.startDebugging(vscode.workspace.getWorkspaceFolder(file), {
    type: "debugpy",
    request: "launch",
    name: `pytest · ${test || relativePath}`,
    python,
    module: "pytest",
    args: pytestArgs(relativePath, test),
    cwd: repoRoot,
    envFile: path.join(repoRoot, ".env"),
    // A debug run is for the person: the comprehension collector writes no story from it, so the
    // pages keep those of the last whole run.
    env: { RAISE_EXCEPTIONS: "1", PYTEST_ADDOPTS: "", COMPREHENSION_STORIES: "off" },
    console: "integratedTerminal",
    redirectOutput: true,
    justMyCode: false,
    stopOnEntry: false,
  });
  if (!started) throw new Error("VS Code could not start the Python debugger.");
}

function activate(context) {
  context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(originalScheme, {
    async provideTextDocumentContent(uri) {
      // A side of a commit's diff names its revision (`ref`), null where the file is not; the
      // `diff` route's side is the file on main.
      const { repoRoot, relativePath, existsOnMain, ref } = JSON.parse(uri.query);
      const revision = ref === undefined ? (existsOnMain ? "main" : null) : ref;
      if (revision === null) return "";
      const { stdout } = await git("git", ["-C", repoRoot, "show", `${revision}:${relativePath}`], {
        maxBuffer: 10 * 1024 * 1024,
      });
      return stdout;
    },
  }));
  context.subscriptions.push(vscode.window.registerUriHandler({
    async handleUri(uri) {
      try {
        if (await handleOpen(uri)) return;
        if (await handleDebugTest(uri)) return;
        if (await handleDebugPytest(uri)) return;
        if (await handleCommit(uri)) return;
        if (await handleCommits(uri)) return;
        await handleDiff(uri);
      } catch (error) {
        vscode.window.showErrorMessage(`Plan review links: ${error.message}`);
      }
    },
  }));
}

module.exports = { activate };
