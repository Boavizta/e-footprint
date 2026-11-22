// The `/debug-test` route's decisions that need no VS Code: which vitest case a linked line
// names and how vitest runs it. Kept apart from `extension.js` so that a repository's own tests
// and its plan-link converter (which refuses a Debug reproduction button this route could not
// run) share one answer.

/** Playwright's specs: not vitest files, and no route of this extension debugs them. */
const PLAYWRIGHT_DIR = "tests/e2e/";

/** `it(` / `test(` / `describe(`, modifiers allowed, then the case name (group 2). */
const CASE_CALL = /^\s*(?:it|test|describe)(?:\.(?:only|skip|fails|each|skipIf|runIf)(?:\([^)]*\))?)*\s*\(\s*(['"`])((?:\\.|(?!\1).)*)\1/;
/** A bug-fixes reproduction, `reproduction('<batch> Task N', '<name>', fn)`, whose case name is
 *  its second argument (group 3). */
const REPRODUCTION_CALL = /^\s*reproduction\s*\(\s*(['"`])(?:\\.|(?!\1).)*\1\s*,\s*(['"`])((?:\\.|(?!\2).)*)\2/;

/** The case a test-file `line` names, as vitest's `-t` wants it: the call opening at `line` or
 *  one of the two lines after it, its arguments possibly wrapped onto the following lines.
 *  Null when no case opens there, and the route then runs the whole file. */
function testNameAt(source, line) {
  const lines = source.split(/\r?\n/);
  for (let i = line - 1; i < Math.min(lines.length, line + 2); i += 1) {
    if (i < 0) continue;
    const call = lines.slice(i, i + 4).join("\n");
    const reproduction = call.match(REPRODUCTION_CALL);
    const name = reproduction ? reproduction[3] : call.match(CASE_CALL)?.[2];
    if (name !== undefined) return name.replace(/\\(['"`])/g, "$1");
  }
  return null;
}

/** The vitest CLI arguments that run `name` (or the whole file) in the suite owning
 *  `relativePath` — the db and migrations suites have their own configs. Throws for a
 *  Playwright spec, which vitest cannot run. */
function vitestArgs(relativePath, name) {
  if (relativePath.startsWith(PLAYWRIGHT_DIR)) {
    throw new Error(
      `${relativePath} is a Playwright spec, which no debug route runs; run it in a terminal: `
      + `REPRO_UNMASK=1 npx playwright test ${relativePath}`,
    );
  }
  const config = relativePath.startsWith("tests/db/") ? ["--config", "vitest.db.config.ts"]
    : relativePath.startsWith("tests/migrations/") ? ["--config", "vitest.migrations.config.ts"]
      : [];
  const args = ["run", ...config, relativePath];
  if (name) args.push("-t", name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return args;
}

module.exports = { PLAYWRIGHT_DIR, testNameAt, vitestArgs };
