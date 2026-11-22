// The pytest routes' decisions that need no VS Code: which files they run, which test a linked
// line names and how pytest runs it. Kept apart from `extension.js`, as `vitest-run.js` is, so
// that a repository's own tests can hold them.

/** The selector after a file's `::` that a link may name: a test function, in a test class or
 *  not, with its parameter case or not. Nothing that pytest would read as an option. */
const TEST_ID = /^(?:Test\w*::)?test_\w+(?:\[[^\r\n]+\])?$/;

const TEST_DEF = /^(\s*)(?:async\s+)?def\s+(test_\w+)\s*\(/;
const CLASS = /^(\s*)class\s+(\w+)/;

/** A file a pytest route runs, as a path from the repository root. */
function isPytestFile(relativePath) {
  return relativePath.startsWith("tests/") && relativePath.endsWith(".py");
}

const indentOf = (text) => text.length - text.trimStart().length;

/** The first line above `from` that is less indented than `limit` and that `wanted` accepts,
 *  each less indented line met on the way lowering the limit: the block that holds a line. */
function holder(lines, from, limit, wanted) {
  for (let i = from - 1; i >= 0 && limit > 0; i -= 1) {
    if (lines[i].trim() === "" || indentOf(lines[i]) >= limit) continue;
    if (wanted(lines[i])) return i;
    limit = indentOf(lines[i]);
  }
  return -1;
}

/** The test a `line` of a pytest file names, as the selector after the file's `::`: the
 *  `def test_…` opening at `line` or one of the two lines after it, else the one whose body
 *  holds the line, with `Test…::` in front when a test class holds it. Null when the line is in
 *  no test, and the route then runs the whole file. */
function pytestIdAt(source, line) {
  const lines = source.split(/\r?\n/);
  let at = -1;
  for (let i = line - 1; i < Math.min(lines.length, line + 2); i += 1) {
    if (i >= 0 && TEST_DEF.test(lines[i])) { at = i; break; }
  }
  if (at < 0 && line >= 1 && line <= lines.length && lines[line - 1].trim() !== "") {
    at = holder(lines, line - 1, indentOf(lines[line - 1]), (text) => TEST_DEF.test(text));
  }
  if (at < 0) return null;
  const [, indent, name] = lines[at].match(TEST_DEF);
  // The block right around the test: a class pytest collects, or the test is not in one.
  const around = holder(lines, at, indent.length, () => true);
  const owner = around < 0 ? null : lines[around].match(CLASS);
  return owner && owner[2].startsWith("Test") ? `${owner[2]}::${name}` : name;
}

/** The pytest arguments that run `test` (or the whole file) plainly: an expected failure runs,
 *  no coverage, no inherited option, output shown, stopping at the first failure. A browser test
 *  runs headed against the local server. */
function pytestArgs(relativePath, test) {
  const args = ["--runxfail", "--no-cov", "-o", "addopts=", "-s", "-vv", "--tb=long", "-x", test ? `${relativePath}::${test}` : relativePath];
  if (relativePath.startsWith("tests/e2e/")) args.push("--base-url", "http://localhost:8000", "--headed");
  return args;
}

module.exports = { TEST_ID, isPytestFile, pytestIdAt, pytestArgs };
