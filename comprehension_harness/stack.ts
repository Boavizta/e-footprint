/**
 * stack.ts — what a stack gives the tools, as types. The tools (the renderers, the plan model, the map) are
 * written once; a project's stack — its language, its test runner, its browser runner — gives them four things:
 *
 *  1. stories: what each test crossed (`Story`), one JSON array per test file, written by the test run;
 *  2. the source index: what the source says without running (`SourceReader`), asked at each render;
 *  3. test titles: planned and written (`TitleReader`), asked for one file's text;
 *  4. a journey run: screens, captures, planned cases (`JourneyCase`), written by the browser run.
 *
 * 1 and 4 are files in every stack. 2 and 3 are read from the source: a stack that runs in Node answers them
 * with a module; any other stack with a command that prints a JSON document, which a reader of the tools turns
 * into the same interface.
 *
 * Rules the four share:
 *  - a path is relative to the repository root, with `/`; lines and columns start at 1;
 *  - a site is a file and a line: one `narrate`, `event` or `planned` call per line;
 *  - a function has one name, the one the stack's own frames print: a story's frame and an indexed function are
 *    matched by `file` and `fn`;
 *  - a test has one title: a story's `test`, a narrative's `firstTest` and a `TestTitle.title` are the same
 *    string for the same test.
 */

export interface Location {
  file: string;
  line: number;
  column: number;
}

// ── 1. Stories ─────────────────────────────────────────────────────────────────

export type NarrativeKind = 'product' | 'mechanism';

/** The narrative a test is declared in. */
export interface NarrativeDeclaration {
  title: string;
  kind: NarrativeKind;
}

export interface StoryFrame extends Location {
  /** The function's name, as the stack's frames print it; null for a function with no name. */
  fn: string | null;
  /** The TypeScript stack only: the name the source-mapped frame prints, read where `fn` is null. */
  mappedFn?: string | null;
}

export interface StoryHit {
  /** A narrative step, the cause (`event`) the steps that follow answer, or a `planned` change on existing code. */
  kind: 'step' | 'event' | 'planned';
  sentence: string;
  /** The watch's value, made plain; `{ error }` when computing it threw. */
  watch: unknown;
  /** The call site: the first frame outside the three calls' own file. */
  site: StoryFrame;
  /** The frames above it, nearest first, of the repository's own files. */
  stack: StoryFrame[];
  /** Milliseconds since the test began. */
  atMs: number;
  /** For a planned hit whose site says what it should see: that, at this crossing, a key of the watch each. */
  expect?: unknown;
}

/** A site that fired more often in one test than a story keeps. */
export interface CappedSite {
  file: string;
  line: number;
  /** Hits of the site recorded in `hits`. */
  kept: number;
  /** Hits counted and not recorded. */
  omitted: number;
}

/** What one test crossed. A test that crosses no site has no story. */
export interface Story {
  file: string;
  test: string;
  narrative: NarrativeDeclaration | null;
  /** The test marked itself its narrative's reference case. */
  canonical: boolean;
  /** Grows with the run: a narrative's variants are told in this order. */
  order: number;
  /** Shown, never judged. `xfailed` for a failure the run expected. */
  state: string | undefined;
  durationMs: number | null;
  hits: StoryHit[];
  capped?: CappedSite[];
  /** The test is declared to fail today, for a bug its piece fixes: it has a story whatever it crossed. */
  reproduction?: boolean;
  /** How the test failed, of a failure the run expected too: the message, and where. */
  failure?: StoryFailure;
}

export interface StoryFailure {
  message: string;
  /** Null for a failure raised outside the repository's files. */
  file: string | null;
  line: number;
}

// ── 2. The source index ────────────────────────────────────────────────────────

/** What a planned site says of its place: `changed` (a `planned` on existing code), `removed`
 *  (`planned.remove`), `added` (the only body of a shell), `evidence` (a place a bug shows, which marks no
 *  change and goes with the fix). */
export type PlannedChange = 'changed' | 'removed' | 'added' | 'evidence';
export const PLANNED_CHANGES: readonly PlannedChange[] = ['changed', 'removed', 'added', 'evidence'];

