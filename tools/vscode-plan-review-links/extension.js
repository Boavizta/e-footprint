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
      const { repoRoot, relativePath, existsOnMain } = JSON.parse(uri.query);
      if (!existsOnMain) return "";
      const { stdout } = await git("git", ["-C", repoRoot, "show", `main:${relativePath}`], {
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
        await handleDiff(uri);
      } catch (error) {
        vscode.window.showErrorMessage(`Plan review links: ${error.message}`);
      }
    },
  }));
}

module.exports = { activate };
