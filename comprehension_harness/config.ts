/**
 * config.ts — the project the tools run in: where it is, and what `comprehension.config.json` at its root says.
 *
 * The tools are the same in every project. What differs is data, and it is all in that one file:
 *
 *  - `name`: the project's name, on its pages' titles;
 *  - `stack`: what answers what the source says (`stack.ts`): a module, as a path from the root, or for a
 *    stack that does not run in Node the two commands that print it as JSON (`sourceIndex`, `titles`), beside
 *    which such a stack keeps keys of its own (the Python stack's `calls`);
 *  - `cache`: where what a run writes and a render reads is kept (the stories, the map's snapshots);
 *  - `docs`: the folder of the project's documents. The feature folders (`features/`), the generated pages and
 *    the journeys' captures are under it, by the method's own layout; the local app serves it;
 *  - `hub`: the page every generated page links back to, or null;
 *  - `productPage`: the name of the one page the product narratives are drawn on, whose hand-written title
 *    and lede are `<name>.skeleton.html` beside it;
 *  - `actor`: the word a product narrative's causes open with ("The user taps …" for `user`); any other cause is the world's;
 *  - `source` and `tests`: what a file is, by its path (`layout.ts`);
 *  - `pagesNamingCode`: the pages whose entries mark the steps they name: debts, rules, conventions;
 *  - `commands`: how a tool, the narrative tests and the journeys are run here. `tests` also runs the test files
 *    that hold a plan's reproduction, before a plan's page is drawn or checked;
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
  stack: string | { sourceIndex: string[]; titles: string[] };
  cache: string;
  docs: string;
  hub: { label: string; page: string } | null;
  productPage: string;
  actor: string;
  pagesNamingCode: PageNamingCode[];
  commands: {
    /** What runs a tool of this folder, the tool's path following. */
    tool: string[];
    /** Runs test files once, their paths following. */
    tests: string[];
    /** Keeps test files running at each save, their paths following. */
    watch: string[];
    /** Runs the journeys. */
    journeys: string[];
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
  ['name', 'string'], ['stack', 'stack'], ['cache', 'string'], ['docs', 'string'], ['hub', 'object', true], ['productPage', 'string'], ['actor', 'string'],
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
      const commands = value as { sourceIndex?: unknown; titles?: unknown } | null;
      if (typeof value === 'string' || (commands !== null && typeof commands === 'object' && strings(commands.sourceIndex) && strings(commands.titles))) continue;
      throw new Error(`config: ${CONFIG_FILE} — "stack" is ${value === undefined ? 'missing' : 'neither a module\'s path nor { "sourceIndex": [command…], "titles": [command…] }'}`);
    }
    const ok = shape === 'string' ? typeof value === 'string'
      : shape === 'strings' ? Array.isArray(value) && value.every((x) => typeof x === 'string')
        : shape === 'array' ? Array.isArray(value)
          : value !== null && typeof value === 'object' && !Array.isArray(value);
    if (!ok) throw new Error(`config: ${CONFIG_FILE} — "${key}" is ${value === undefined ? 'missing' : `not ${shape === 'strings' ? 'a list of strings' : shape === 'array' ? 'a list' : `a${shape === 'object' ? 'n' : ''} ${shape}`}`}${nullable ? ' (or null)' : ''}`);
  }
  return json as Config;
}

export const config = readConfig();
export const layout = layoutOf(config);

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