/** A `planned` site, as the source states it: its piece (`<feature>#<slug>`) and what kind of change it announces
 *  (`PlannedChange`). `signature` is a shell's declaration text up to its body. */
export interface PlannedSite {
  feature: string;
  slug: string;
  /** What changes at this place, in one clause, as written at the site; for evidence, what is seen there today. */
  sentence: string;
  change: PlannedChange;
  signature: string | null;
  /** What the place should see, as the site writes it: a literal, or an expression computed at each crossing.
   *  Its value at a crossing is the story's (`StoryHit.expect`). */
  expect?: string;
  /** The keys of the watch each crossing should see a value of its own for: the bug shows where two crossings
   *  of a test saw the same. */
  distinct?: string[];
}

/** A `narrate`, `event` or `planned` call, as the source holds it. */
export interface RawSite extends Location {
  kind: 'step' | 'event' | 'planned';
  /** The function the call sits in, named as a frame of it would be. */
  fn: string;
  /** The call's sentence when it is a literal, else null. */
  sentence: string | null;
  planned?: PlannedSite;
}

export type Resolution =
  | { linked: true; rule: 1 | '1b' | 2 | 3; at: Location }
  | { linked: false; reason: string };

/** What a test file says about a narrative it declares: the first paragraph of the comment above it, its first test. */
export interface Declaration {
  summary: string;
  firstTest: string | null;
  line: number;
}

/** A function a site's function is referred to by, or calls. */
export interface Neighbour {
  file: string;
  line: number;
  fn: string;
  /** Whether that function holds a `narrate` call of its own. */
  narrated: boolean;
  /** How it is related when not by a direct reference: "via X" (it refers to X, which refers to the site's
   *  function), "handed as onChange by X" (X renders the site's component and passes it this function). */
  how?: string;
}

/** The nearest named function a site sits in, and the code next to it. Candidates, not what a run observed. */
export interface Around {
  /** First and last line of the function. */
  range: [number, number];
  callers: Neighbour[];
  callees: Neighbour[];
}

/** Everything the tools ask the source. Each answer is read from the source as it stands. */
export interface SourceReader {
  /** The shape of a name this language declares, in whichever of its styles: a backticked token of that shape
   *  that resolves to nothing is what `--check` holds a sentence and a page of rules to. It is the stack's to
   *  say: words joined by an underscore are a function in Python and a database column in TypeScript. One
   *  lowercase word is shaped like any word, and is in no stack's shape. */
  looksDeclared: RegExp;
  /** The sites of a file, in source order. Throws for a file the stack does not read; refuses, with the file and
   *  the line, a `planned` call whose tag or sentence is no literal and a shell that throws anything but its tag. */
  sites(file: string): RawSite[];
  /** The product source files: where a `planned` call can stand and where a name is looked for. */
  sourceFiles(): string[];
  /** The source files that hold a site. */
  siteFiles(): string[];
  /** The test files that declare a narrative, found in the source: a cold start knows what to run. */
  narrativeTestFiles(): string[];
  /** The narrative `file` declares under `title`. Throws when it declares none. */
  declaration(file: string, title: string): Declaration;
  /** Where a name of a sentence is declared, seen from a site: an import of its file (rule 1), a local of the
   *  functions around the call, nearest first (1b), a top-level declaration of the file (2), one unique across
   *  the source (3). Otherwise the reason. */
  resolve(site: RawSite, name: string): Resolution;
  /** Rules 2 and 3 with no site: a top-level declaration in one of `files`, else one unique across the source. */
  resolveUnscoped(name: string, files: readonly string[]): Location | null;
  /** A declaration that is no top-level one (a local, a method, a field), in the files of `places`, nearest to one of them. */
  resolveNear(name: string, places: ReadonlyArray<{ file: string; line: number }>): Location | null;
  /** The first line where the site's own function uses the symbol declared at `at`, the call itself left out. */
  useSite(site: RawSite, name: string, at: Location): Location | null;
  /** The same for the function `fn` of `file`; null when the file holds no single function of that name. */
  useIn(file: string, fn: string, name: string, at: Location): Location | null;
  /** The source file a path names, or a basename when exactly one source file has it. */
  sourceFile(token: string): string | null;
  /** The function around a site; null when the site sits in no named function. */
  around(site: RawSite): Around | null;
  /** A reader of the source as it is now, reusing what it can of this one (a live page re-renders at each save). */
  fresh(): SourceReader;
}

