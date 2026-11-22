/**
 * layout.ts — what a project's configuration says of a file, as pure functions: no disk, so the plan model and
 * its tests take a layout as an argument. `config.ts` reads the project's own from `comprehension.config.json`.
 */

/** The tier of a test: `narrative` for a test that tells a flow, `server` for one a server step names as its
 *  truth, `unit` otherwise. */
export type Tier = 'narrative' | 'server' | 'unit';

/** The `source` and `tests` sections of `comprehension.config.json`. A folder is a prefix of a path, written
 *  with its closing `/`; a pattern is a regular expression over a path relative to the repository root. */
export interface LayoutSettings {
  source: {
    /** The folders a `@planned` comment can stand in. */
    scan: string[];
    /** The app's own code: a frame of it is "inside the app", and a name of a sentence is looked for there. */
    app: string[];
    /** The product's code: a commit that changes a file of it beyond the plan is a line of the lot check. */
    product: string[];
    /** The folders whose words count as "the code": a page token that appears in none of them is stale. */
    words: string[];
    /** The folders a `narrate` site is expected to belong to a mechanism narrative in. */
    mechanisms: string[];
    /** The chip a step carries, by its file's folder: `[folder, css class, label]`. */
    chips: Array<[folder: string, cls: string, label: string]>;
  };
  tests: {
    /** The folders of test code: an event written there is linked from the case, not from a helper. */
    roots: string[];
    /** Pattern: the files whose tests the plan reads (the unit and server tiers, the narratives). */
    files: string;
    /** The folders of the tests that declare a narrative. */
    narrative: string[];
    /** The folders of the tests a browser runs: no unit test. */
    browser: string[];
    /** Pattern: the test files that declare a journey. */
    journeys: string;
    /** The tests of the real server: one of `roots` is the server tier when a file under `namedIn` names its path. */
    server: { roots: string[]; namedIn: string[] } | null;
  };
}

export interface Layout {
  settings: LayoutSettings;
  isApp(file: string): boolean;
  isProduct(file: string): boolean;
  isTest(file: string): boolean;
  /** A file whose tests the plan reads. */
  isTestFile(file: string): boolean;
  isJourneyTest(file: string): boolean;
  /** A test of the real server, whether a server step names it or not. */
  isServerTest(file: string): boolean;
  /** A test file that is neither a narrative's nor a browser's. */
  isUnitTest(file: string): boolean;
  /** Where server steps are declared, each naming the test that is its truth. */
  declaresTruths(file: string): boolean;
  /** The tier of a test file. `truthSources` is the text of every file that declares server steps. */
  tierOf(file: string, truthSources: string): Tier;
}

const under = (folders: readonly string[]) => (file: string) => folders.some((f) => file.startsWith(f));

export function layoutOf(settings: LayoutSettings): Layout {
  const files = new RegExp(settings.tests.files);
  const journeys = new RegExp(settings.tests.journeys);
  const isTest = under(settings.tests.roots);
  const isNarrative = under(settings.tests.narrative);
  const isBrowser = under(settings.tests.browser);
  const isServerTest = under(settings.tests.server?.roots ?? []);
  return {
    settings,
    isApp: under(settings.source.app),
    isProduct: under(settings.source.product),
    isTest,
    isTestFile: (file) => files.test(file),
    isJourneyTest: (file) => journeys.test(file),
    isServerTest,
    isUnitTest: (file) => isTest(file) && !isNarrative(file) && !isBrowser(file),
    declaresTruths: under(settings.tests.server?.namedIn ?? []),
    tierOf: (file, truthSources) => (isNarrative(file) ? 'narrative' : isServerTest(file) && truthSources.includes(file) ? 'server' : 'unit'),
  };
}
