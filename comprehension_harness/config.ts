/**
 * config.ts — the project the tools run in: where it is, and what `comprehension.config.json` at its root says.
 *
 * The tools are the same in every project. What differs is data, and it is all in that one file:
 *
 *  - `name`: the project's name, on its pages' titles;
 *  - `stack`: what answers what the source says (`stack.ts`): a module, as a path from the root, or for a
 *    stack that does not run in Node the two commands that print it as JSON (`sourceIndex`, `titles`) and,
 *    optionally, the one that takes an archived feature's marks off a file (`strip`), beside which such a
 *    stack keeps keys of its own (the Python stack's `calls`);
 *  - `cache`: where what a run writes and a render reads is kept (the stories, the map's snapshots);
 *  - `docs`: the folder of the project's documents. The feature folders (`features/`), the generated pages and
 *    the journeys' captures are under it, by the method's own layout; the local app serves it;
 *  - `hub`: the page every generated page links back to, or null;
 *  - `actor`: the word a product narrative's causes open with ("The user taps …" for `user`); any other cause is the world's;
 *  - `source` and `tests`: what a file is, by its path (`layout.ts`);
 *  - `pagesNamingCode`: the pages whose entries mark the steps they name: debts, rules, conventions;
 *  - `commands`: how a tool, the narrative tests and the journeys are run here. `tests` also runs the test files
 *    that hold a plan's reproduction, before a plan's page is drawn or checked; `testsUnder`, optional, names the
 *    folders `tests` does not run, each with the command that does, or null for one left to a run by hand
 *    (`testCommandOf`);
 *  - `planDiff`: a module that draws what a proposed migration does to the database, or null;
 *  - `repositories`, optional: where the checkout of another repository is, by its name, as a path from the
 *    root. A plan that points at a piece planned there is read against it (`plan.md` § "Planned elsewhere").
 *
 * A key that is missing or of the wrong shape stops the tool, naming it.
 */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { layoutOf, type LayoutSettings } from './layout';

export const CONFIG_FILE = 'comprehension.config.json';

export interface PageNamingCode {
  page: string;
  kind: 'debt' | 'rule' | 'convention';
  /** How the page is cut into entries: a list's items, the constitution's numbered rules, the headings. */
  split: 'list' | 'rule' | 'heading';
}

export interface Config extends LayoutSettings {
  name: string;
  stack: string | { sourceIndex: string[]; titles: string[]; strip?: string[] };
  cache: string;
  docs: string;
  hub: { label: string; page: string } | null;
  actor: string;
  pagesNamingCode: PageNamingCode[];
  commands: {
    /** What runs a tool of this folder, the tool's path following. */
    tool: string[];
    /** Runs test files once, their paths following. */
    tests: string[];
    /** Keeps test files running at each save, their paths following. */
    watch: string[];
    /** Runs screen journeys. An empty list disables this optional integration, regardless of whether
     *  the product has a UI. Its spec is then spec.md alone and needs no journey run or captures. */
    journeys: string[];
    /** Optional: the test folders `tests` does not run, each as a path from the root ending in `/`, with the
     *  command that runs a file of it once, its paths following, or null for a folder no tool runs (a server
     *  that must be started first, a paid call). */
    testsUnder?: Record<string, string[] | null>;
  };
  planDiff: string | null;
  repositories?: Record<string, string>;
}

/** The nearest folder holding the configuration, from where the tool was started and upwards: the repository
 *  root. Found from the working directory and not from this file's own place, so that every runner that loads
 *  this module (a script, the unit tests' setup, the browser tests) finds it the same way. */
function findRoot(): string {
  let dir = process.cwd();
  for (;;) {
    if (existsSync(join(dir, CONFIG_FILE))) return dir;
    const parent = dirname(dir);
    if (parent === dir) throw new Error(`config: no ${CONFIG_FILE} in ${process.cwd()} or a folder above it — the tools read the project's layout from it`);
    dir = parent;
  }
}

export const ROOT = findRoot();

type Shape = 'string' | 'strings' | 'object' | 'array' | 'stack';
const SHAPES: Array<[key: string, shape: Shape, nullable?: true]> = [
  ['name', 'string'], ['stack', 'stack'], ['cache', 'string'], ['docs', 'string'], ['hub', 'object', true], ['actor', 'string'],
  ['source', 'object'], ['source.scan', 'strings'], ['source.app', 'strings'], ['source.product', 'strings'], ['source.words', 'strings'],
  ['source.mechanisms', 'strings'], ['source.chips', 'array'],
  ['tests', 'object'], ['tests.roots', 'strings'], ['tests.files', 'string'], ['tests.narrative', 'strings'], ['tests.browser', 'strings'],
  ['tests.journeys', 'string'], ['tests.server', 'object', true],
  ['pagesNamingCode', 'array'],
  ['commands', 'object'], ['commands.tool', 'strings'], ['commands.tests', 'strings'], ['commands.watch', 'strings'], ['commands.journeys', 'strings'],
  ['planDiff', 'string', true],
];