/**
 * The source index as a document: what a stack that does not run in Node prints, and `json-source.ts` answers
 * `SourceReader` from. Tables, by file; the stack fills them as far as its parser can tell, by name where it
 * has no identities.
 */
export interface SourceIndexDocument {
  /** The shape of a name the language declares (`SourceReader.looksDeclared`), as the source of a regular
   *  expression both the stack's language and JavaScript read the same. */
  looksDeclared: string;
  /** Every narrative a test file declares. */
  narratives: Array<{ file: string; title: string; line: number; summary: string; firstTest: string | null }>;
  /** Every file of the source folders, and every test file that declares a narrative or holds a site. */
  files: Record<string, SourceFileIndex>;
}

export interface SourceFileIndex {
  /** The `narrate`, `event` and `planned` calls, in source order. A `planned` one says its piece and its change. */
  sites: Array<{
    kind: 'step' | 'event' | 'planned';
    line: number;
    column: number;
    fn: string;
    sentence: string | null;
    planned?: { feature: string; slug: string; change: PlannedChange; signature: string | null; expect?: string; distinct?: string[] };
  }>;
  /** Every named function, with the line its name is on and its last line. A site, a local or a use belongs to
   *  the functions whose lines hold it, the innermost first. */
  functions: Array<{ fn: string; line: number; column: number; endLine: number }>;
  /** The top-level declarations. */
  declarations: Array<{ name: string; line: number; column: number }>;
  /** A name the file imports, with where it is declared. */
  imports: Array<{ name: string; at: Location }>;
  /** Every declaration that is no top-level one: a parameter, a variable, an inner function, a method, a field. */
  locals: Array<{ name: string; line: number; column: number }>;
  /** A reference to a name declared in the source, with that declaration. What stands inside a `narrate`,
   *  `event` or `planned` call is left out (a watch is documentation, not use), and so is a reference the stack
   *  cannot place. Callers and callees are read from these. */
  uses: Array<{ name: string; line: number; column: number; at: Location }>;
}

/** What a stack's module exports under `stack` (`comprehension.config.json` names the module). */
export interface Stack {
  /** A reader of the source as it stands. */
  openSource(): SourceReader;
  titles: TitleReader;
}

// ── 3. Test titles ─────────────────────────────────────────────────────────────

export interface TestTitle {
  title: string;
  line: number;
  column: number;
  /** Declared with no body: a test to write. */
  planned: boolean;
  /** Written, and declared to fail today for a bug its piece fixes. */
  reproduction?: boolean;
  /** A short hash of a written test's own lines, its declaration left out: the same once a reproduction is
   *  declared a test like another. What an approval holds of a reproduction (`PlanTodo.body`). */
  body?: string;
}

/** A case a feature will add to a journey, declared in a journey test. */
export interface JourneyCaseDeclaration extends Location {
  feature: string;
  journey: string;
  screen: string;
  title: string;
}

/** What a line opens: a test, a group of tests or a declaration. A `@planned` comment right above it stands on it. */
export interface Stand {
  line: number;
  /** What the pages print: `it "<title>"`, a declared name. */
  label: string;
  /** The test's title, when the line opens one test. */
  test: string | null;
}

/** One file's text, read for its tests. */
export interface TestFile {
  /** Every test, in file order. */
  tests: TestTitle[];
  stands: Stand[];
  journeyCases: JourneyCaseDeclaration[];
}

/** Asked for a file's text, not for the checkout: the lot check reads a test file on both sides of a commit. */
export interface TitleReader {
  read(file: string, text: string): TestFile;
  /** Optional. The files about to be read, at once: a reader that costs a process answers them in one. */
  prime?(files: ReadonlyArray<{ file: string; text: string }>): void;
}

// ── 4. A journey run ───────────────────────────────────────────────────────────