function readConfig(): Config {
  const file = join(ROOT, CONFIG_FILE);
  let json: unknown;
  try { json = JSON.parse(readFileSync(file, 'utf8')); } catch (error) { throw new Error(`config: ${CONFIG_FILE} is not JSON — ${(error as Error).message}`); }
  for (const [key, shape, nullable] of SHAPES) {
    const value = key.split('.').reduce<unknown>((at, part) => (at !== null && typeof at === 'object' ? (at as Record<string, unknown>)[part] : undefined), json);
    if (value === null && nullable) continue;
    const strings = (x: unknown) => Array.isArray(x) && x.length > 0 && x.every((part) => typeof part === 'string');
    if (shape === 'stack') {
      const commands = value as { sourceIndex?: unknown; titles?: unknown; strip?: unknown } | null;
      if (typeof value === 'string' || (commands !== null && typeof commands === 'object' && strings(commands.sourceIndex) && strings(commands.titles) && (commands.strip === undefined || strings(commands.strip)))) continue;
      throw new Error(`config: ${CONFIG_FILE} — "stack" is ${value === undefined ? 'missing' : 'neither a module\'s path nor { "sourceIndex": [command…], "titles": [command…] }, with "strip": [command…] or without'}`);
    }
    const ok = shape === 'string' ? typeof value === 'string'
      : shape === 'strings' ? Array.isArray(value) && value.every((x) => typeof x === 'string')
        : shape === 'array' ? Array.isArray(value)
          : value !== null && typeof value === 'object' && !Array.isArray(value);
    if (!ok) throw new Error(`config: ${CONFIG_FILE} — "${key}" is ${value === undefined ? 'missing' : `not ${shape === 'strings' ? 'a list of strings' : shape === 'array' ? 'a list' : `a${shape === 'object' ? 'n' : ''} ${shape}`}`}${nullable ? ' (or null)' : ''}`);
  }
  const under = (json as { commands: { testsUnder?: unknown } }).commands.testsUnder;
  if (under !== undefined) {
    const commandOrNull = (x: unknown) => x === null || (Array.isArray(x) && x.length > 0 && x.every((part) => typeof part === 'string'));
    if (under === null || typeof under !== 'object' || Array.isArray(under) || !Object.entries(under).every(([root, command]) => root.endsWith('/') && commandOrNull(command))) {
      throw new Error(`config: ${CONFIG_FILE} — "commands.testsUnder" is not an object of folders, each ending in "/", to a command (a list of strings) or null`);
    }
  }
  return json as Config;
}

export const config = readConfig();
export const layout = layoutOf(config);

/**
 * The command that runs a test file once, its path following: that of the folder of `commands.testsUnder` it is
 * under, else `commands.tests`. Null for a file no tool runs: one under a folder `testsUnder` gives null, and a
 * browser's, which the journeys' command runs as a whole.
 */
export function testCommandOf(file: string): string[] | null {
  const under = Object.entries(config.commands.testsUnder ?? {}).find(([root]) => file.startsWith(root));
  if (under) return under[1];
  return layout.isBrowserTest(file) ? null : config.commands.tests;
}

// ── The method's own layout, under `docs` and `cache` ──────────────────────────

/** A feature's folder, from the root: `<docs>/features/<feature>`. */
export const FEATURES = `${config.docs}/features`;
export const featureFolder = (feature: string) => `${FEATURES}/${feature}`;

/** The generated pages: the narratives, the mechanisms, the plans, and their stylesheet. */
export const PAGES = `${config.docs}/comprehension_harness`;

/** What a journey run writes, a folder per journey, and the journey pages beside them. */
export const JOURNEYS = `${config.docs}/design/journeys-generated`;

/** The stories of the last test run: one JSON array per test file. A cache — a clean install empties it, a run refills it. */
export const STORIES = `${config.cache}/stories`;
export const STORIES_DIR = join(ROOT, STORIES);
/** A test file's stories are one JSON array in one file, named after it (`file` relative to the repository root). */
export const storyFile = (file: string) => join(STORIES_DIR, `${file.replace(/\//g, '__')}.json`);

/** The map's snapshots. */
export const MAP_DIR = join(ROOT, config.cache, 'map');

/** A command of the configuration as one would type it, with what follows it. */
export const typed = (command: readonly string[], ...rest: string[]) => [...command, ...rest].join(' ');