/** A control of a screen, as the page and the accessibility tree have it. */
export interface Control {
  /** Its index among the screen's controls. */
  i: number;
  tag: string;
  /** The element's own text, trimmed. */
  text: string;
  title: string | null;
  ariaLabel: string | null;
  testId: string | null;
  disabled: boolean;
  /** Inside an open dialog. */
  inDialog: boolean;
  /** Not a control for the accessibility tree: an element that only looks clickable. */
  pointerOnly: boolean;
  /** As the accessibility tree has it; null when the element is no control there. */
  role: string | null;
  name: string | null;
}

/** A call a server step answered during a journey. */
export interface ServerCall {
  name: string;
  does: string;
  method: string;
  /** Path and query, as the app asked. */
  path: string;
  /** The request's JSON body, when it had one. */
  sent: unknown;
  status: number;
  /** The answer's body, when the step gave one. */
  answered: unknown;
  /** The test that owns what the real server does here. */
  truth: string;
}

export interface StorySite { file: string; line: number; fn: string | null }

/** What led to a screen. */
export interface Cause {
  /** `open`: the case opened the app at a URL. `action`: the learner did something. `time`: the case let a paused clock run. */
  kind: 'open' | 'action' | 'time';
  url: string;
  /** For `time`: how long, and what that wait is to the learner. */
  elapsed?: { ms: number; why: string };
  /** DOM event type, for an action. */
  type?: string;
  key?: string | null;
  /** The control it landed on, as the previous screen listed it (index into that screen's controls); null when the element was not there at that screen. */
  control?: number | null;
  /** Fallback naming, read off the element at the moment of the action. */
  on?: { tag: string; text: string; title: string | null; ariaLabel: string | null };
  /** `event(…)` calls the action fired, in order. */
  events: Array<{ sentence: string; site: StorySite; watch: unknown }>;
  /** `narrate(…)` sites crossed after it, distinct, in first-hit order. */
  steps: Array<{ sentence: string; site: StorySite; count: number }>;
  /** URLs the frame navigated to after it (same-document included). */
  navigations: string[];
  /** The named server steps it reached, in the order the stubs answered them. */
  server: ServerCall[];
}

export interface ScreenRecord {
  id: string;
  why: string;
  url: string;
  /** A planned change of this screen: the feature and its mockup fragment (repo-relative), which carries the screen's address. */
  planned?: { feature: string; mockup: string; what: string };
  /** Relative to the journey folder. Absent on a return whose DOM is the first visit's. */
  capture: string | null;
  css: string;
  sha: string;
  bytes: number;
  counts: Record<string, number>;
  /** Index of the earlier screen of this case with the same id, when this is a return. */
  returnsTo: number | null;
  /** The DOM is the first visit's, focus and scroll offsets apart. */
  identicalToFirstVisit: boolean | null;
  movedSinceFirstVisit: { focus: boolean; scroll: boolean } | null;
  controls: Control[];
  /** What happened between the previous screen (or the seed) and this one. */
  before: Cause[];
}

/** A case a feature will add to the journey. */
export interface PlannedCase { feature: string; screen: string; title: string; line: number }

/** One case of a journey, as its run wrote it. */
export interface JourneyCase {
  journey: { name: string; slug: string; who: string; wants: string; now: string; file: string; todos: PlannedCase[]; viewport?: { width: number; height: number } };
  title: string;
  slug: string;
  line: number;
  status: string | undefined;
  narrate: string;
  screens: ScreenRecord[];
  /** Actions after the last screen. */
  after: Cause[];
}

// ── Beside the stack: a project's own hook ─────────────────────────────────────

/** What a proposed migration does to the database, drawn for a plan page. A project that has a way to show it
 *  names a module exporting this (`planDiff` of the configuration); the pages do without otherwise. */
export interface PlanDiff {
  /** The diff for one migration's SQL, as a fragment of the page at `page` with its stylesheet; `infidelity`
   *  lists where the copy it was drawn on reads differently from the real database. Throws when the SQL fails. */
  draw(sql: string, page: string): Promise<{ html: string; css: string; infidelity: string[] }>;
  /** Whether an error of `draw` says the database could not be reached, and not that the SQL is wrong. */
  isUnreachable(error: unknown): boolean;
  /** What to run when the database could not be reached. */
  remedy: string;
}
