/**
 * render.ts — the narrative pages and the plan pages, generated from `narrate` stories.
 *
 *   npx tsx comprehension_harness/render.ts            # render every page
 *   npx tsx comprehension_harness/render.ts --check    # symbols that did not link, gaps, dead actions, a plan out of order
 *                                              # (a missing feature folder, a rule claimed that does not exist or
 *                                              # claimed twice, a `#slug` of plan.md naming no piece); exit 1 on any;
 *                                              # plus informative lists (unclaimed sites, stale page tokens,
 *                                              # untraced entries, rules with no owner)
 *   npx tsx comprehension_harness/render.ts --check --archive <feature>   # the archive gate: fails while a planned site of it remains
 *   npx tsx comprehension_harness/render.ts --strip <feature> [--dry-run]  # once the gate passes: takes the feature's `built` calls, the
 *                                              # tags of its test titles and its planned screens off the code, then
 *                                              # lists every line outside its folder that still names it; exit 1
 *                                              # while one is in the code
 *   npx tsx comprehension_harness/render.ts --approve <feature>           # on the reviewer's word only: writes the plan as it stands to
 *                                              # `specs/features/<feature>/plan.approved.json` and takes the `Changed:`
 *                                              # paragraphs off `plan.md`, once the plan passes the check; `--check`
 *                                              # then holds every difference to a reason
 *
 * Reads every story the stack's collector wrote under the stories folder of the project's cache
 * (one JSON array per test file; a cache, so a clean install empties it and a unit run refills it) and
 * renders one page per product narrative under `specs/comprehension_harness/narratives/`, one page per mechanism
 * narrative under `specs/comprehension_harness/mechanisms/`, one plan page per feature with a planned
 * site under `specs/comprehension_harness/plans/`, and `specs/comprehension_harness/index.html`, which lists every
 * generated page by kind, the journeys' and the specs' included, all on the one stylesheet
 * `specs/comprehension_harness/comprehension_harness.css` (hand-written, inlined). Nothing on a page is hand-written
 * or declared here: a narrative is declared where its story is produced —
 *
 *  - the test file declares it, a product narrative or a mechanism, under a title, with the stack's
 *    own declaration; the collector stamps each story with that title and kind. The comment above
 *    the declaration is the summary, read from the source. The first test is canonical unless one
 *    marks itself so; the others are variants. A page's title is the narrative's, its lede the summary;
 *    why a subsystem is shaped as it is belongs to the document that owns it, which links the page;
 *  - a feature's plan is its tagged sites (`plan.ts` holds the model and the rules): a piece is a
 *    slug, `<feature>#<slug>`, on every `planned('<feature>#<slug>', sentence)` call (or
 *    `planned.remove(…)`, or the only body of a shell that throws after it), every
 *    test to write titled `<feature>#<slug>: …` in any test file and every comment opening with `@planned` and
 *    the tag. The plan page opens with the feature's `plan.md` (what no site carries: one section per
 *    decision, each `#slug` linking its piece), then tells the pieces in the order the narratives'
 *    canonical stories first cross their `planned` calls, each with its sites, the canonical step
 *    around each call, the tests that reach it, its planned tests by tier, and — for the piece that
 *    carries the feature folder's proposed `.sql` — the `db:plan` diff of the database view; it ends
 *    with the rules of `spec.md` and the one test that owns each. A narrative page draws a planned
 *    hit as a dashed row at its position; `--check --archive <feature>` fails while any site remains;
 *  - a step's identity is derived, `<file>#<function>#<ordinal>`: the ordinal counts the
 *    `narrate` sites of one function in source order, read from the source index, so a
 *    story's hit is matched to a step by its call site alone — no id is written anywhere;
 *  - a narrative's steps are the distinct sites that fired during its canonical test, in
 *    first-hit order; repeat hits are numbered stops; a variant is paired to the canonical
 *    by that identity and reports the canonical steps it did not reach;
 *  - a site is a mechanism's when the mechanism's canonical story hit it. A product story's
 *    hits at such sites are not steps of the product narrative: they collapse into one
 *    "rides on" row per mechanism per segment, placed where the first such hit occurred,
 *    naming the mechanism's steps crossed and linking its page. The product page's "Rides on"
 *    block and the mechanism page's "Exercised by" list are computed from the same facts;
 *  - the sentence is markdown-lite: `**bold**` is the rule the step enacts, a backticked
 *    token is a code symbol, resolved from the step's point of view by the stack's source
 *    reader (an import → its declaration; a local of the step's own function → its line; a
 *    top-level declaration of the file; a top-level declaration, exported or not, unique
 *    across `src/`; otherwise plain code) and linked like the step's own line, with a "called
 *    here" alternate — the line inside the step's own function where the symbol is used, the
 *    traced call line when the stories carry one, else the first static reference;
 *  - causes: an `event` hit opens a segment, and every step hit that follows belongs to it
 *    until the next event; the row carries an actor chip (learner / world, from the
 *    sentence's subject) and the segment's steps are grouped beneath it. An event written in
 *    a test helper links the line of the case that called the helper, the helper as a named
 *    alternate ("via `mount`") in the link's right-click menu; a hit under `src/` links its
 *    own site. A leading segment
 *    with no event is a gap, an event with no step after it a dead action — both in `--check`.
 *    A cause whose right answer is silence says so, "…; nothing follows." — then a step
 *    after it is the finding;
 *  - the chip, from the file's folder; the watch names and values, from the thunk;
 *  - nesting, from the call stack: a run of steps whose nearest enclosing `src/` frame is
 *    one function that is itself no step's site is rendered inside a "within" row naming
 *    that function. The row's claim is checked over every stop of every grouped step:
 *    "nothing else on this run calls them" is emitted only when it holds, otherwise the
 *    other callers seen are named. (A link a collector may record through the async context
 *    is not used here: it does not survive every promise scheduler.);
 *  - backlinks: the pages that name code — `specs/backlog/tech-debt.md`, the constitution, the
 *    conventions — are indexed by `backlinks.ts` (their backticked tokens resolved with
 *    no step scope), and a step whose function, file or linked sentence symbol an entry names
 *    carries a marker in its watch column linking the entry; a mechanism page lists every
 *    entry that names any of its steps under "Named by". Nothing is cross-referenced by hand.
 *
 * Every source link carries the `data-review-source-href` the repo's `specs/review-links.js`
 * re-points on the reader's machine, so VS Code links and the debug route work unchanged.
 *
 * What the source says without running — where the calls are, where a name is declared, what a test file
 * holds — is asked of the project's stack (`stack.ts`; `source-index.ts` gives a site its identity). This
 * file reads no source language itself.
 */
import { renderStamp } from './render-stamp';
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { CONFIG_FILE, FEATURES, JOURNEYS, PAGES, ROOT, STORIES, STORIES_DIR, config, featureFolder, layout, testCommandOf, typed } from './config';
import { blocksHtml, parseIntent, type MdBlock } from './intent-md';
import { loadPlanDiff, openSource, strip, titles } from './project-stack';
import { SourceIndex, type SourceSite } from './source-index';
import type { Location, NarrativeKind, PlannedSite, Resolution, SourceReader, Story, StoryFrame, StoryHit, Stripped } from './stack';
import { approvalRefusal, assemblePlans, builtPlaceOf, idsToKeep, landingsToFreeze, markOf, type BuiltLanding, commitBlocks, commitsNamed, editItems, filesNamed, findings, isOpenTest, isOwnNotice, namesFeature, isStoryOf, lotLeft, names, shared, siteLineOf, unexpected, type CommitBlock, type Crossing, type FrozenChain, type FunctionLines, BESIDE, NOTES, asksNoEdit, changedAway, REPRODUCTIONS, UNPLANNED, chainsToFreeze, fixedChains, isBuiltPlace, placesCrossed, reproductionKeyOf, type PieceCommit, overSentenceBudget, parseTag, pieceDocOf, pieceQuestion, planDocOf, reviewItems, waiverQuestion, writeAcceptedAnswers, type PointerTarget, replaceSlugRefs, scanJourneyCases, scanPlannedComments, scanTodos, todosByTier, TIERS, type FeatureDocs, type JourneyCase, type PlanBaseline, type DeltaLine, type PlanChange, type PlanFeedback, type PlanLot, type PlanMove, type ReviewItem, type UnitDelta, type Plan, type PlanGroup, type PlanSite, type PlanSection, type PlanPiece, type PlanTodo, type StaticSite } from './plan';
import { commitsOfLines, hunkReader, readPieceCommits, type HunkReader } from './commits';
import { buildBacklinks, describeEntry, markersFor, unresolvedDeclaredLooking, untracedEntries, type BacklinkIndex, type Marker, type PageEntry, type StepKeys } from './backlinks';

export type { PlannedSite, Story, StoryFrame, StoryHit };
export { SourceIndex };
export { TIERS, todosByTier };
export type { Plan, PlanDoc, PlanGroup, PlanRule, PlanSection, PlanSite, PlanPiece, PlanTodo, StaticSite, Tier } from './plan';

export { ROOT };
/** This script, from the root: what a page and a message tell the reader to run. */
const SELF = relative(ROOT, fileURLToPath(import.meta.url));
const PAGE_CSS = join(ROOT, PAGES, 'comprehension_harness.css');
export const NARRATIVES_DIR = join(ROOT, PAGES, 'narratives');
export const MECHANISMS_DIR = join(ROOT, PAGES, 'mechanisms');
export const PLANS_DIR = join(ROOT, PAGES, 'plans');
/** The list of every generated page, by kind. */
export const INDEX_PAGE = join(ROOT, PAGES, 'index.html');
/** From either page folder to the repository root, for `data-review-source-href`. */
const TO_ROOT = `${relative(MECHANISMS_DIR, ROOT)}/`;
/** From either page folder to the documents' folder, where `review-links.js` is. */
const TO_DOCS = `${relative(MECHANISMS_DIR, join(ROOT, config.docs))}/`;
/** The link every page carries back to the project's hub, when it has one. */
const HUB = config.hub ? `<a href="${relative(MECHANISMS_DIR, join(ROOT, config.hub.page))}" target="_blank" rel="noopener">${config.hub.label}</a>` : '';
/** The app's own folders, as a message names them. */
const APP = config.source.app.join(', ');
/** The folders a `narrate` site is expected to belong to a mechanism in (`--check`, informative). */
const MECHANISM_FOLDERS = config.source.mechanisms;

// ── Stories ────────────────────────────────────────────────────────────────────

/** Every story of the last unit run: one JSON array per test file, in test order. */
export function readStories(): Story[] {
  if (!existsSync(STORIES_DIR)) return [];
  const stories: Story[] = [];
  for (const f of readdirSync(STORIES_DIR).sort()) {
    if (!f.endsWith('.json')) continue;
    const ofFile: unknown = JSON.parse(readFileSync(join(STORIES_DIR, f), 'utf8'));
    if (!Array.isArray(ofFile)) throw new Error(`comprehension-render: ${join(STORIES_DIR, f)} is not an array of stories — delete it and run the unit project again`);
    stories.push(...(ofFile as Story[]));
  }
  return stories;
}

/** What a script prints when the cache holds no story: a cold start (a fresh checkout, an `npm ci`), with its remedy. */
export const NO_STORIES = `no unit stories under ${STORIES}/ (a fresh checkout or an \`npm ci\` leaves none) — ${typed(config.commands.tests)}`;

// ── Derivation ─────────────────────────────────────────────────────────────────

export interface Step {
  n: number;
  /** The derived identity, `<file>#<function>#<ordinal>`. */
  id: string;
  source: SourceSite;
  sentence: string;
  site: StoryFrame;
  stops: StoryHit[];
  /** The nearest enclosing `src/` frame above the first stop's site, if any. */
  within: StoryFrame | null;
}

/** A narrative as the stories and the source declare it. */
export interface Narrative {
  kind: NarrativeKind;
  title: string;
  slug: string;
  /** The declaring test file. */
  file: string;
  summary: string;
  declaredAt: number;
  /** The reference case's title: the marked one, else the first `it`. */
  canonicalTest: string | null;
  canonical: Story | null;
  variants: Story[];
  /** The canonical's steps, with the sites an earlier mechanism owns left out. */
  steps: Step[];
  stepIds: Set<string>;
  /** Every site any story of the narrative hit — what a mechanism owns, its steps included. */
  siteIds: Set<string>;
}

const EMPTY = new Set<string>();

/** The step hits grouped by call site, in first-hit order, leaving out the sites in `exclude` (another
 *  narrative's). Events are not steps: see `deriveSegments`. */
function deriveSteps(story: Story, index: SourceIndex, exclude: ReadonlySet<string> = EMPTY): Step[] {
  const byId = new Map<string, Step>();
  for (const hit of story.hits) {
    if (hit.kind !== 'step') continue;
    const source = index.identity(hit.site);
    if (exclude.has(source.id)) continue;
    let step = byId.get(source.id);
    if (step === undefined) {
      step = {
        n: byId.size + 1,
        id: source.id,
        source,
        sentence: hit.sentence,
        site: hit.site,
        stops: [],
        within: hit.stack.find((f) => layout.isApp(f.file)) ?? null,
      };
      byId.set(source.id, step);
    }
    step.stops.push(hit);
  }
  return [...byId.values()];
}

export const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/** Every narrative the stories declare, mechanisms first (their sites decide what a product step is). */
export function deriveNarratives(stories: Story[], index: SourceIndex): Narrative[] {
  const groups = new Map<string, Story[]>();
  for (const s of stories) {
    if (!s.narrative) continue;
    const key = `${s.file}::${s.narrative.title}`;
    groups.set(key, [...(groups.get(key) ?? []), s]);
  }
  const narratives: Narrative[] = [];
  for (const group of groups.values()) {
    const { file, narrative } = group[0];
    const { title, kind } = narrative!;
    const declared = index.declaration(file, title);
    const marked = group.filter((s) => s.canonical);
    if (marked.length > 1) throw new Error(`comprehension-render: "${title}" marks ${marked.length} cases canonical: ${marked.map((s) => s.test).join(' | ')}`);
    const canonicalTest = marked[0]?.test ?? declared.firstTest;
    const canonical = group.find((s) => s.test === canonicalTest) ?? null;
    narratives.push({
      kind, title, slug: slug(title), file,
      summary: declared.summary, declaredAt: declared.line,
      canonicalTest, canonical,
      variants: group.filter((s) => s !== canonical).sort((a, b) => a.order - b.order),
      steps: [], stepIds: new Set(), siteIds: new Set(),
    });
  }
  // Mechanisms first, the one whose canonical crosses the fewest distinct sites first: a mechanism
  // can ride on another (a provider's live read is a database's live read), and the more
  // primitive one is the one that crosses less. Each narrative's steps leave out the sites an
  // earlier mechanism already owns, so a site has one owner.
  const distinct = (n: Narrative) => (n.canonical ? deriveSteps(n.canonical, index).length : 0);
  narratives.sort((a, b) => (a.kind === b.kind ? (a.kind === 'mechanism' && distinct(a) !== distinct(b) ? distinct(a) - distinct(b) : a.title.localeCompare(b.title)) : a.kind === 'mechanism' ? -1 : 1));
  const owned = new Set<string>();
  for (const n of narratives) {
    if (!n.canonical) continue;
    n.steps = deriveSteps(n.canonical, index, owned);
    n.stepIds = new Set(n.steps.map((s) => s.id));
    // A mechanism owns every site its stories reach, a variant's included: a site only a variant
    // reaches (the wrapper's disabled branch) would otherwise surface as a step of whichever
    // narrative crosses it next. Its steps stay the canonical's.
    for (const story of [n.canonical, ...n.variants]) {
      for (const h of story.hits) if (h.kind === 'step') {
        const id = index.identity(h.site).id;
        if (!owned.has(id)) n.siteIds.add(id);
      }
    }
    if (n.kind === 'mechanism') for (const id of n.siteIds) owned.add(id);
  }
  return narratives;
}

/** Which mechanism owns a site: the first whose stories hit it. */
function ownership(narratives: Narrative[]): Map<string, Narrative> {
  const owner = new Map<string, Narrative>();
  for (const n of narratives) if (n.kind === 'mechanism') for (const id of n.siteIds) if (!owner.has(id)) owner.set(id, n);
  return owner;
}

/** A cause and the step hits that follow it until the next cause. A leading segment with no
 *  event is a gap: steps ran before anything was said to cause them. */
interface Segment {
  event: StoryHit | null;
  hits: StoryHit[];
}

function deriveSegments(story: Story): Segment[] {
  const segments: Segment[] = [];
  for (const hit of story.hits) {
    if (hit.kind === 'event') segments.push({ event: hit, hits: [] });
    else if (segments.length === 0) segments.push({ event: null, hits: [hit] });
    else segments[segments.length - 1].hits.push(hit);
  }
  return segments;
}

/** The actor of an event, from the sentence's subject: the learner, or the world. */
const ACTOR = new RegExp(`^The ${config.actor}\\b`);
const isActor = (sentence: string) => ACTOR.test(sentence);
const actor = (sentence: string) => (isActor(sentence) ? config.actor : 'world');

/** A cause whose right answer is silence says so; then a step after it is the finding, not the absence of one. */
const EXPECTS_SILENCE = /\bnothing follows\.?$/i;

const frameKey = (f: StoryFrame) => `${f.file}::${f.fn ?? f.mappedFn ?? '(anonymous)'}`;

/** The nearest enclosing `src/` function of a stop, as `file::fn`; null when none (the test called the site). */
function callerKey(stop: StoryHit): string | null {
  const f = stop.stack.find((fr) => layout.isApp(fr.file));
  return f ? frameKey(f) : null;
}

/** A step is nested when its enclosing function is no step's own function. */
function nestingKey(step: Step, steps: Step[]): string | null {
  const w = step.within;
  if (w === null || w.fn === null) return null;
  if (steps.some((s) => s.site.fn === w.fn && s.site.file === w.file)) return null;
  return frameKey(w);
}

/** The short label of a step in a variant's summary: the function, plus `#ordinal` when it has several sites. */
function label(step: Step, index: SourceIndex): string {
  return index.siblings(step.source) > 1 ? `${step.source.fn}#${step.source.ordinal}` : step.source.fn;
}

const CHIPS = config.source.chips;

function chip(file: string): string {
  const hit = CHIPS.find(([folder]) => file.startsWith(folder + '/'));
  if (hit) return `<span class="node ${hit[1]}">${hit[2]}</span>`;
  const folder = file.split('/').slice(0, 2).join('/');
  return `<span class="node app">${esc(folder)}</span>`;
}

// ── Sentences: markdown-lite, symbols resolved ─────────────────────────────────

interface SentenceToken {
  name: string;
  resolution: Resolution;
  /** "Open call": the line where the symbol is used. Inside the step's own function first — the traced call
   *  line when the stories carry one, else the first static reference; failing that, the first reference inside
   *  a function the stories saw call the step's own function (`how: 'caller'`, `fn` naming it), then inside
   *  another step's function of the same narrative (`how: 'sibling'`). Null when none of them uses it. */
  calledHere: { at: Location; how: 'traced' | 'static' | 'caller' | 'sibling'; fn?: string } | null;
  staticAt: Location | null;
  tracedAt: Location | null;
}

/** The line in the step's own function from which a narrated function was called, as the stories saw it: a hit at
 *  one of that function's own sites whose stack carries the step's function as a frame. */
function tracedCall(site: SourceSite, name: string, at: Location, stories: Story[], index: SourceIndex): Location | null {
  if (!layout.isApp(at.file)) return null;
  const narrated = [...index.sites(at.file).values()].some((s) => s.kind !== 'planned' && s.fn === name);
  if (!narrated) return null;
  for (const story of stories) {
    for (const h of story.hits) {
      if (h.kind === 'event' || h.site.file !== at.file || index.identity(h.site).fn !== name) continue;
      const frame = h.stack.find((f) => f.file === site.file && (f.fn ?? f.mappedFn) === site.fn);
      if (frame) return { file: frame.file, line: frame.line, column: frame.column };
    }
  }
  return null;
}

/** The first use of a symbol inside a function that called the step's own function, as the stories saw it: the
 *  first `src/` frame above a hit at the step's site that is not the step's function, each caller tried once.
 *  A sentence may tell what the caller set up for its step — a decision made on what its reader read — and
 *  the caller may be no step of its own. */
function callerCall(site: SourceSite, name: string, at: Location, stories: Story[], index: SourceIndex): { at: Location; fn: string } | null {
  const tried = new Set<string>();
  for (const story of stories) {
    for (const h of story.hits) {
      if (h.kind !== site.kind || h.site.file !== site.file || h.site.line !== site.line) continue;
      const caller = h.stack.find((f) => !(f.file === site.file && (f.fn ?? f.mappedFn) === site.fn));
      const fn = caller && layout.isApp(caller.file) ? caller.fn ?? caller.mappedFn : null;
      if (!caller || !fn) continue;
      const key = `${caller.file}#${fn}`;
      if (tried.has(key)) continue;
      tried.add(key);
      const use = index.useIn(caller.file, fn, name, at);
      if (use) return { at: use, fn };
    }
  }
  return null;
}

/** The first use of a symbol inside another step's function of the narrative, each function tried once. */
function siblingCall(site: SourceSite, name: string, at: Location, siblings: SourceSite[], index: SourceIndex): { at: Location; fn: string } | null {
  const tried = new Set([`${site.file}#${site.fn}`]);
  for (const sibling of siblings) {
    const key = `${sibling.file}#${sibling.fn}`;
    if (tried.has(key)) continue;
    tried.add(key);
    const use = index.useSite(sibling, name, at);
    if (use) return { at: use, fn: sibling.fn };
  }
  return null;
}

/** `**bold**` → <b>, `` `symbol` `` → a source link when it resolves (with an "Open call" alternate when a
 *  function of the narrative uses it), <code> otherwise; nothing else. `stories` lets a traced call line win over
 *  the static one; `siblings` are the sites of the narrative's steps, searched when the step's own function
 *  never uses the symbol. */
function sentenceHtml(sentence: string, site: SourceSite, index: SourceIndex, stories: Story[] = [], siblings: SourceSite[] = []): { html: string; tokens: SentenceToken[] } {
  const tokens: SentenceToken[] = [];
  const html = sentence.replace(/\*\*([^*]+)\*\*|`([^`]+)`|[^*`]+|[*`]/g, (m, bold?: string, code?: string) => {
    if (bold !== undefined) return `<b>${esc(bold)}</b>`;
    if (code === undefined) return esc(m);
    const resolution = index.resolve(site, code);
    if (!resolution.linked) {
      tokens.push({ name: code, resolution, calledHere: null, staticAt: null, tracedAt: null });
      return `<code>${esc(code)}</code>`;
    }
    const staticAt = index.useSite(site, code, resolution.at);
    const tracedAt = tracedCall(site, code, resolution.at, stories, index);
    const caller = tracedAt || staticAt ? null : callerCall(site, code, resolution.at, stories, index);
    const sibling = tracedAt || staticAt || caller ? null : siblingCall(site, code, resolution.at, siblings, index);
    const calledHere: SentenceToken['calledHere'] = tracedAt ? { at: tracedAt, how: 'traced' } : staticAt ? { at: staticAt, how: 'static' } : caller ? { ...caller, how: 'caller' } : sibling ? { ...sibling, how: 'sibling' } : null;
    tokens.push({ name: code, resolution, calledHere, staticAt, tracedAt });
    const label = calledHere?.fn ? `Open call (in ${calledHere.fn})` : 'Open call';
    return srcLink(resolution.at.file, resolution.at.line, resolution.at.column, code, '', calledHere ? [{ label, at: calledHere.at }] : []);
  });
  return { html, tokens };
}

// `--check` holds a sentence to the stack's `looksDeclared` (`stack.ts`): a token shaped like a name the
// language declares, that is not a watch key of the step, must have linked.

function watchKeys(step: Step): Set<string> {
  const keys = new Set<string>();
  for (const stop of step.stops) if (stop.watch && typeof stop.watch === 'object') for (const k of Object.keys(stop.watch)) keys.add(k);
  return keys;
}

// ── HTML ───────────────────────────────────────────────────────────────────────

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** A named alternate target of a source link, listed in the right-click menu beside the primary. */
interface Alternate {
  label: string;
  at: Location;
}

const sourceHref = (at: Location) => `${TO_ROOT}${at.file}#L${at.line}:${at.column}`;

/** One link mechanism: a primary target in `data-review-source-href`, zero or more named alternates in
 *  `data-review-alt-hrefs` (JSON `[{ label, href }]`), each resolved by `review-links.js` like the primary. */
function srcLink(file: string, line: number, column: number, text: string, extra = '', alternates: Alternate[] = []): string {
  const abs = join(ROOT, file);
  const alts = alternates.length ? ` data-review-alt-hrefs="${esc(JSON.stringify(alternates.map((a) => ({ label: a.label, href: sourceHref(a.at) }))))}"` : '';
  return `<a class="src"${extra} href="vscode://file/${abs}:${line}:${column}" data-review-source-href="${sourceHref({ file, line, column })}"${alts}>${esc(text)}</a>`;
}

/** Where the test file declares the case: the line the stack's title reader gives the test of that title, or 1. */
function testLine(file: string, test: string): number {
  const abs = join(ROOT, file);
  if (!existsSync(abs)) return 1;
  return titles.read(file, readFileSync(abs, 'utf8')).tests.find((t) => t.title === test)?.line ?? 1;
}

function testLink(story: Story, extra = ''): string {
  const line = testLine(story.file, story.test);
  return srcLink(story.file, line, 1, story.file.replace(/\.test\.tsx?$/, ''), extra);
}

function value(v: unknown): string {
  const flat = JSON.stringify(v);
  if (flat === undefined) return '<code>undefined</code>';
  if (flat.length <= 96) return `<code>${esc(flat)}</code>`;
  return `<pre class="val">${esc(JSON.stringify(v, null, 2))}</pre>`;
}

function stopHtml(stop: StoryHit, k: number, total: number): string {
  const watch = stop.watch && typeof stop.watch === 'object' ? Object.entries(stop.watch as Record<string, unknown>) : [];
  const rows = watch.map(([name, v]) => `<div class="kv"><span class="k">${esc(name)}</span>${value(v)}</div>`).join('');
  const head = total > 1 ? `<b>stop ${k}</b> <small>+${stop.atMs} ms</small>` : `<small>+${stop.atMs} ms</small>`;
  return `<div class="stop">${head}${rows || '<small>no watch</small>'}</div>`;
}

/** Where a page's links to the other pages go. */
interface PageLinks {
  /** From this page to a mechanism's page. */
  mechanism(n: Narrative): string;
  /** From this page to a product narrative's section. */
  product(n: Narrative): string;
  /** From this page to a feature's plan page. */
  plan(feature: string): string;
}

/** What one narrative's rendering needs beside the story. */
interface RenderContext {
  index: SourceIndex;
  narrative: Narrative;
  owner: Map<string, Narrative>;
  links: PageLinks;
  backlinks: BacklinkIndex;
  /** Which steps already carry their anchor (a step shown in two segments gets one); null in a variant, which anchors nothing. */
  anchored: Set<string> | null;
}

/** A step row; `stops` are the stops to show here (this segment's), numbered among all the step's stops. */
function stepHtml(step: Step, nested: boolean, story: Story, variants: Story[], ctx: RenderContext, stops: StoryHit[]): string {
  const { index } = ctx;
  const { site } = step;
  const reach = variants.filter((v) => v.hits.some((h) => h.kind === 'step' && index.identity(h.site).id === step.id)).length;
  const total = step.stops.length;
  const k = (s: StoryHit) => step.stops.indexOf(s) + 1;
  const shown = stops.slice(0, 3).map((s) => stopHtml(s, k(s), total)).join('');
  const folded = stops.length > 3
    ? `<details><summary>${stops.length - 3} more stop${stops.length > 4 ? 's' : ''}</summary>${stops.slice(3).map((s) => stopHtml(s, k(s), total)).join('')}</details>`
    : '';
  const anchor = ctx.anchored === null || ctx.anchored.has(step.id) ? '' : ` id="${esc(ctx.narrative.slug)}-step-${step.n}"`;
  ctx.anchored?.add(step.id);
  const sentence = sentenceHtml(step.sentence, step.source, index, narrativeStories(ctx.narrative), ctx.narrative.steps.map((s) => s.source));
  const named = markersFor(ctx.backlinks, stepKeys(step, sentence.tokens));
  return `
  <div class="step${nested ? ' nested' : ''}" data-step="${esc(step.id)}"${anchor}><b>${step.n}</b>
    <div>${chip(site.file)}${sentence.html}
      <span class="test">${srcLink(site.file, site.line, site.column, `${site.file}:${site.line}`)} in <code>${esc(site.fn ?? site.mappedFn ?? '(anonymous)')}</code> · ${testLink(story)} · ${total} stop${total === 1 ? '' : 's'}${stops.length < total ? ` (${stops.length} here)` : ''}${variants.length ? ` · reached by ${reach} of ${variants.length} variant${variants.length === 1 ? '' : 's'}` : ''} · <span class="cost">free</span></span></div>
    <div class="watch">${markersHtml(named)}Stop at ${srcLink(site.file, site.line, site.column, 'the call', ' data-watch')}.${shown}${folded}</div>
  </div>`;
}

const narrativeStories = (n: Narrative): Story[] => [n.canonical, ...n.variants].filter((s): s is Story => s !== null);

/** What the backlink index is asked about a step: its function, its file, the symbols its sentence links. */
function stepKeys(step: Step, tokens: SentenceToken[]): StepKeys {
  const linked: StepKeys['linked'] = [];
  for (const t of tokens) if (t.resolution.linked) linked.push({ key: `${t.resolution.at.file}#${t.name}`, name: t.name });
  return { fn: step.source.fn, file: step.source.file, linked };
}

const MARK_LABEL: Record<PageEntry['kind'], string> = { debt: 'debt', rule: 'rule', convention: 'convention' };

/** The marker: one click target, the entry's line in the markdown file through `data-review-source-href`, which
 *  `review-links.js` opens in VS Code (a browser link to the `.md` only ever shows plain text). */
function markerHtml(entry: PageEntry, via: Marker['via']): string {
  return `<span class="mark ${entry.kind}${via.tier === 'fn' ? '' : ' weak'}" data-via="${via.tier}">${srcLink(entry.page, entry.line, 1, `${MARK_LABEL[entry.kind]} · ${entry.title}`, ` title="${esc(entry.lead)} — ${esc(via.text)}"`)}</span>`;
}

/** The step's markers: the function- and file-tier ones visible, the sentence-tier ones (the noisy tier, an entry
 *  that names a symbol the sentence links) collapsed into one pill with a count that expands to the list. */
function markersHtml(named: ReturnType<typeof markersFor>): string {
  if (named.length === 0) return '';
  const shown = named.filter((m) => m.via.tier !== 'sentence');
  const folded = named.filter((m) => m.via.tier === 'sentence');
  const pill = folded.length
    ? `<details class="via-sentence"><summary>+${folded.length} via sentence</summary>${folded.map((m) => markerHtml(m.entry, m.via)).join(' ')}</details>`
    : '';
  return `<div class="named">${shown.map((m) => markerHtml(m.entry, m.via)).join(' ')}${pill}</div>`;
}

/** A mechanism page's "Named by": every page entry that names any of its steps, and which steps. */
function namedByHtml(mechanism: Narrative, ctx: RenderContext): string {
  const byEntry = new Map<PageEntry, { via: Marker['via']; steps: number[] }>();
  for (const step of mechanism.steps) {
    const { tokens } = sentenceHtml(step.sentence, step.source, ctx.index);
    for (const { entry, via } of markersFor(ctx.backlinks, stepKeys(step, tokens))) {
      const seen = byEntry.get(entry) ?? { via, steps: [] };
      seen.steps.push(step.n);
      byEntry.set(entry, seen);
    }
  }
  const rows = [...byEntry].map(([e, { via, steps }]) => `${markerHtml(e, via)}<small>${esc(e.lead)} — ${esc(via.text)} · step${steps.length === 1 ? '' : 's'} ${steps.join(', ')}</small>`);
  return `<small class="kicker">Named by</small><div class="narr-list">${rows.length ? rows.join('\n  ') : '<small>no debt entry, rule or convention names this mechanism\'s steps</small>'}</div>`;
}

/** The "rides on" row: a product story's hits at a mechanism's sites, collapsed, naming the mechanism's steps crossed. */
function ridesHtml(mechanism: Narrative, hits: StoryHit[], nested: boolean, ctx: RenderContext): string {
  const crossed = new Map<Step, number>();
  const beyond = new Map<string, number>();
  for (const h of hits) {
    const site = ctx.index.identity(h.site);
    const step = mechanism.steps.find((s) => s.id === site.id);
    if (step) crossed.set(step, (crossed.get(step) ?? 0) + 1);
    else beyond.set(site.fn + (ctx.index.siblings(site) > 1 ? `#${site.ordinal}` : ''), (beyond.get(site.fn) ?? 0) + 1);
  }
  const page = ctx.links.mechanism(mechanism);
  const steps = [...crossed].sort(([a], [b]) => a.n - b.n).map(([s, n]) => `<a href="${page}#${esc(mechanism.slug)}-step-${s.n}">step ${s.n}</a> <code>${esc(label(s, ctx.index))}</code>${n > 1 ? ` ×${n}` : ''}`).join(', ');
  const extra = beyond.size ? `${steps ? '; ' : ''}beyond its canonical: ${[...beyond].map(([l, n]) => `<code>${esc(l)}</code>${n > 1 ? ` ×${n}` : ''}`).join(', ')}` : '';
  return `
  <div class="rides${nested ? ' nested' : ''}" data-rides-on="${esc(mechanism.slug)}"><b>↳</b>
    <div><span class="node mech">rides on</span><a href="${page}">${esc(mechanism.title)}</a> — ${steps}${extra} <span class="test">${hits.length} hit${hits.length === 1 ? '' : 's'} from +${hits[0].atMs} ms · the stops are on the mechanism's page</span></div>
  </div>`;
}

/** The planned row: a `planned` site's hits in this segment, at the first — what this place will do once its
 *  piece of the feature's plan lands, linking the piece on the plan page. A removed site's row says so. */
function plannedRowHtml(site: SourceSite, hits: StoryHit[], nested: boolean, ctx: RenderContext): string {
  const p = site.planned!;
  const page = `${ctx.links.plan(p.feature)}#piece-${p.slug}`;
  const verb = p.change === 'removed' ? 'removed by' : 'planned';
  return `
  <div class="planned${nested ? ' nested' : ''}" data-planned="${esc(site.id)}"><b>⋯</b>
    <div><span class="node plan">${verb}</span><a href="${page}">${esc(p.feature)}#${esc(p.slug)}</a>${p.change === 'removed' ? ` — <code>${esc(site.fn)}</code> goes: ` : ': '}${sentenceHtml(p.sentence, site, ctx.index).html} <span class="test">${srcLink(site.file, site.line, site.column, `${site.file}:${site.line}`)} in <code>${esc(site.fn)}</code> · ${hits.length} hit${hits.length === 1 ? '' : 's'} from +${hits[0].atMs} ms</span></div>
  </div>`;
}

/** The "within" row of a run of nested steps, its claim checked over every stop of every grouped step. */
function withinHtml(group: Step[], key: string, stopsByStep: Map<Step, StoryHit[]>): string {
  const w = group[0].within!;
  const first = group[0];
  const last = group[group.length - 1];
  const range = group.length > 1 ? `Steps ${first.n} to ${last.n} run` : `Step ${first.n} runs`;
  const stops = group.flatMap((s) => stopsByStep.get(s) ?? []);
  const others = [...new Set(stops.map(callerKey).filter((k) => k !== key))].map((k) => (k === null ? `the test directly (no ${APP} frame)` : k.replace('::', ' · ')));
  const claim = others.length === 0
    ? `nothing else on this run calls them (${stops.length} stops checked)`
    : `on this run they are also called from ${others.map((o) => `<code>${esc(o)}</code>`).join(', ')} (${stops.length} stops checked)`;
  return `\n  <div class="within">${range} inside ${srcLink(w.file, w.line, 1, w.fn ?? w.file)} (<code>${esc(w.file)}</code>); ${claim}.</div>`;
}

type Item =
  | { kind: 'step'; step: Step; stops: StoryHit[] }
  | { kind: 'rides'; mechanism: Narrative; hits: StoryHit[] }
  | { kind: 'planned'; site: SourceSite; hits: StoryHit[] };

/** One segment's hits as rows, in the order they were first hit: a step with the segment's stops, a
 *  mechanism's sites collapsed into one "rides on" row at the first hit, or a planned site's hits as one
 *  planned row at the first. */
function deriveItems(segment: Segment, steps: Step[], ctx: RenderContext): Item[] {
  const items: Item[] = [];
  for (const hit of segment.hits) {
    const source = ctx.index.identity(hit.site);
    const id = source.id;
    if (hit.kind === 'planned') {
      const open = items.find((i): i is Item & { kind: 'planned' } => i.kind === 'planned' && i.site.id === id);
      if (open) open.hits.push(hit);
      else items.push({ kind: 'planned', site: source, hits: [hit] });
      continue;
    }
    const mechanism = ctx.owner.get(id);
    if (mechanism && mechanism !== ctx.narrative) {
      const open = items.find((i): i is Item & { kind: 'rides' } => i.kind === 'rides' && i.mechanism === mechanism);
      if (open) open.hits.push(hit);
      else items.push({ kind: 'rides', mechanism, hits: [hit] });
      continue;
    }
    const step = steps.find((s) => s.id === id);
    if (!step) throw new Error(`comprehension-render: ${id} fired in "${ctx.narrative.title}" but is no step of it — a site the canonical did not reach`);
    const open = items.find((i): i is Item & { kind: 'step' } => i.kind === 'step' && i.step === step);
    if (open) open.stops.push(hit);
    else items.push({ kind: 'step', step, stops: [hit] });
  }
  return items;
}

/** The rows of one segment; the within-row grouping runs over the step rows, a rides-on row between
 *  two grouped steps stays inside the group. */
function segmentStepsHtml(segment: Segment, steps: Step[], story: Story, variants: Story[], ctx: RenderContext): string {
  const items = deriveItems(segment, steps, ctx);
  const stopsByStep = new Map<Step, StoryHit[]>();
  for (const i of items) if (i.kind === 'step') stopsByStep.set(i.step, i.stops);
  const out: string[] = [];
  let openKey: string | null = null;
  items.forEach((item, i) => {
    if (item.kind === 'rides') {
      out.push(ridesHtml(item.mechanism, item.hits, openKey !== null, ctx));
      return;
    }
    if (item.kind === 'planned') {
      out.push(plannedRowHtml(item.site, item.hits, openKey !== null, ctx));
      return;
    }
    const key = nestingKey(item.step, steps);
    if (key !== null && key !== openKey) {
      const group: Step[] = [item.step];
      for (let j = i + 1; j < items.length; j += 1) {
        const next = items[j];
        if (next.kind !== 'step') continue;
        if (nestingKey(next.step, steps) !== key) break;
        group.push(next.step);
      }
      out.push(withinHtml(group, key, stopsByStep));
    }
    openKey = key;
    out.push(stepHtml(item.step, key !== null, story, variants, ctx, item.stops));
  });
  return out.join('');
}

/** Where an event written in a test is linked from: the OUTERMOST frame still under `tests/` — the line in the
 *  `it` body that called the helper (`mount`, `renderList`, …), so the reader sees the cause in its case — with
 *  the helper's own site as the "via" alternate. An event called directly in the case has no helper to name. */
function eventFrames(e: StoryHit): { primary: StoryFrame; via: StoryFrame | null } {
  if (!layout.isTest(e.site.file)) return { primary: e.site, via: null };
  const outer = [...e.stack].reverse().find((f) => layout.isTest(f.file));
  return outer ? { primary: outer, via: e.site } : { primary: e.site, via: null };
}

function eventHtml(segment: Segment, ctx: RenderContext, n: number): string {
  const e = segment.event;
  if (e === null) {
    return `\n  <div class="event"><b>·</b><div><span class="node world">before any event</span>${segment.hits.length} step hit${segment.hits.length === 1 ? '' : 's'} fired before anything was said to cause them — a gap: narrate the cause as an <code>event</code>.</div></div>`;
  }
  const { index } = ctx;
  const watch = e.watch && typeof e.watch === 'object' ? Object.entries(e.watch as Record<string, unknown>) : [];
  const rows = watch.map(([name, v]) => `<div class="kv"><span class="k">${esc(name)}</span>${value(v)}</div>`).join('');
  const silent = EXPECTS_SILENCE.test(e.sentence);
  const after = segment.hits.length === 0
    ? (silent ? ` · <span class="quiet">no step followed, as the sentence says</span>` : ` · <span class="none">dead action: no step followed</span>`)
    : (silent ? ` · <span class="none">${segment.hits.length} step hits followed a cause that says nothing follows</span>` : '');
  const { primary, via } = eventFrames(e);
  const alternates: Alternate[] = via ? [{ label: `via ${via.fn ?? via.mappedFn ?? '(anonymous)'}`, at: { file: via.file, line: via.line, column: via.column } }] : [];
  const inFn = via ? 'the case' : (primary.fn ?? primary.mappedFn ?? '(anonymous)');
  return `\n  <div class="event" data-event="${esc(index.identity(e.site).id)}"><b>${n}</b>
    <div><span class="node ${isActor(e.sentence) ? 'actor' : 'world'}">${esc(actor(e.sentence))}</span>${sentenceHtml(e.sentence, index.identity(e.site), index).html}
      <span class="test">${srcLink(primary.file, primary.line, primary.column, `${primary.file}:${primary.line}`, '', alternates)} in <code>${esc(inFn)}</code> · +${e.atMs} ms${after}</span></div>
    <div class="watch">${rows || '<small>no watch</small>'}</div>
  </div>`;
}

/** The story as segments: each cause, then the steps it set off. */
function stepsHtml(story: Story, steps: Step[], variants: Story[], ctx: RenderContext): string {
  const segments = deriveSegments(story);
  let n = 0;
  return segments.map((segment) => {
    if (segment.event) n += 1;
    return `${eventHtml(segment, ctx, n)}\n  <div class="segment">${segmentStepsHtml(segment, steps, story, variants, ctx)}\n  </div>`;
  }).join('');
}

/** Whether a story passes through any of the given sites. */
function crosses(story: Story, ids: ReadonlySet<string>, index: SourceIndex): boolean {
  return story.hits.some((h) => h.kind === 'step' && ids.has(index.identity(h.site).id));
}

/** The product-step hits of a story and its hits on each mechanism, for the header line. */
function hitCounts(story: Story, ctx: RenderContext): { steps: number; mechanisms: Map<Narrative, number> } {
  let steps = 0;
  const mechanisms = new Map<Narrative, number>();
  for (const h of story.hits) {
    if (h.kind !== 'step') continue;
    const m = ctx.owner.get(ctx.index.identity(h.site).id);
    if (m && m !== ctx.narrative) mechanisms.set(m, (mechanisms.get(m) ?? 0) + 1);
    else steps += 1;
  }
  return { steps, mechanisms };
}

function variantHtml(story: Story, ctx: RenderContext): string {
  const { index, narrative, owner } = ctx;
  const exclude = new Set([...owner].filter(([, m]) => m !== narrative).map(([id]) => id));
  const steps = deriveSteps(story, index, exclude);
  const missed = narrative.steps.filter((c) => !steps.some((s) => s.id === c.id));
  const beyond = steps.filter((s) => !narrative.stepIds.has(s.id));
  // The variant's own steps are numbered as the canonical numbers them, so the two read alike.
  for (const s of steps) s.n = narrative.steps.find((c) => c.id === s.id)?.n ?? s.n;
  const reached = steps.map((s) => `${label(s, index)} ×${s.stops.length}`).join(', ');
  const events = story.hits.filter((h) => h.kind === 'event').length;
  const counts = hitCounts(story, ctx);
  const rides = [...counts.mechanisms].map(([m, n]) => `${n} on ${m.title}`).join(', ');
  return `
<details class="fold">
  <summary>${esc(story.test)} <small>— ${events} event${events === 1 ? '' : 's'} · ${counts.steps} step hits${rides ? ` · rides on: ${esc(rides)}` : ''} · ${esc(reached)}${missed.length ? ` · <span style="color:#b45309">not reached: ${esc(missed.map((m) => label(m, index)).join(', '))}</span>` : ' · every canonical step reached'}${beyond.length ? ` · <span style="color:#6d28d9">beyond the canonical: ${esc(beyond.map((b) => label(b, index)).join(', '))}</span>` : ''}</small></summary>
  <div class="fbody">
    <p style="font-size:.8rem;color:var(--muted)">pinned by ${testLink(story)} · ${story.state ?? 'unknown'} in ${story.durationMs ?? '?'} ms</p>
    <div class="lane-head"><span>step</span><span>what happens, who calls it, and the rule it enacts</span><span>where to stop, what to check</span></div>
    ${stepsHtml(story, steps, [], { ...ctx, anchored: null })}
  </div>
</details>`;
}

/** The other tests, by file, that cross a narrative's sites — the raw material of the coverage index. */
function elsewhereHtml(narrative: Narrative, stories: Story[], index: SourceIndex): string {
  const own = new Set([narrative.canonical, ...narrative.variants]);
  const elsewhere = new Map<string, number>();
  for (const s of stories) if (!own.has(s) && !s.narrative && crosses(s, narrative.stepIds, index)) elsewhere.set(s.file, (elsewhere.get(s.file) ?? 0) + 1);
  if (elsewhere.size === 0) return '';
  const total = [...elsewhere.values()].reduce((a, b) => a + b, 0);
  const rows = [...elsewhere].sort().map(([file, n]) => `${srcLink(file, 1, 1, file)} <small style="display:inline">· ${n} test${n === 1 ? '' : 's'}</small>`).join('<br>');
  const list = elsewhere.size > 8 ? `<details><summary>${elsewhere.size} files</summary>${rows}</details>` : rows;
  return `<small class="kicker">Also crossed by</small><div class="narr-list">${list}<small>${total} tests in ${elsewhere.size} files pass through at least one step of this narrative; their stories are written and not rendered.</small></div>`;
}

function narrativeHtml(narrative: Narrative, stories: Story[], narratives: Narrative[], index: SourceIndex, links: PageLinks, backlinks: BacklinkIndex): string {
  const { canonical, variants, steps } = narrative;
  if (!canonical) {
    return `<section class="narr" id="${esc(narrative.slug)}"><header><strong>${esc(narrative.title)}</strong><small>no story yet for its canonical case${narrative.canonicalTest ? ` "${esc(narrative.canonicalTest)}"` : ''} — run <code>npm run comprehension</code> or <code>${esc(typed(config.commands.tests, narrative.file))}</code></small></header></section>`;
  }
  const ctx: RenderContext = { index, narrative, owner: ownership(narratives), links, backlinks, anchored: new Set() };
  const counts = hitCounts(canonical, ctx);
  const rides = [...counts.mechanisms].map(([m, n]) => `${n} on <a href="${links.mechanism(m)}">${esc(m.title)}</a>`).join(', ');
  const plannedRows = deriveSegments(canonical).reduce((n, s) => n + new Set(s.hits.filter((h) => h.kind === 'planned').map((h) => index.identity(h.site).id)).size, 0);
  return `
<section class="narr" id="${esc(narrative.slug)}" data-narrative>
  <header>
    <strong>${esc(narrative.title)}</strong>
    <small>present tense · one screen · pinned by ${testLink(canonical, ' data-narrative-test')}, "${esc(canonical.test)}" · the data is the test's · ${deriveSegments(canonical).filter((s) => s.event).length} events, ${counts.steps} hits over ${steps.length} steps${rides ? `, ${rides}` : ''}${plannedRows ? `, ${plannedRows} planned row${plannedRows === 1 ? '' : 's'}` : ''} in ${canonical.durationMs ?? '?'} ms</small>
  </header>
  <div class="lane-head"><span>step</span><span>what happens, who calls it, and the rule it enacts</span><span>where to stop, what to check</span></div>
${stepsHtml(canonical, steps, variants, ctx)}
</section>
${variants.length ? `<small class="kicker">Variants — the other cases of the same narrative, as they ran</small>${variants.map((v) => variantHtml(v, ctx)).join('')}` : ''}
${narrative.kind === 'mechanism' ? `${namedByHtml(narrative, ctx)}\n${exercisedByHtml(narrative, narratives, index, links)}` : ''}
${elsewhereHtml(narrative, stories, index)}`;
}

/** A mechanism page's "Exercised by": every other narrative whose stories crossed any of its sites. */
function exercisedByHtml(mechanism: Narrative, narratives: Narrative[], index: SourceIndex, links: PageLinks): string {
  const rows: string[] = [];
  for (const n of narratives) {
    if (n === mechanism) continue;
    const stories = [n.canonical, ...n.variants].filter((s): s is Story => s !== null);
    const crossing = stories.filter((s) => crosses(s, mechanism.stepIds, index));
    if (crossing.length === 0) continue;
    const stepsCrossed = new Set<number>();
    for (const s of crossing) for (const h of s.hits) if (h.kind === 'step') {
      const step = mechanism.steps.find((m) => m.id === index.identity(h.site).id);
      if (step) stepsCrossed.add(step.n);
    }
    rows.push(`<a href="${n.kind === 'product' ? links.product(n) : links.mechanism(n)}"><strong>${esc(n.title)}</strong></a><small>${n.kind} · ${crossing.length} of ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'} cross${crossing.length === 1 ? 'es' : ''} steps ${[...stepsCrossed].sort((a, b) => a - b).join(', ')} of this mechanism</small>`);
  }
  return `<small class="kicker">Exercised by</small><div class="narr-list">${rows.length ? rows.join('\n  ') : '<small>no product narrative crosses this mechanism yet</small>'}</div>`;
}

/** A product narrative page's "Rides on": one line per mechanism its canonical story crossed. */
function ridesOnHtml(products: Narrative[], narratives: Narrative[], index: SourceIndex, links: PageLinks): string {
  const owner = ownership(narratives);
  const lines: string[] = [];
  for (const m of narratives) {
    if (m.kind !== 'mechanism') continue;
    const by: string[] = [];
    for (const p of products) {
      if (!p.canonical) continue;
      const crossed = new Set<Step>();
      for (const h of p.canonical.hits) {
        if (h.kind !== 'step') continue;
        const id = index.identity(h.site).id;
        if (owner.get(id) !== m) continue;
        crossed.add(m.steps.find((s) => s.id === id)!);
      }
      if (crossed.size) by.push(`${esc(p.title)} crosses step${crossed.size === 1 ? '' : 's'} ${[...crossed].map((s) => s.n).sort((a, b) => a - b).join(', ')} of ${m.steps.length}`);
    }
    if (by.length) lines.push(`<li><a href="${links.mechanism(m)}">${esc(m.title)}</a>: ${esc(m.summary)} — ${by.join('; ')}.</li>`);
  }
  return lines.length
    ? `<ul class="rules">\n  ${lines.join('\n  ')}\n</ul>`
    : `<p><small>No mechanism narrative is crossed by a product story yet.</small></p>`;
}

/** The pages' one stylesheet, hand-written beside them and inlined so a page opens from file://. */
function pageStyle(): string {
  if (!existsSync(PAGE_CSS)) throw new Error(`comprehension-render: ${relative(ROOT, PAGE_CSS)} is missing — the pages' stylesheet lives there`);
  return readFileSync(PAGE_CSS, 'utf8');
}


/** How the links of a narrative page and a mechanism page are used: the same on every page, so said once. */
const LINK_HINT = '<p style="font-size:.8rem;color:var(--muted);margin:.2rem 0 .6rem">A dotted link opens VS Code at the line; right-click it for the diff against <code>main</code>, or, on a test, to debug that case. A narrative\'s "▶ debug this narrative" runs its test under the debugger: set breakpoints at the watch points you want first, then continue from one stop to the next beside the steps.</p>';

function pageHtml(title: string, crumb: string, body: string, footerNote: string, extraStyle = ''): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(config.name)} comprehension — ${esc(title)} (generated)</title>
<style>
${pageStyle()}${extraStyle}</style>
</head>
<body>

<p class="crumb">${HUB ? `${HUB} / ` : ''}${crumb} · ${renderStamp()}</p>
${body}
<footer>${esc(config.name)} comprehension · ${HUB ? `${HUB} · ` : ''}generated by <code>${esc(SELF)}</code> from the stories the test run wrote under <code>${esc(STORIES)}/</code> · ${footerNote}</footer>
<script src="${TO_DOCS}review-links.js" defer></script>
</body>
</html>
`;
}

const PRODUCT_LINKS: PageLinks = {
  mechanism: (m) => `../mechanisms/${m.slug}.html`,
  product: (p) => `${p.slug}.html`,
  plan: (feature) => `../plans/${feature}.html`,
};
const MECHANISM_LINKS: PageLinks = {
  mechanism: (m) => `${m.slug}.html`,
  product: (p) => `../narratives/${p.slug}.html`,
  plan: (feature) => `../plans/${feature}.html`,
};
const PLAN_LINKS: PageLinks = {
  mechanism: (m) => `../mechanisms/${m.slug}.html`,
  product: (p) => `../narratives/${p.slug}.html`,
  plan: (feature) => `${feature}.html`,
};

// ── Plans: a feature's tagged sites, with what the stories observed at them ──────
// The model, the scans and the order the pieces are told in are `plan.ts`; here is what needs the
// source reader, the stories and the disk, and the page.

/** The folders a planned site can stand in. */
const SCAN_ROOTS = config.source.scan;
/** The files a planned site can stand in, by extension. */
export const SCANNED = /\.(?:[cm]?[jt]sx?|py|css|sql|md|html|ya?ml|toml|sh)$/;

/** A plan's sites with no `planned` call: the `@planned` comments and the tagged tests to write. */
export interface PlanSources {
  statics: StaticSite[];
  todos: PlanTodo[];
  /** The `todo` cases of the journey tests: the spec's criteria nobody has written yet. */
  journeyCases: JourneyCase[];
}

/** Read from the working tree: the tracked files and the new ones git does not ignore, so never `node_modules`
 *  nor a generated page — a proposed migration is a site before its first commit. */
export function readPlanSources(): PlanSources {
  const listed = execFileSync('git', ['ls-files', '-z', '-co', '--exclude-standard', '--', ...SCAN_ROOTS], { cwd: ROOT, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  const files = [...new Set(listed.split('\0'))].filter((f) => SCANNED.test(f) && existsSync(join(ROOT, f))).sort();
  const texts = new Map<string, string>();
  const text = (f: string) => texts.get(f) ?? texts.set(f, readFileSync(join(ROOT, f), 'utf8')).get(f)!;
  // The files the title reader will be asked for, said at once: a reader that costs a process answers in one.
  titles.prime?.(files.filter((f) => text(f).includes('@planned') || layout.isJourneyTest(f) || (layout.isTestFile(f) && text(f).includes('#'))).map((file) => ({ file, text: text(file) })));
  // Where server steps are declared, each naming the test of the real server that is its truth.
  const truths = files.filter((f) => layout.declaresTruths(f)).map(text).join('\n');
  const statics: StaticSite[] = [];
  const todos: PlanTodo[] = [];
  const journeyCases: JourneyCase[] = [];
  for (const f of files) {
    const t = text(f);
    statics.push(...scanPlannedComments(f, t, titles));
    if (layout.isJourneyTest(f)) journeyCases.push(...scanJourneyCases(f, t, titles));
    // A written test counts when its tag names a feature in flight: titles such as `auth#login: …` open the same way.
    if (layout.isTestFile(f)) todos.push(...scanTodos(f, t, titles)
      .filter((todo) => !todo.written || existsSync(join(ROOT, featureFolder(todo.feature))))
      .map((todo) => ({ ...todo, tier: layout.tierOf(f, truths) })));
  }
  return { statics, todos, journeyCases };
}

/** The test files that hold a reproduction of a plan, each with the command that runs it once (`testCommandOf`):
 *  null for one no tool runs, left to a run by hand. */
export function reproductionFiles(sources: PlanSources): Array<{ file: string; command: string[] | null }> {
  return [...new Set(sources.todos.filter((t) => t.reproduction).map((t) => t.file))].sort().map((file) => ({ file, command: testCommandOf(file) }));
}

/** One run of the reproductions: the command as typed, its files following, and what it printed. */
interface ReproductionRun { command: string; ok: boolean; output: string }

/**
 * Runs the reproductions the plans hold, before a page is drawn or a plan checked: a bug's evidence is what its
 * reproductions saw, and a page drawn from whichever run came last says "no run" of a test nobody ran lately.
 * Whole files, a run per command and no option: a file's stories are then complete, and a failure is worded the
 * same at each render. A run that exits with an error is returned with what it printed: a reproduction that
 * passes fails it, since its failure is expected strictly, and so does a server its command needs and finds down.
 */
export function runReproductions(files: Array<{ file: string; command: string[] | null }>): { ran: number; failed: ReproductionRun[] } {
  const byCommand = new Map<string[], string[]>();
  for (const { file, command } of files) if (command) byCommand.set(command, [...(byCommand.get(command) ?? []), file]);
  const failed: ReproductionRun[] = [];
  for (const [[program, ...args], ofCommand] of byCommand) {
    const done = spawnSync(program, [...args, ...ofCommand], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    const run = { command: typed([program, ...args], ...ofCommand), ok: done.status === 0, output: `${done.stdout ?? ''}${done.stderr ?? ''}${done.error ? String(done.error) : ''}` };
    if (!run.ok) failed.push(run);
  }
  return { ran: [...byCommand.values()].flat().length, failed };
}

/** What a run of the reproductions that did not end well says, in a few lines. */
const reproductionsFailed = (run: ReproductionRun) => `the reproductions did not run as expected — ${run.command}\n${run.output.trim().split('\n').slice(-12).map((line) => `    ${line}`).join('\n')}`;

/** A line that stands on the declaration under it: a decorator, an attribute, a comment. The line above a
 *  nested function is often its enclosing function's own code, so nothing else is taken for the function's. */
const STANDS_ON = /^\s*(?:@|#|\/\/|\/\*|\*|\[)/;

/**
 * The functions of a file as a change is read into them (`FunctionLines`): the source index's, as the code
 * stands, each with the lines that stand directly on it (`STANDS_ON`) — a decorator is where a change of a
 * function is often written. None for a file the stack gives no function of.
 */
function functionLines(file: string, index: SourceIndex): FunctionLines[] {
  const functions = existsSync(join(ROOT, file)) ? index.functions(file) : [];
  if (functions.length === 0) return [];
  const text = readFileSync(join(ROOT, file), 'utf8').split('\n');
  return functions.map((f) => {
    let from = f.line;
    while (from > 1 && STANDS_ON.test(text[from - 2] ?? '')) from -= 1;
    return { ...f, from };
  });
}

/**
 * How many lines a function holds that it did not hold at the commit of an approval, whose difference `since`
 * reads: what tells a place built from one that was skipped or undone (`FeatureDocs.gained`). Null where the
 * index places no single function of that name, and where git cannot read that commit.
 */
export function gainedSince(since: HunkReader, index: SourceIndex): NonNullable<FeatureDocs['gained']> {
  return (file, fn) => {
    const named = functionLines(file, index).filter((f) => f.fn === fn);
    const hunks = named.length === 1 ? since(file) : null;
    if (named.length !== 1 || !hunks) return null;
    const [{ from, endLine }] = named;
    return hunks.reduce((n, h) => n + (h.now ? Math.max(0, Math.min(h.now[1], endLine) - Math.max(h.now[0], from) + 1) : 0), 0);
  };
}

/** What a file changed at no place of a plan since the commit of its approval (`FeatureDocs.away`,
 *  `changedAway`): the difference is git's (`since`), the functions the source index's, both as the code
 *  stands at this render. */
export function awaySince(since: HunkReader, feature: string, index: SourceIndex): NonNullable<FeatureDocs['away']> {
  return (file, named) => {
    const hunks = since(file);
    return hunks ? changedAway(file, hunks, feature, named, functionLines(file, index)) : [];
  };
}

/** What a feature folder holds beside its sites: `plan.md` and `spec.md`, parsed. */
function featureDocs(feature: string): FeatureDocs {
  const dir = featureFolder(feature);
  const read = (name: string) => {
    const file = `${dir}/${name}`;
    return existsSync(join(ROOT, file)) ? { file, intent: parseIntent(readFileSync(join(ROOT, file), 'utf8'), file) } : null;
  };
  const file = `${dir}/${APPROVED_FILE}`;
  const approved = existsSync(join(ROOT, file)) ? { file, baseline: JSON.parse(readFileSync(join(ROOT, file), 'utf8')) as PlanBaseline } : null;
  return {
    folderExists: existsSync(join(ROOT, dir)), plan: read('plan.md'), spec: read('spec.md'),
    approved,
    feedback: readFeedback(feature),
    commits: readPieceCommits(feature, approved?.baseline.base ?? null, ROOT, titles, layout),
    pointed: (repository, slug) => pointerTarget(feature, repository, slug),
  };
}

/** What another repository's plan of the same feature says of a piece, read from its checkout's files: its
 *  `plan.md` and its approval. Nothing of that repository is run. Null when the configuration names no
 *  checkout of it, or none is there: another machine may hold this repository alone. */
function pointerTarget(feature: string, repository: string, slug: string): PointerTarget | null {
  const at = config.repositories?.[repository];
  const root = at === undefined ? null : resolve(ROOT, at);
  if (root === null || !existsSync(root)) return null;
  // Its documents' folder is its own configuration's.
  const theirs = join(root, CONFIG_FILE);
  const docs = existsSync(theirs) ? (JSON.parse(readFileSync(theirs, 'utf8')) as { docs?: string }).docs ?? config.docs : config.docs;
  const source = join(root, docs, 'features', feature, 'plan.md');
  const absent = { statement: null, approvedOn: null, source, line: 1 };
  if (!existsSync(source)) return absent;
  const section = planDocOf(parseIntent(readFileSync(source, 'utf8'), source), source).sections.find((s) => s.piece === slug);
  if (!section) return absent;
  const approval = join(dirname(source), APPROVED_FILE);
  const baseline = existsSync(approval) ? JSON.parse(readFileSync(approval, 'utf8')) as PlanBaseline : null;
  const approved = baseline?.units.some((u) => u.kind === 'piece' && u.name === `#${slug}`) ?? false;
  return { statement: pieceDocOf(section, source).what, approvedOn: approved ? baseline!.approvedOn : null, source, line: section.line };
}

/** The reviewer's answers, written from the pages by the local app (`npm run comprehension`); deleted by an approval. */
const FEEDBACK_FILE = 'plan-feedback.json';
const feedbackPath = (feature: string) => join(ROOT, featureFolder(feature), FEEDBACK_FILE);
const readFeedback = (feature: string): PlanFeedback => (existsSync(feedbackPath(feature)) ? JSON.parse(readFileSync(feedbackPath(feature), 'utf8')) as PlanFeedback : {});

/** One answer from a page: approved, or not, with what should change. It replaces the answer the item had. */
export function saveFeedback(feature: string, answer: { key: string; unit: string; what: string; verdict: string; note: string }): void {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(feature) || !existsSync(join(ROOT, featureFolder(feature), 'plan.md'))) throw new Error(`no plan.md for "${feature}"`);
  if (answer.verdict !== 'approved' && answer.verdict !== 'refused') throw new Error(`"${answer.verdict}" is no verdict: approved, or refused`);
  if (!/^[0-9a-f]{8}$/.test(answer.key)) throw new Error('the item key is missing');
  if (answer.verdict === 'refused' && answer.note.trim() === '') throw new Error('an item that is not approved says what should change');
  const all = readFeedback(feature);
  all[answer.key] = { unit: answer.unit, what: answer.what, verdict: answer.verdict, note: answer.note.trim(), at: new Date().toISOString() };
  writeFileSync(feedbackPath(feature), `${JSON.stringify(all, null, 2)}\n`);
}

/** The approval given from the page: every edit of the plan as it stands was answered "approved". Then it is
 *  `approve`, which refuses while a `To confirm:` stands in `plan.md`: a question answered there is still one
 *  until the agent has written the answer as a statement. */
export function approveFromPage(feature: string, source: SourceReader = openSource()): { file: string; units: number; cleared: number } {
  const index = new SourceIndex(source);
  const stories = readStories();
  index.realign(stories);
  const plan = derivePlans(stories, deriveNarratives(stories, index), index).find((p) => p.feature === feature);
  if (!plan) throw new Error(`no plan for "${feature}"`);
  const open = reviewItems(plan).filter((i) => plan.feedback[i.key]?.verdict !== 'approved');
  if (open.length) throw new Error(`${open.length} item${open.length === 1 ? ' is' : 's are'} not approved: ${open.map((i) => `${i.unit} — ${i.what}`).join('; ')}`);
  return approve(feature, source);
}

/** The approved plan of a feature, in its folder: deleted with it at the archive. */
const APPROVED_FILE = 'plan.approved.json';

/**
 * Approves a feature's plan as it stands: writes its snapshot, with the commit it was read on, and takes the
 * `Changed:` paragraphs off `plan.md` — they told the reviewer what moved, and it is approved. Refuses, with
 * nothing written, while a point is still to confirm (an approval with a question open approves nothing) and
 * while the plan fails the check: what is approved is a plan that passes. Run on the reviewer's word.
 */
export function approve(feature: string, source: SourceReader = openSource()): { file: string; units: number; cleared: number; answered: string[] } {
  const index = new SourceIndex(source);
  const stories = readStories();
  index.realign(stories);
  const planOf = () => derivePlans(stories, deriveNarratives(stories, index), index).find((p) => p.feature === feature);
  const read = planOf();
  if (!read?.doc) throw new Error(`comprehension-render --approve ${feature}: ${read ? `${featureFolder(feature)}/plan.md does not exist` : 'no planned site names it'}`);
  // Refused before anything is written: a failed approval leaves `plan.md` as the reviewer read it.
  const refusal = approvalRefusal(read);
  if (refusal) throw new Error(`comprehension-render --approve ${feature}: ${refusal}`);
  const md = join(ROOT, read.doc.file);
  // A point answered "Yes, as proposed" on the page is written in as its proposal, and the plan read again: the
  // approval holds the line.
  const answered = writeAcceptedAnswers(readFileSync(md, 'utf8'), read);
  if (answered.applied.length) writeFileSync(md, answered.text);
  const plan = answered.applied.length ? planOf()! : read;
  const lines = readFileSync(md, 'utf8').split('\n');
  // A `Changed:` paragraph runs to the next blank line; the blank line before it goes with it.
  const kept: string[] = [];
  let cleared = 0;
  for (let i = 0; i < lines.length; i += 1) {
    if (!lines[i].startsWith('Changed:')) {
      kept.push(lines[i]);
      continue;
    }
    cleared += 1;
    while (i + 1 < lines.length && lines[i + 1].trim() !== '') i += 1;
    if (kept.length && kept[kept.length - 1].trim() === '') kept.pop();
  }
  if (cleared) writeFileSync(md, kept.join('\n'));
  const baseline: PlanBaseline = {
    feature,
    base: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(),
    approvedOn: new Date().toISOString().slice(0, 10),
    units: plan.snapshot.units,
  };
  // What each reproduction tells today is kept: once its piece is built, no run tells it again.
  const chains = Object.fromEntries(plan.pieces.map((piece) => [piece.slug, chainsToFreeze(piece)] as const).filter(([, kept]) => kept.length > 0));
  if (Object.keys(chains).length) baseline.chains = chains;
  // Where each place lands today is kept too: once it is code, no story crosses a `planned` call there.
  const told = deriveNarratives(stories, index).filter((n) => n.canonical).map((n) => ({ title: n.title, steps: n.steps.map((step) => `${label(step, index)} — ${step.sentence}`) }));
  const landings = Object.fromEntries(plan.pieces.map((piece) => [piece.slug, landingsToFreeze(piece, told)] as const).filter(([, kept]) => kept.length > 0));
  if (Object.keys(landings).length) baseline.landings = landings;
  const ids = Object.fromEntries(plan.pieces.map((piece) => [piece.slug, idsToKeep(piece)] as const).filter(([, kept]) => Object.keys(kept).length > 0));
  if (Object.keys(ids).length) baseline.ids = ids;
  const file = `${featureFolder(feature)}/${APPROVED_FILE}`;
  writeFileSync(join(ROOT, file), `${JSON.stringify(baseline, null, 2)}\n`);
  // The answers were on the plan that is now approved: the round is closed.
  if (existsSync(feedbackPath(feature))) rmSync(feedbackPath(feature));
  return { file, units: baseline.units.length, cleared, answered: answered.applied };
}

/**
 * The canonical step a planned call's change lands in, and how that is told (`PlanSite.crossedBy`), the first
 * of these that tells:
 *  - `in`: the call sits in a step's own function — when the function holds several steps, the one whose
 *    `narrate` stands nearest the call;
 *  - `after`: the call's function had, under the same cause, already called down to a step (the reader after
 *    its decision): the change is met right after that step;
 *  - `via`: it sits in a helper a step's sentence names in backticks;
 *  - `after`: any step ran before it under the same cause (a child component React renders, code reached
 *    across an `await`);
 *  - `via`: the nearest frame above the hit is a step's function.
 * Null when none tells.
 */
function landsIn(story: Story, at: number, site: SourceSite, n: Narrative, index: SourceIndex): { step: Step; how: 'in' | 'via' | 'after' } | null {
  const own = n.steps.filter((s) => s.source.file === site.file && s.source.fn === site.fn);
  if (own.length) return { step: own.reduce((a, b) => (Math.abs(b.source.line - site.line) < Math.abs(a.source.line - site.line) ? b : a)), how: 'in' };
  const before: Array<{ step: Step; hit: StoryHit }> = [];
  for (let k = at - 1; k >= 0; k -= 1) {
    const hit = story.hits[k];
    if (hit.kind === 'event') break;
    if (hit.kind !== 'step') continue;
    const id = index.identity(hit.site).id;
    const step = n.steps.find((s) => s.id === id);
    if (step) before.push({ step, hit });
  }
  const inside = before.find(({ hit }) => hit.stack.some((f) => f.file === site.file && (f.fn ?? f.mappedFn) === site.fn));
  if (inside) return { step: inside.step, how: 'after' };
  const named = n.steps.find((s) => s.sentence.includes(`\`${site.fn}\``));
  if (named) return { step: named, how: 'via' };
  if (before.length) return { step: before[0].step, how: 'after' };
  for (const f of story.hits[at].stack) {
    const step = n.steps.find((s) => s.source.file === f.file && s.source.fn === (f.fn ?? f.mappedFn));
    if (step) return { step, how: 'via' };
  }
  return null;
}

/** One plan per feature a site names. The `planned` calls come from the source index, what crosses them from the stories;
 *  the comments and the todos from `sources`. */
export function derivePlans(stories: Story[], narratives: Narrative[], index: SourceIndex, sources: PlanSources = readPlanSources()): Plan[] {
  const sites: PlanSite[] = index.plannedSites().map((site) => {
    const p = site.planned!;
    const crossedBy: PlanSite['crossedBy'] = [];
    const reachedBy = new Map<string, string[]>();
    const seenBy: PlanSite['seenBy'] = [];
    for (const story of stories) {
      const here = (h: StoryHit) => h.kind === 'planned' && index.identity(h.site).id === site.id;
      const at = story.hits.findIndex(here);
      if (at < 0) continue;
      reachedBy.set(story.file, [...(reachedBy.get(story.file) ?? []), story.test]);
      // A bug's evidence is what a test that fails today saw at the place, every time it crossed it.
      if (story.reproduction) seenBy.push({ file: story.file, test: story.test, at, crossings: story.hits.filter(here).map((h) => ({ watch: h.watch, expect: h.expect ?? null })) });
      const n = narratives.find((x) => x.canonical === story);
      if (!n) continue;
      const lands = landsIn(story, at, site, n, index);
      crossedBy.push({ narrative: n.title, at, step: lands ? { n: lands.step.n, label: label(lands.step, index), how: lands.how } : null });
    }
    return {
      feature: p.feature, slug: p.slug, id: site.id, file: site.file, line: site.line, column: site.column, fn: site.fn,
      change: p.change, ...(p.place ? { place: p.place } : {}), sentence: p.sentence, signature: p.signature, expect: p.expect ?? null, distinct: p.distinct ?? [], seenBy,
      crossedBy, reachedBy: [...reachedBy].sort(([a], [b]) => a.localeCompare(b)).map(([file, titles]) => ({ file, tests: titles.length, titles })),
    };
  });
  // A reproduction's last run: its state and how it failed, from its story.
  const todos = sources.todos.map((todo) => {
    const story = todo.reproduction ? stories.find((s) => isStoryOf(todo, s)) : undefined;
    return story ? { ...todo, run: { state: story.state, failure: story.failure ?? null } } : todo;
  });
  return assemblePlans({
    sites,
    statics: sources.statics,
    todos,
    journeyCases: sources.journeyCases,
    narratives: narratives.filter((n) => n.canonical).map((n) => ({ title: n.title, kind: n.kind, steps: n.steps.map((step) => `${label(step, index)} — ${step.sentence}`), stepPlaces: n.steps.map((step) => ({ file: step.source.file, fn: step.source.fn })) })),
    // A place of an approved plan is read by its function: what it gained since the approval. So is what a
    // lot changed beside its places.
    docs: (feature) => {
      const docs = featureDocs(feature);
      const base = docs.approved?.baseline.base;
      if (!base) return docs;
      // Made here, for this render: the working tree moves between two renders of the local app.
      const since = hunkReader(base, ROOT);
      return { ...docs, gained: gainedSince(since, index), away: awaySince(since, feature, index) };
    },
    layout,
  });
}

// ── The database change of a plan ──────────────────────────────────────────────

/** What drawing a proposed migration's diff came to: the fragment, or why there is none. */
export type DbDiff =
  | { drawn: true; html: string; css: string; infidelity: string[]; /** The feature's files applied before it, in order. */ after: string[] }
  | { drawn: false; unreachable: boolean; reason: string };

/** By `.sql` file, relative to the root. */
export type DbDiffs = Map<string, DbDiff>;

/** The project's hook that draws one (`planDiff` of the configuration), loaded when a plan first proposes a migration. */
let planDiff: ReturnType<typeof loadPlanDiff> | undefined;
const drawnDiffs = new Map<string, DbDiff>();

/**
 * The diff of every proposed change of the database: a `.sql` file of a feature folder carrying a `@planned`
 * tag, drawn by the project's own hook (`PlanDiff`, `stack.ts`) on a copy of its database. **A feature's files
 * are read in name order, and each is diffed against the state the earlier ones leave**: a file that rewrites
 * what another added shows that rewrite, not both changes at once. The render never needs that
 * database: when it cannot be reached, or with SQL that fails, the diff is a reason the page shows in red, and a
 * warning here. A diff is drawn once per process for the same SQL.
 */
export async function planDbDiffs(sources: PlanSources = readPlanSources()): Promise<DbDiffs> {
  const files = [...new Set(sources.statics.filter((s) => s.file.startsWith(`${featureFolder(s.feature)}/`) && s.file.endsWith('.sql')).map((s) => `${s.feature}\n${s.file}`))].sort();
  const earlierOf = new Map<string, Array<{ file: string; sql: string }>>();
  const out: DbDiffs = new Map();
  if (files.length === 0) return out;
  planDiff ??= loadPlanDiff();
  if (planDiff === null) return out;
  let unreachable: string | null = null;
  for (const entry of files) {
    const [feature, file] = entry.split('\n');
    const sql = readFileSync(join(ROOT, file), 'utf8');
    const earlier = earlierOf.get(feature) ?? [];
    earlierOf.set(feature, [...earlier, { file, sql }]);
    const key = [feature, ...earlier.map((e) => e.sql), sql].join('\n');
    let diff = drawnDiffs.get(key);
    if (!diff && unreachable !== null) diff = { drawn: false, unreachable: true, reason: unreachable };
    if (!diff) {
      try {
        diff = { drawn: true, after: earlier.map((e) => e.file), ...await planDiff.draw(sql, join(PLANS_DIR, `${feature}.html`), earlier.map((e) => e.sql)) };
        drawnDiffs.set(key, diff);
      } catch (error) {
        const reason = (error as Error).message;
        if (planDiff.isUnreachable(error)) {
          unreachable = reason;
          console.warn(`comprehension-render: WARNING — the database diff of ${file} is not drawn: ${reason}. ${planDiff.remedy}`);
        } else {
          console.warn(`comprehension-render: WARNING — the database diff of ${file} is not drawn: its SQL failed on the throwaway copy — ${reason}`);
        }
        diff = { drawn: false, unreachable: planDiff.isUnreachable(error), reason };
      }
    }
    out.set(file, diff);
  }
  return out;
}

// ── The plan page ──────────────────────────────────────────────────────────────
// Read top down: the pieces no flow shows; the flows the change lands in, each step one grey line for what it
// does today and one bold line per change that lands there; then a card per piece of the plan (its statement and reason from plan.md,
// one line per place in the code, one per test); then the rules' owners, the decisions across pieces, and the
// points the reviewer must answer. A site's clause is written once, at the site, and drawn in its flow row and
// in its card.

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** What rendering a plan needs beside the plan. */
interface PlanContext {
  plan: Plan;
  index: SourceIndex;
  narratives: Narrative[];
  diffs: DbDiffs;
  /** The commits that changed a function's lines, read once a render (`builtCommits`). */
  lineCommits: Map<string, string[] | null>;
}

const narrativeHref = (n: Narrative) => (n.kind === 'product' ? PLAN_LINKS.product(n) : PLAN_LINKS.mechanism(n));

/** `plan.md`'s markdown-lite, plus its own two links: `[text](url)` and `#slug`, a piece of this plan. */
function planInline(text: string, plan: Plan): string {
  const known = new Set(plan.pieces.map((s) => s.slug));
  const elsewhere = new Set(plan.pointers.map((p) => p.slug));
  const refs = replaceSlugRefs(esc(text), (slug) => (known.has(slug)
    ? `<a class="slug" href="#piece-${slug}">#${slug}</a>`
    : elsewhere.has(slug) ? `<a class="slug" href="#elsewhere-${slug}" title="planned in another repository">#${slug}</a>`
      : `<span class="flag" title="no site carries this tag">#${slug} — no such piece</span>`));
  return refs
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // A link to a file beside `plan.md` opens that file: the page is generated elsewhere.
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, shown: string, href: string) => (/^(?:[a-z][a-z0-9+.-]*:|[#/]|\.\.)/i.test(href)
      ? `<a href="${href}">${shown}</a>`
      : `<a class="src" href="vscode://file/${join(ROOT, featureFolder(plan.feature), href)}" data-review-source-href="${sourceHref({ file: `${featureFolder(plan.feature)}/${href}`, line: 1, column: 1 })}">${shown}</a>`));
}

const mdBlocks = (blocks: MdBlock[], plan: Plan) => blocksHtml(blocks, (t) => planInline(t, plan));

/** A file reference of a plan line: the file's name and the line, the whole path in the tooltip. */
const placeLink = (file: string, line: number, column = 1) => srcLink(file, line, column, `${basename(file)}:${line}`, ` title="${esc(file)}:${line}"`);

/** Where the function a place names stands in its file today: the top-level declaration of that name, else the
 *  one named function of that name the file holds — a function inside another (`moveFigure`, which `stepper`
 *  returns) is no declaration of the file and is a function of it. Null when the file holds neither. */
function functionPlace(index: SourceIndex, file: string, fn: string): { file: string; line: number; column: number } | null {
  const name = fn.replace(/#\d+$/, '');
  const declared = index.resolveUnscoped(name, [file]);
  if (declared && declared.file === file) return declared;
  const lines = index.lines(file, name);
  return lines ? { file, line: lines[0], column: 1 } : null;
}

/** A place's id, as its tag writes it after the piece: what its `built` call carries once it is code. */
const placeId = (place: string | undefined) => (place === undefined ? '' : ` <small title="the place's id: planned('…:${esc(place)}', …), then built('…:${esc(place)}') once it is code">:${esc(place)}</small>`);

/** A piece's chip: the link to its card, amber and marked `?` when the card holds a point to confirm. */
function pieceChip(piece: PlanPiece): string {
  return `<a class="slug${piece.doc?.ask ? ' ask' : ''}" href="#piece-${piece.slug}">#${piece.slug}${piece.doc?.ask ? ' ?' : ''}</a>`;
}

/**
 * The opening clause of a `narrate` or `event` sentence, for a flow row: what stands before its first full
 * stop, colon, dash, semicolon or bracket, then before its first comma when five words or more precede it (any
 * comma for an event), cut at 12 words. A sentence has no short form of its own; this is the nearest thing the
 * page can derive.
 */
export function headClause(sentence: string, atComma = false): string {
  const plain = sentence.replace(/\*\*/g, '');
  let cut = plain.split(atComma ? /\. |: | — |; |, / : /\. |: | — |; | \(/)[0];
  const comma = cut.indexOf(', ');
  if (comma > 0 && cut.slice(0, comma).split(/\s+/).length >= 5) cut = cut.slice(0, comma);
  const w = cut.split(/\s+/);
  if (w.length > 12) cut = `${w.slice(0, 12).join(' ')} …`;
  if ((cut.match(/`/g) ?? []).length % 2 === 1) cut += '`';
  return cut.replace(/[.,:]$/, '');
}

const clauseInline = (text: string) => esc(text).replace(/`([^`]+)`/g, '<code>$1</code>');

/** A planned call's clause, its symbols linked. */
function siteClause(site: PlanSite, ctx: PlanContext): string {
  const source = ctx.index.sites(site.file).get(site.line);
  if (!source) throw new Error(`comprehension-render: the planned site ${site.id} is no call at ${site.file}:${site.line}`);
  return sentenceHtml(site.sentence, source, ctx.index).html;
}

const CHANGE_MARK: Record<PlannedSite['change'], string> = { changed: 'changed', removed: 'removed', added: 'new', evidence: 'evidence', built: 'built' };

// ── The flows ──

/** A place the approval held and that is code now: its line as approved, read (`builtPlaceOf`). */
type BuiltPlace = NonNullable<ReturnType<typeof builtPlaceOf>> & { line: string };

/** What a step's row carries: a place still planned, or one that is built, drawn where it lands (`BuiltLanding`). */
type FlowChange =
  | { site: PlanSite; of: PlanPiece; how: 'in' | 'via' | 'after' }
  | { built: BuiltPlace; of: PlanPiece; how: 'in' | 'via' | 'after'; by: BuiltLanding['by']; among: number };

type FlowRow =
  | { kind: 'cause'; sentence: string }
  | { kind: 'step'; step: Step; changes: FlowChange[] }
  | { kind: 'new'; site: PlanSite; of: PlanPiece }
  | { kind: 'newBuilt'; built: BuiltPlace; of: PlanPiece };

const clauseOf = (c: FlowChange) => ('site' in c ? c.site.sentence : c.built.clause);

interface Flow {
  narrative: Narrative;
  rows: FlowRow[];
}

/**
 * The flows a plan lands in: every product narrative one of its sites lands in a step of, then a mechanism only
 * for a change no product flow shows. A flow is the narrative's causes and steps in the order its canonical
 * story crosses them; a step carries the sites that land in it; a shell is a new row after the step of the first
 * site whose clause names its function. A place that is built stays on its flow, where the approval froze it or
 * where its function tells a step now (`PlanPiece.lands`): the reviewer reads the clause approved under what
 * the step tells today. `shown` is every site a flow shows.
 */
function planFlows(ctx: PlanContext): { flows: Flow[]; shown: Set<PlanSite> } {
  const { plan } = ctx;
  const all = plan.pieces.flatMap((of) => of.sites.map((site) => ({ site, of })));
  const built = plan.pieces.flatMap((of) => of.built.sites.flatMap((line) => {
    const place = builtPlaceOf(line);
    return place ? [{ built: { ...place, line }, of }] : [];
  }));
  const keyOf = (b: { built: BuiltPlace; of: PlanPiece }) => `${b.of.slug}\n${b.built.line}`;
  const shown = new Set<PlanSite>();
  const shownBuilt = new Set<string>();
  const flows: Flow[] = [];
  const ordered = [...ctx.narratives].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'product' ? -1 : 1));
  for (const n of ordered) {
    if (!n.canonical) continue;
    const landing = all.flatMap(({ site, of }) => {
      const c = site.crossedBy.find((x) => x.narrative === n.title && x.step !== null);
      return c ? [{ site, of, n: c.step!.n, how: c.step!.how }] : [];
    });
    const landed = built.flatMap((b) => {
      const l = b.of.lands.find((x) => x.line === b.built.line && x.narrative === n.title);
      const step = l ? n.steps[l.step] : undefined;
      return l && step ? [{ ...b, n: step.n, how: l.how, by: l.by, among: l.among }] : [];
    });
    if (landing.length + landed.length === 0) continue;
    if (n.kind === 'mechanism' && landing.every((l) => shown.has(l.site)) && landed.every((l) => shownBuilt.has(keyOf(l)))) continue;
    const rows: FlowRow[] = [];
    const told = new Set<Step>();
    for (const segment of deriveSegments(n.canonical)) {
      const steps = n.steps.filter((s) => !told.has(s) && segment.hits.includes(s.stops[0]));
      if (steps.length === 0) continue;
      if (segment.event) rows.push({ kind: 'cause', sentence: segment.event.sentence });
      for (const step of steps) {
        told.add(step);
        const changes: FlowChange[] = [
          ...landing.filter((l) => l.n === step.n).map(({ site, of, how }) => ({ site, of, how })),
          ...landed.filter((l) => l.n === step.n).map(({ built: place, of, how, by, among }) => ({ built: place, of, how, by, among })),
        ];
        rows.push({ kind: 'step', step, changes });
        for (const c of changes) {
          if ('site' in c) shown.add(c.site);
          else shownBuilt.add(keyOf(c));
        }
        // A shell the plan adds is told where it is first called from.
        for (const shell of all) {
          if (shell.site.change !== 'added' || shown.has(shell.site)) continue;
          if (changes.some((c) => !('site' in c && c.site === shell.site) && names(clauseOf(c), shell.site.fn))) {
            rows.push({ kind: 'new', site: shell.site, of: shell.of });
            shown.add(shell.site);
          }
        }
        // So is a function the plan added and that is code, where no step of this narrative is its own.
        for (const b of built) {
          if (b.built.change !== 'added' || shownBuilt.has(keyOf(b)) || landed.some((l) => keyOf(l) === keyOf(b))) continue;
          if (changes.some((c) => !('built' in c && c.built.line === b.built.line) && names(clauseOf(c), b.built.fn))) {
            rows.push({ kind: 'newBuilt', built: b.built, of: b.of });
            shownBuilt.add(keyOf(b));
          }
        }
      }
    }
    flows.push({ narrative: n, rows });
  }
  return { flows, shown };
}

/** A built place's clause as approved, its symbols linked to the code that stands today. */
const builtClause = (place: BuiltPlace, of: PlanPiece, ctx: PlanContext) => codeInline(place.clause, ctx.plan, filesOf(of), ctx.index);

/** A built place's function, linked to where it stands today. */
function builtFn(place: BuiltPlace, ctx: PlanContext): string {
  const at = functionPlace(ctx.index, place.file, place.fn);
  return at ? srcLink(at.file, at.line, at.column, place.fn, ` title="${esc(at.file)}:${at.line}"`) : `<code>${esc(place.fn)}</code>`;
}

/**
 * The commits of a built place's piece that changed the function the place stands in, oldest first: the diff a
 * reviewer reads its clause against. A call marks a line, not a stretch, so the function is what is read; two
 * places of one function share its commits. Empty where git cannot tell (the file is being edited).
 */
function builtCommits(place: BuiltPlace, of: PlanPiece, ctx: PlanContext): PieceCommit[] {
  const lines = ctx.index.lines(place.file, place.fn);
  if (lines === null || of.commits.length === 0) return [];
  const key = `${place.file}:${lines[0]}-${lines[1]}:${of.commits[0].sha}`;
  if (!ctx.lineCommits.has(key)) ctx.lineCommits.set(key, commitsOfLines(place.file, lines[0], lines[1], of.commits[0].sha, ROOT));
  const changed = ctx.lineCommits.get(key) ?? [];
  return of.commits.filter((c) => changed.includes(c.sha));
}

/** The link from a built line to what was written for it: the commits that changed its function, each one
 *  opening in the editor and, when they read as one diff, all of them at once; else the piece's commits. */
function builtCommitsHtml(place: BuiltPlace, of: PlanPiece, ctx: PlanContext): string {
  const commits = builtCommits(place, of, ctx);
  const piece = `<a href="${deliveryPage(ctx.plan.feature)}#piece-${of.slug}" title="the piece's commits, as one diff, on the delivery page">its commits</a>`;
  if (commits.length === 0) return piece;
  const one = (c: PieceCommit) => `<a href="vscode://local.plan-review-links/commit?sha=${c.sha}" title="${esc(subjectHead(c.subject))}"><code>${c.sha.slice(0, 8)}</code></a>`;
  const together = commits.length > 1 && commitBlocks(commits, ctx.plan.history).length === 1
    ? ` <a href="vscode://local.plan-review-links/commits?shas=${commits.map((c) => c.sha.slice(0, 12)).join(',')}&amp;title=${encodeURIComponent(`${ctx.plan.feature}#${of.slug} · ${place.fn}`)}" title="Open what these commits come to as one diff">as one diff</a>` : '';
  return `<span title="the commits of #${esc(of.slug)} that changed ${esc(place.fn)}">built in ${commits.map(one).join(' ')}</span>${together}`;
}

/** The line a built place stands at, linked, where its `built` call says it; nothing otherwise. */
function builtAt(place: BuiltPlace, of: PlanPiece): string {
  const mark = markOf(of, place.line);
  return mark ? ` <small>${placeLink(mark.file, mark.line, mark.column)}</small>` : '';
}

function flowHtml(flow: Flow, ctx: PlanContext): string {
  const n = flow.narrative;
  const rows = flow.rows.map((row) => {
    if (row.kind === 'cause') return `<div class="fcause">${clauseInline(headClause(row.sentence, true))}</div>`;
    if (row.kind === 'new') {
      return `<div class="frow new"><span class="n">+</span><span class="today">${placeLink(row.site.file, row.site.line, row.site.column)} <code>${esc(row.site.fn)}</code></span>
        <span class="chg"><span class="mark added">new</span> ${siteClause(row.site, ctx)}</span>${pieceChip(row.of)}</div>`;
    }
    if (row.kind === 'newBuilt') {
      const at = functionPlace(ctx.index, row.built.file, row.built.fn);
      return `<div class="frow new done"><span class="n">+</span><span class="today">${at ? placeLink(at.file, at.line, at.column) : esc(basename(row.built.file))} <code>${esc(row.built.fn)}</code></span>
        <span class="chg"><span class="mark done">built</span> ${builtClause(row.built, row.of, ctx)}</span>${pieceChip(row.of)}</div>`;
    }
    const { step, changes } = row;
    const head = headClause(step.sentence);
    const fn = step.source.fn;
    const rest = head.startsWith(`\`${fn}\` `) ? head.slice(fn.length + 3) : `· ${head}`;
    const today = `${srcLink(step.source.file, step.source.line, step.source.column, fn, ` title="${esc(step.source.file)}:${step.source.line}"`)} ${clauseInline(rest)}`;
    const lines = changes.map((c) => ('site' in c ? `
        <span class="chg"><span class="mark ${c.site.change}">${CHANGE_MARK[c.site.change]}</span> ${siteClause(c.site, ctx)}${c.how === 'in' ? '' : ` <small>in <code>${esc(c.site.fn)}</code></small>`}</span>${pieceChip(c.of)}` : `
        <span class="chg"><span class="mark done">built</span> ${builtClause(c.built, c.of, ctx)}${builtAt(c.built, c.of)}${c.how === 'in' ? '' : ` <small>in ${builtFn(c.built, ctx)}</small>`}${c.among > 1 ? ` <small class="pending" title="${c.by === 'approved' ? 'The step this place was approved in tells another sentence now, and its function tells several steps: this one is the closest to the sentence approved.' : 'Nothing was kept of where this place was approved to land, and its function tells several steps: this is the first of them.'}">step not certain: the ${c.by === 'approved' ? 'closest' : 'first'} of the ${c.among} steps of <code>${esc(step.source.fn)}</code></small>` : ''} · <small>${builtCommitsHtml(c.built, c.of, ctx)}</small></span>${pieceChip(c.of)}`)).join('');
    const state = changes.length === 0 ? 'same' : changes.every((c) => 'built' in c) ? 'done' : 'touched';
    return `<div class="frow ${state}"><span class="n">${step.n}</span><span class="today"><a class="stepref" href="${narrativeHref(n).split('#')[0]}#${esc(n.slug)}-step-${step.n}" title="the step on its narrative page">↗</a> ${today}</span>${lines}</div>`;
  });
  return `<div class="flow"><h3><a href="${narrativeHref(n)}">${esc(n.title)}</a></h3>
${rows.join('\n')}
</div>`;
}

// ── The cards ──

/** What kind of place a `@planned` comment marks, by where its file stands. */
function staticMark(site: StaticSite): string {
  if (site.file.endsWith('.sql')) return 'sql';
  if (layout.isTest(site.file)) return 'test';
  if (/\.(?:md|html)$/.test(site.file)) return 'doc';
  return 'comment';
}

function siteLine(site: PlanSite, ctx: PlanContext, ofABug = false): string {
  const name = site.change === 'added' && site.signature ? site.signature.replace(/^export\s+(?:default\s+)?(?:async\s+)?(?:function\s+|const\s+)?/, '') : site.fn;
  // What a reproduction saw is in no narrative: a bug is in no told flow, or it would not be one.
  const flag = site.change === 'added' || site.change === 'evidence' || ofABug ? ''
    : site.crossedBy.length === 0 ? ' <small class="pending" title="no narrative\'s reference case crosses this call">no narrative crosses it</small>'
      : '';
  const untested = site.change !== 'added' && site.reachedBy.length === 0 ? ' <small class="pending">no test reaches it</small>' : '';
  return `<div class="pline" data-planned="${esc(site.id)}"><span class="mark ${site.change}">${CHANGE_MARK[site.change]}</span><span class="where">${placeLink(site.file, site.line, site.column)} <code>${esc(name)}</code>${placeId(site.place)}</span><span class="clause">${siteClause(site, ctx)}${flag}${untested}</span></div>`;
}

/** A comment on a test says what becomes of the test under it: deleted, or changed. Elsewhere it says what the
 *  file is. The colours are the code's: red goes, amber changes, green is new. */
function staticLine(site: StaticSite, plan: Plan): string {
  const onTest = layout.isTest(site.file);
  const mark = onTest ? (site.removes ? '<span class="mark removed">deleted</span>' : '<span class="mark changed">changed</span>') : `<span class="mark${site.removes ? ' removed' : ''}">${site.removes ? 'deleted' : staticMark(site)}</span>`;
  return `<div class="pline">${mark}<span class="where">${placeLink(site.file, site.line)}${site.on ? ` on <code>${esc(site.on)}</code>` : ''}</span><span class="clause">${site.text ? planInline(site.text, plan) : '<small class="flag">no text after the tag</small>'}</span></div>`;
}

function todoLine(todo: PlanTodo, plan: Plan, fixed = false): string {
  const rule = todo.rule === null ? ''
    : plan.rules.some((r) => r.slug === todo.rule) ? ` <a class="rule" href="#rule-${todo.rule}" title="owns this rule of spec.md">${todo.rule}</a>`
      : ` <span class="flag">[${esc(todo.rule)}] is no rule of spec.md</span>`;
  const unnamed = todo.tier === 'unit' && layout.isServerTest(todo.file) ? ' <small>a db or edge test no server step names as its truth</small>' : '';
  // A planned test is a test added: its tier says where it stands.
  if (todo.reproduction) return `<div class="pline"><span class="mark failing">fails today</span><span class="where">${placeLink(todo.file, todo.line, todo.column)} <small>${todo.tier} · reproduction</small></span><span class="clause">${clauseInline(todo.title)}${rule}</span></div>`;
  // A reproduction that passes is a test like another: it says what it was approved as.
  if (fixed) return `<div class="pline"><span class="mark done">passes</span><span class="where">${placeLink(todo.file, todo.line, todo.column)} <small>${todo.tier} · was the reproduction</small></span><span class="clause">${clauseInline(todo.title)}${rule}</span></div>`;
  return `<div class="pline"><span class="mark added">added</span><span class="where">${placeLink(todo.file, todo.line, todo.column)} <small>${todo.tier}${todo.written ? ' · written' : ''}</small></span><span class="clause">${clauseInline(todo.title)}${rule}${unnamed}</span></div>`;
}

/** The spec's journey cases still to write, under their journey. They carry no piece: a case on screen usually
 *  needs several, and is written once those are in. */
function planJourneyCasesHtml(plan: Plan): string {
  if (plan.journeyCases.length === 0) return '';
  const journeys = [...new Set(plan.journeyCases.map((c) => c.journey))];
  const boxes = journeys.map((journey) => {
    const cases = plan.journeyCases.filter((c) => c.journey === journey);
    return `<div class="pbox"><p class="also"><b>${esc(journey)}</b> · ${srcLink(cases[0].file, cases[0].line, 1, basename(cases[0].file))}</p><div class="plines tests">${cases.map((c) => `<div class="pline"><span class="mark tier">journey</span><span class="where">${placeLink(c.file, c.line, c.column)} <small>at ${esc(c.screen)}</small></span><span class="clause">${clauseInline(c.title)}</span></div>`).join('')}</div></div>`;
  });
  return `
<h2 id="journeys">The spec's journey cases — ${plural(plan.journeyCases.length, 'case')} to write</h2>
<p class="legend">Declared by the spec in the journey tests, as <code>todo</code>. Each is written once the pieces behind it are in, so none is listed under a piece.</p>
${boxes.join('\n')}`;
}

/** The proposed migration of a piece: the diff of the database view, folded; a red note when it could not be drawn. */
function dbDiffHtml(file: string, ctx: PlanContext): string {
  // A project with no way to draw a migration's diff shows the migration as any other place of the piece.
  if (config.planDiff === null) return '';
  const diff = ctx.diffs.get(file);
  const head = `The database after ${srcLink(file, 1, 1, basename(file))}`;
  if (!diff) return `<p class="note red">${head} is not drawn by this render: the diff needs the local Postgres, and this render did not ask for it. Run <code>npm run comprehension:render</code>.</p>`;
  if (!diff.drawn) {
    return `<p class="note red">${head} is not drawn: ${diff.unreachable
      ? `the local Postgres is not reachable (${esc(diff.reason)}). Run <code>${esc(planDiff?.remedy ?? '')}</code>.`
      : `the SQL failed on the throwaway copy — <code>${esc(diff.reason)}</code>`}</p>`;
  }
  const infidelity = diff.infidelity.length ? `<p class="fine">The throwaway copy reads differently from the shared database in ${plural(diff.infidelity.length, 'place')}, the same on both sides of the diff.</p>` : '';
  // Open: for a change of the database this is the place to read, and the file is only what produced it.
  const after = diff.after.length ? `, read after ${diff.after.map((f) => srcLink(f, 1, 1, basename(f))).join(', ')}` : '';
  return `<details class="pfold dbdiff" open><summary>${head} — the diff of the view${after}</summary>${infidelity}${diff.html}</details>`;
}

/** Where a piece lands, for its card's header: the steps of each narrative, or why there is none. */
function landsLabel(piece: PlanPiece, group: PlanGroup | undefined, narratives: Narrative[], plan: Plan): string {
  const product = (title: string) => (narratives.find((n) => n.title === title)?.kind === 'product' ? 0 : 1);
  const stepsOf = (sites: PlanSite[]) => {
    const by = new Map<string, Set<number>>();
    for (const site of sites) for (const c of site.crossedBy) if (c.step) by.set(c.narrative, (by.get(c.narrative) ?? new Set()).add(c.step.n));
    return [...by].sort((x, y) => product(x[0]) - product(y[0])).map(([narrative, ns]) => `${esc(narrative)} · ${ns.size === 1 ? 'step' : 'steps'} ${[...ns].sort((x, y) => x - y).join(', ')}`).join(' — ');
  };
  const lands = stepsOf(piece.sites);
  if (lands) return lands;
  // A piece all built is told where its places landed.
  const builtBy = new Map<string, Set<number>>();
  for (const l of piece.lands) {
    const step = narratives.find((n) => n.title === l.narrative)?.steps[l.step];
    if (step) builtBy.set(l.narrative, (builtBy.get(l.narrative) ?? new Set()).add(step.n));
  }
  const builtIn = [...builtBy].sort((x, y) => product(x[0]) - product(y[0])).map(([narrative, ns]) => `${esc(narrative)} · ${ns.size === 1 ? 'step' : 'steps'} ${[...ns].sort((x, y) => x - y).join(', ')}`).join(' — ');
  if (piece.sites.length === 0) return piece.built.sites.length ? (builtIn ? `built, in ${builtIn}` : 'built: its places are code') : piece.statics.length ? 'no runtime line' : 'no place in this repository\'s code';
  // A piece of shells runs where the sites that name its functions land.
  const shells = piece.sites.filter((x) => x.change === 'added');
  const callers = plan.pieces.flatMap((other) => other.sites).filter((x) => !piece.sites.includes(x) && shells.some((shell) => names(x.sentence, shell.fn)));
  const calledFrom = stepsOf(callers);
  if (calledFrom) return `new code, called from ${calledFrom}`;
  return group?.kind === 'narrative' ? `crossed by ${esc(group.narrative!)}, in no step of it` : 'crossed by no narrative';
}

/** A piece planned elsewhere: where, what its repository states of it and whether that is approved there, then
 *  what this plan relies on. */
function pointerHtml(pointer: Plan['pointers'][number], plan: Plan): string {
  const { target } = pointer;
  const state = target === null ? 'not checked: no checkout of that repository is known here'
    : target.statement === null ? '<span class="flag">no such piece in its plan</span>'
      : target.approvedOn ? `approved there on ${esc(target.approvedOn)}` : 'not approved there yet';
  const stated = target?.statement
    ? `<b>${esc(target.statement)}</b> <small><a class="src" href="vscode://file/${esc(target.source)}:${target.line}:1">its plan.md</a></small><br>`
    : '';
  return `<div class="pline" id="elsewhere-${pointer.slug}"><span class="where"><span class="slug">${esc(pointer.repository)} #${pointer.slug}</span><br><small>${state}</small></span>`
    + `<span class="clause">${stated}${planInline(pointer.reason, plan)} <small>${srcLink(plan.doc!.file, pointer.line, 1, 'plan.md')}</small></span></div>`;
}

/** The watches a place shows in full before the rest is counted. */
const SEEN_SHOWN = 6;

/** What a reproduction saw at one place: each distinct crossing, counted, a value that is not the one the
 *  crossing should have in red, with that one. Where the place says what it should see, the crossings that
 *  differ are shown first and in full; those that saw what they should are counted, and folded. Crossings that
 *  saw one value where each should have its own open the list, together: the value once, then what else each saw. */
function seenValuesHtml(site: Pick<PlanSite, 'expect' | 'distinct'>, crossings: Crossing[]): string {
  const pairsOf = (x: unknown) => (x !== null && typeof x === 'object' && !Array.isArray(x) ? x as Record<string, unknown> : null);
  const groups = shared(site.distinct, crossings);
  const together = new Set(groups.flat());
  const distinct = new Map<string, { crossing: Crossing; times: number }>();
  for (const crossing of crossings) {
    if (together.has(crossing) || ((crossing.watch ?? null) === null && (crossing.expect ?? null) === null)) continue;
    const flat = JSON.stringify(crossing);
    distinct.set(flat, { crossing, times: (distinct.get(flat)?.times ?? 0) + 1 });
  }
  const rows = [...distinct.values()].map((x) => ({ ...x, wrong: unexpected(x.crossing) }));
  /** The pairs of a crossing, those of `left` aside: a key whose value is not the one it should have in red. */
  const pairsHtml = (crossing: Crossing, left: string[] = []) => {
    const wrong = unexpected(crossing);
    const seen = pairsOf(crossing.watch);
    const should = pairsOf(crossing.expect) ?? {};
    const shouldBe = (key: string) => ` <span class="should">should be ${value(should[key])}</span>`;
    const pairs = seen
      ? Object.entries(seen).filter(([key]) => !left.includes(key)).map(([key, v]) => `<span class="pair${wrong.includes(key) ? ' wrong' : ''}"><span class="k">${esc(key)}</span> ${value(v)}${wrong.includes(key) ? shouldBe(key) : ''}</span>`).join('')
      : crossing.watch === null ? '' : `<span class="pair">${value(crossing.watch)}</span>`;
    const missing = wrong.filter((key) => !(seen && key in seen)).map((key) => `<span class="pair wrong"><span class="k">${esc(key)}</span> <small>not in the watch</small>${shouldBe(key)}</span>`).join('');
    return `${pairs}${missing}`;
  };
  const row = ({ crossing, times }: typeof rows[number]) => `<div class="seen">${times > 1 ? `<small class="times">×${times}</small>` : ''}${pairsHtml(crossing)}</div>`;
  const sharedRows = groups.map((group) => {
    const seen = pairsOf(group[0].watch)!;
    const same = site.distinct.map((key) => `<span class="pair wrong"><span class="k">${esc(key)}</span> ${value(seen[key])}</span>`).join('');
    const each = group.map((crossing) => pairsHtml(crossing, site.distinct)).filter(Boolean).map((pairs) => `<div class="seen each">${pairs}</div>`).join('');
    return `<div class="seen"><small class="times">×${group.length}</small>${same} <span class="should">should be one for each crossing</span></div>${each}`;
  }).join('');
  const list = (some: typeof rows) => `${some.slice(0, SEEN_SHOWN).map(row).join('')}${some.length > SEEN_SHOWN ? `<div class="seen"><small>… and ${plural(some.length - SEEN_SHOWN, 'other value')}</small></div>` : ''}`;
  if (site.expect === null && site.distinct.length === 0) return list(rows);
  const wrong = rows.filter((x) => x.wrong.length > 0);
  const right = rows.filter((x) => x.wrong.length === 0);
  const times = right.reduce((n, x) => n + x.times, 0);
  const stated = site.expect !== null && !wrong.length && !groups.length ? `<div class="seen"><small>should see</small><code>${esc(site.expect)}</code></div>` : '';
  return `${sharedRows}${wrong.map(row).join('')}${stated}${right.length ? `<details class="pfold"><summary>${plural(times, 'other crossing')} saw ${site.expect === null ? `a value of ${times === 1 ? 'its' : 'their'} own` : `what ${times === 1 ? 'it' : 'they'} should`}</summary>${list(right)}</details>` : ''}`;
}

/** Why a reproduction has no story, and what gives it one: the render's own run of it wrote none (a server it
 *  needs was down, the run died before the file's end), or no tool runs it. */
function noRunHtml(file: string): string {
  const command = testCommandOf(file);
  const link = srcLink(file, 1, 1, file);
  if (command) return `the render ran ${link} first (<code>${esc(typed(command, file))}</code>) and the run wrote no story: what the render printed says why. Once it can run, render again.`;
  if (layout.isBrowserTest(file)) return `${link} runs in a browser, whose run writes no story here: its diagnostic holds how it fails.`;
  return `no tool runs ${link} (<code>commands.testsUnder</code> of <code>${CONFIG_FILE}</code>): run it by hand, then render again.`;
}

/**
 * The bug a piece fixes, as its reproductions tell it: each test declared to fail today, the places of the
 * piece it crossed in run order with what it saw at each, then how it failed. A reproduction is run under the
 * debugger from here. Evidence no reproduction crossed is listed last: it shows nothing yet. `shown` is the
 * places the block draws, which the piece's own list then leaves out.
 */
function bugHtml(piece: PlanPiece, ctx: PlanContext): { html: string; shown: Set<PlanSite> } {
  const reproductions = piece.todos.filter((t) => t.reproduction);
  const evidence = piece.sites.filter((s) => s.change === 'evidence');
  const shown = new Set<PlanSite>();
  if (reproductions.length === 0 && evidence.length === 0) return { html: '', shown };
  const told = reproductions.map((t) => {
    const crossed = placesCrossed(piece, t);
    for (const { site } of crossed) shown.add(site);
    const rows = crossed.map(({ site, seen }) => `<div class="pline"><span class="mark ${site.change}">${CHANGE_MARK[site.change]}</span><span class="where">${placeLink(site.file, site.line, site.column)} <code>${esc(site.fn)}</code>${seen.crossings.length > 1 ? ` <small>crossed ×${seen.crossings.length}</small>` : ''}</span><span class="clause">${siteClause(site, ctx)}${seenValuesHtml(site, seen.crossings)}</span></div>`).join('');
    const failure = t.run?.failure;
    const failed = failure ? `<div class="failure"><small>it fails at ${failure.file ? placeLink(failure.file, failure.line) : `line ${failure.line}`}:</small><pre>${esc(failure.message)}</pre></div>`
      : t.run ? `<p class="also"><span class="flag">Its last run did not fail (${esc(t.run.state ?? 'no state')}):</span> a reproduction that passes is a test like another, declared as one.</p>`
        : `<p class="also"><span class="pending">No run on file:</span> ${noRunHtml(t.file)}</p>`;
    return `<div class="repro"><div class="repro-head"><span class="mark failing">fails today</span><span>${clauseInline(t.title)}</span>${srcLink(t.file, t.line, t.column, '▶ debug this reproduction', ' data-debug-reproduction title="Run this test under the VS Code debugger, stopping at your breakpoints"')}</div>`
      + `${rows ? `<div class="plines">${rows}</div>` : t.run ? '<p class="also">It crosses no place of the piece.</p>' : ''}${failed}</div>`;
  });
  return { html: `<div class="bug"><p class="bug-head"><b>The bug today</b> — what each reproduction saw at the piece's places, in the order it crossed them, then how it failed.</p>${told.join('')}</div>`, shown };
}

/**
 * The bug a built piece fixed, as the approval kept it (`FrozenChain`): each test that was its reproduction, the
 * places it crossed with what it saw at each, how it failed then, and the test as it stands now. The evidence is
 * gone from the source and the test passes: no run tells this again, so it is drawn from the approval, and a
 * place is named by its file and its function, not by a line. Empty for a piece whose approval froze nothing.
 */
function fixedBugHtml(piece: PlanPiece, plan: Plan): string {
  const chains = fixedChains(piece);
  if (chains.length === 0) return '';
  const file = (f: string) => (existsSync(join(ROOT, f)) ? srcLink(f, 1, 1, basename(f), ` title="${esc(f)}"`) : esc(basename(f)));
  const told = chains.map((chain: FrozenChain) => {
    const t = piece.todos.find((o) => o.file === chain.file && o.title === chain.title);
    const rows = chain.crossed.map((x) => `<div class="pline"><span class="mark ${x.change}">${CHANGE_MARK[x.change]}</span><span class="where">${file(x.file)} <code>${esc(x.fn)}</code>${x.crossings.length > 1 ? ` <small>crossed ×${x.crossings.length}</small>` : ''}</span><span class="clause">${clauseInline(x.sentence).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')}${seenValuesHtml(x, x.crossings)}</span></div>`).join('');
    const failed = chain.failure ? `<div class="failure"><small>it failed${chain.failure.file ? ` in ${file(chain.failure.file)}` : ''}:</small><pre>${esc(chain.failure.message)}</pre></div>` : '';
    const now = t ? `<span class="mark done">a test now</span>${placeLink(t.file, t.line, t.column)}` : '<span class="flag">the test is gone</span>';
    return `<div class="repro"><div class="repro-head"><span class="mark failing">failed when approved</span><span>${clauseInline(chain.title)}</span><span class="now">${now}</span></div>`
      + `${rows ? `<div class="plines">${rows}</div>` : '<p class="also">It crossed no place of the piece.</p>'}${failed}</div>`;
  });
  return `<div class="bug fixed"><p class="bug-head"><b>The bug, as approved${plan.approved ? ` on ${esc(plan.approved.approvedOn)}` : ''}</b> — what each reproduction saw then at the piece's places, and how it failed. The places are code now, and the evidence went with the fix.</p>${told.join('')}</div>`;
}

function planPieceHtml(piece: PlanPiece, ctx: PlanContext): string {
  const { plan } = ctx;
  const group = plan.groups.find((g) => g.pieces.includes(piece));
  const doc = piece.doc;
  const statement = doc
    ? `<p class="what">${planInline(doc.what, plan)} <small>${srcLink(plan.doc!.file, doc.section.line, 1, 'plan.md')}</small></p>${doc.why.length ? `<div class="why">${mdBlocks(doc.why, plan)}</div>` : ''}`
    : plan.doc ? `<p class="what"><span class="pending">No section "## #${esc(piece.slug)}" in plan.md: the piece has no statement.</span></p>` : '';
  const moved = (plan.delta ?? []).find((d) => d.kind === 'piece' && d.name === `#${piece.slug}`);
  // A bug's piece says each thing once: a place its reproductions crossed and the reproductions themselves are
  // in the block above, and the lists under it hold the rest.
  const bug = bugHtml(piece, ctx);
  const ofABug = bug.html !== '';
  const uncrossed = piece.sites.filter((s) => !bug.shown.has(s));
  const places = [...uncrossed.map((s) => siteLine(s, ctx, ofABug)), ...piece.statics.map((s) => staticLine(s, plan)), builtLinesHtml(piece, plan, ctx.index)].filter(Boolean);
  const tests = piece.todos.filter((t) => !t.reproduction).map((t) => todoLine(t, plan, piece.reproduced.includes(reproductionKeyOf(t))));
  const placesHead = ofABug && uncrossed.length ? `<p class="also">${plural(uncrossed.length, 'place')} of the piece no reproduction crosses:</p>` : '';
  const noPlace = '<div class="pline"><span class="mark"></span><span class="where"></span><span class="clause"><small>no place in the code: planned tests only</small></span></div>';
  const reach = piece.sites.filter((s) => s.reachedBy.length);
  const reached = reach.length ? `<details class="pfold"><summary>the tests that reach these places today</summary>${reach.map((s) => {
    const total = s.reachedBy.reduce((n, r) => n + r.tests, 0);
    return `<p>${placeLink(s.file, s.line, s.column)} — ${plural(total, 'test')}: ${s.reachedBy.map((r) => `${srcLink(r.file, 1, 1, r.file)} <small>${r.tests}</small>`).join(', ')}</p>`;
  }).join('')}</details>` : '';
  const across = piece.decidedIn.length ? `<p class="also">Also decided in ${piece.decidedIn.map((s) => `<a href="#${s.anchor}">${esc(s.title)}</a>`).join(', ')}.</p>` : '';
  return `
<section class="piece" id="piece-${piece.slug}" data-piece="${esc(plan.feature)}#${piece.slug}">
  <header><a class="slug big" href="#piece-${piece.slug}">#${piece.slug}</a><small>${landsLabel(piece, group, ctx.narratives, plan)}</small>${moved ? `<a class="slug ask" href="${deliveryPage(plan.feature)}#piece-${piece.slug}">${moved.state === 'new' ? 'new' : 'modified'} since your approval</a>` : ''}</header>
  ${statement}
  ${notesHtml(piece, plan, (t) => planInline(t, plan))}
  ${pieceAskHtml(piece, plan)}
  ${bug.html}
  ${fixedBugHtml(piece, plan)}
  ${placesHead}
  ${places.length ? `<div class="plines">${places.join('')}</div>` : ofABug ? '' : `<div class="plines">${noPlace}</div>`}
  ${tests.length ? `<div class="plines tests">${tests.join('')}</div>` : ofABug ? '' : '<p class="also">No planned test yet.</p>'}
  ${piece.sql.map((file) => dbDiffHtml(file, ctx)).join('')}
  ${moved && unitDeltaHtml(moved, plan, ctx.index) ? `<details class="pfold since" open><summary>since your approval — the card above is the plan as it stands; this is what differs from the plan you approved</summary>${unitDeltaHtml(moved, plan, ctx.index)}<p class="legend">${DELTA_LEGEND}</p></details>` : ''}
  ${reached}
  ${across}
</section>`;
}

/** The rules of `spec.md` and the one test that owns each; a rule with none or with two is flagged. A rule the
 *  plan waives reads "no test" and its reason, with the amber mark and the reviewer's answer under it while the
 *  waiver is to confirm. */
function planRulesHtml(plan: Plan): string {
  if (plan.rulesFile === null) return '';
  const owner = (todo: PlanTodo) => `${todo.tier} · ${placeLink(todo.file, todo.line, todo.column)} <a class="slug" href="#piece-${todo.slug}">#${todo.slug}</a>`;
  const rows = plan.rules.map((r) => {
    const waived = r.waiver
      ? `${r.waiver.toConfirm ? '<span class="slug ask">?</span> ' : ''}${srcLink(plan.doc!.file, r.waiver.line, 1, 'no test')}: ${planInline(r.waiver.reason, plan)}`
      : '';
    const state = r.waiver && r.owners.length ? `<span class="flag">a test and a waiver — a rule has one or the other</span> ${r.owners.map(owner).join(' ')}`
      : r.waiver ? waived
        : r.owners.length === 1 ? owner(r.owners[0])
          : r.owners.length === 0 ? `<span class="pending">no owner yet</span>`
            : `<span class="flag">${r.owners.length} owners — a rule has one</span> ${r.owners.map(owner).join(' ')}`;
    return `<div class="pline" id="rule-${r.slug}"><span class="rule">${r.slug}</span><span class="clause">${planInline(headClause(r.text), plan)} <small>${srcLink(plan.rulesFile!, r.line, 1, `spec.md:${r.line}`)}</small></span><span class="where">${state}</span></div>${r.waiver?.toConfirm ? verdictHtml(waiverQuestion(r.waiver), plan) : ''}`;
  });
  const stray = plan.unknownRules.map((t) => `<div class="pline"><span class="flag">[${esc(t.rule!)}]</span><span class="clause"><span class="flag">is no rule of spec.md</span></span><span class="where">${owner(t)}</span></div>`);
  const owned = plan.rules.filter((r) => r.owners.length === 1 && !r.waiver).length;
  const waivedCount = plan.rules.filter((r) => r.waiver && r.owners.length === 0).length;
  return `
<h2 id="rules">The spec's rules no screen shows — ${owned} of ${plan.rules.length} owned by one test${waivedCount ? `, ${waivedCount} held by no test` : ''}</h2>
<div class="pbox rules">${[...rows, ...stray].join('')}</div>`;
}

export function renderPlanPage(plan: Plan, stories: Story[], narratives: Narrative[], index: SourceIndex, diffs: DbDiffs = new Map()): string {
  const generatedAt = new Date().toISOString();
  const ctx: PlanContext = { plan, index, narratives, diffs, lineCommits: new Map() };
  const folder = `${featureFolder(plan.feature)}/`;
  const doc = plan.doc;
  const lede = doc
    ? `<div class="lede">${mdBlocks(doc.lead, plan)}</div>`
    : `<p class="lede">${plan.folderExists
      ? `<span class="flag">${esc(folder)}plan.md does not exist</span>: the pieces have no statement and no reason.`
      : `<span class="flag">${esc(folder)} does not exist — <code>--check</code> fails on it.</span>`}</p>`;
  const { flows, shown } = planFlows(ctx);
  // What no flow shows is read first: a piece no narrative crosses, one with no place in this repository. A
  // flow gives such a piece no context, so nothing else on the page points the reader at it. A piece whose
  // places all became code is no such piece.
  const outside = plan.pieces.filter((s) => !s.sites.some((x) => shown.has(x)) && !pieceState(s).done && !(s.sites.length === 0 && s.built.sites.length > 0));
  const cards = [...outside, ...plan.pieces.filter((s) => !outside.includes(s))];
  const asks = plan.pieces.filter((s) => s.doc?.ask);
  const waiversToConfirm = plan.rules.filter((r) => r.waiver?.toConfirm);
  const points = asks.length + waiversToConfirm.length;
  const bar = doc ? reviewBarHtml(plan) : '';
  const places = plan.pieces.reduce((n, s) => n + s.sites.length + s.statics.length, 0);
  const toWrite = plan.pieces.reduce((n, s) => n + s.todos.filter((t) => !t.written).length, 0);
  const builtPlaces = plan.pieces.reduce((n, s) => n + s.built.sites.filter(isBuiltPlace).length + s.built.comments.length, 0);
  const across = doc ? doc.sections.filter((s) => s.piece === null && !s.bug) : [];
  // A plan of bugs is read a bug at a time: what is wrong, then the pieces that fix it, in the order plan.md
  // holds them. A piece under no bug keeps its place before them.
  const bugs = doc ? doc.sections.filter((s) => s.bug) : [];
  const lineOf = (piece: PlanPiece) => piece.doc?.section.line ?? 0;
  const fixing = (bug: PlanSection) => plan.pieces.filter((s) => s.bug === bug).sort((a, b) => lineOf(a) - lineOf(b));
  // A bug is fixed once every piece under it is built: no place left, and its reproductions tests like others.
  const isFixed = (bug: PlanSection) => fixing(bug).length > 0 && fixing(bug).every((s) => pieceState(s).done);
  const bugHead = (bug: PlanSection) => `<section class="abug${isFixed(bug) ? ' fixed' : ''}" id="${bug.anchor}"><h3>${isFixed(bug) ? '<span class="mark done">fixed</span>' : '<span class="mark failing">bug</span>'} ${planInline(bug.title, plan)} <small>${srcLink(doc!.file, bug.line, 1, 'plan.md')}</small></h3>${mdBlocks(bug.blocks, plan)}<p class="also">${isFixed(bug) ? 'Fixed by' : 'To be fixed by'} ${fixing(bug).map(pieceChip).join(' ')}${isFixed(bug) ? ': each is built, and its reproductions pass as tests.' : ''}</p></section>`;
  const outsideRow = (s: PlanPiece) => `<div class="pline"><span class="where">${pieceChip(s)}<br><small>${landsLabel(s, plan.groups.find((g) => g.pieces.includes(s)), narratives, plan)}</small></span><span class="clause">${s.doc ? planInline(s.doc.what, plan) : '<span class="pending">no statement in plan.md</span>'}</span></div>`;
  const byBug = <T>(pieces: PlanPiece[], piece: (s: PlanPiece) => T, head: (bug: PlanSection) => T): T[] => [
    ...pieces.filter((s) => s.bug === null).map(piece),
    ...bugs.flatMap((bug) => { const its = fixing(bug).filter((s) => pieces.includes(s)); return its.length ? [head(bug), ...its.map(piece)] : []; }),
  ];
  // A drawn diff brings the database view's stylesheet, scoped to the element the fragment sits in (CSS nesting);
  // its `:root` variables are set on that element.
  const drawn = plan.pieces.flatMap((s) => s.sql).map((f) => diffs.get(f)).find((d) => d?.drawn);
  const dbCss = drawn?.drawn ? `.dbdiff { ${drawn.css.replace(':root', '&')} }` : '';
  const body = `
<h1>${esc(doc ? doc.title : `Plan — ${plan.feature}`)}</h1>
${lede}
${doc && (plan.approved || doc.lots.length) ? `<p class="legend">${plan.approved ? `Approved on ${esc(plan.approved.approvedOn)}${plan.delta!.length ? `; <b>${plural(plan.delta!.length, 'unit')} not as approved</b>` : ', and as approved'}. ` : ''}<a href="${deliveryPage(plan.feature)}">The delivery${doc.lots.length ? `, in ${plural(doc.lots.length, 'lot')}` : ''}, and what moved since the approval</a>.</p>` : ''}
${points || bar ? `
<h2 id="answers">Your answers${points ? ` — ${plural(points, 'point')} to confirm, each answered where it is stated` : ''}</h2>
${points ? `<p class="pbox">${[...asks.map((s) => `<a class="slug ask" href="#ask-${s.slug}">#${s.slug} ?</a>`), ...waiversToConfirm.map((r) => `<a class="slug ask" href="#rule-${r.slug}">no test for ${r.slug} ?</a>`)].join(' ')}</p>` : ''}
${bar}` : ''}
${plan.pointers.length ? `
<h2 id="elsewhere">Planned elsewhere — ${plural(plan.pointers.length, 'piece')}</h2>
<div class="pbox outside">${plan.pointers.map((p) => pointerHtml(p, plan)).join('')}</div>
<p class="legend">Each is planned, built and approved in its own repository, under this feature's name. This plan relies on it and holds none of it.</p>` : ''}
${outside.length ? `
<h2 id="outside">Outside the narratives — ${plural(outside.length, 'piece')}</h2>
<div class="pbox outside">${byBug(outside, outsideRow, (bug) => `<div class="pline bugrow"><span class="where"><a href="#${bug.anchor}"><span class="mark failing">bug</span></a></span><span class="clause"><b>${planInline(bug.title, plan)}</b></span></div>`).join('')}</div>
<p class="legend">No narrative${flows.length ? ' below' : ''} shows ${outside.length === 1 ? 'this piece' : 'these pieces'}: ${bugs.length ? `${outside.length === 1 ? 'its card stands' : 'their cards stand'} below in the order of plan.md, a bug at a time` : `${outside.length === 1 ? 'its card is' : 'their cards are'} the first of the pieces`}.</p>` : ''}
${flows.length ? `
<h2 id="flows">The change, in the ${flows.length === 1 ? 'narrative' : `${flows.length} narratives`} it lands in</h2>
<div class="flows">
${flows.map((f) => flowHtml(f, ctx)).join('\n')}
</div>
<p class="legend">Grey is what a step does today; the line under it is what changes there.${flows.some((f) => f.rows.some((r) => r.kind === 'newBuilt' || (r.kind === 'step' && r.changes.some((c) => 'built' in c)))) ? ' A line marked <span class="mark done">built</span> is the clause you approved, kept where it landed: the step above it is what the code tells now, and the hashes after it are the commits of its piece that changed the function it stands in.' : ''}${asks.length ? ` A piece marked <span class="slug ask">?</span> holds a point for you to confirm: ${asks.length} in all.` : ''}</p>` : ''}

<h2 id="plan">The ${bugs.length ? `${plural(bugs.length, 'bug')}, ` : ''}${plural(plan.pieces.length, 'piece')} — ${plural(places, 'place')} in the code, ${plural(toWrite, 'test')} to write${builtPlaces ? `, ${plural(builtPlaces, 'place')} built` : ''}</h2>
${byBug(cards, (s) => planPieceHtml(s, ctx), bugHead).join('\n')}
${planJourneyCasesHtml(plan)}
${planRulesHtml(plan)}
${across.length ? `
<h2 id="across">Decided across pieces</h2>
<div class="cards">${across.map((s) => `<section class="card" id="${s.anchor}"><h2>${srcLink(doc!.file, s.line, 1, s.title)}</h2>${mdBlocks(s.blocks, plan)}</section>`).join('')}</div>` : ''}
${REVIEW_SCRIPT}
`;
  const crumb = `comprehension · plans / ${esc(plan.feature)} · <b>generated</b> from ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'} at ${generatedAt}`;
  return pageHtml(`Plan — ${plan.feature}`, crumb, body, `${doc ? 'each piece\'s statement and reason hand-written in plan.md' : 'no hand-written input'}; the places from the <code>planned</code> calls under ${APP} and the <code>@planned</code> comments, the tests from the tagged titles, which step a change lands in from the reference case of each narrative`, dbCss);
}


// ── The delivery page: the lots, and what is not as approved ───────────────────

const deliveryPage = (feature: string) => `${feature}-delivery.html`;

/** A word of prose that is shaped like a symbol of the code: camelCase, PascalCase of two words, CONSTANT_CASE. */
const BARE_SYMBOL = /^(?:[a-z][a-z0-9]*[A-Z][A-Za-z0-9]*|[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*|[A-Z][A-Z0-9]*_[A-Z0-9_]+)$/;

/**
 * A line of the delivery page with its code linked: `#slug` to the piece, a backticked symbol and a bare word
 * shaped like one to its declaration — in one of `files` first (the places of the piece the line belongs to),
 * else the one of that name under `src/`, else a local or a property of that name near one of those places. A title names `describeTheCap` with no backticks, and a reader
 * wants to open it all the same. What resolves to nothing stays as it is written.
 */
function codeInline(text: string, plan: Plan, places: ReadonlyArray<{ file: string; line: number }>, index: SourceIndex): string {
  const files = [...new Set(places.map((p) => p.file))];
  const link = (name: string, shown: string) => {
    const bare = name.replace(/\(.*$/, '');
    const at = index.resolveUnscoped(bare, files) ?? index.resolveNear(bare, places);
    return at ? srcLink(at.file, at.line, at.column, shown) : null;
  };
  const known = new Set(plan.pieces.map((x) => x.slug));
  return text.split(/(`[^`]+`)/).map((part) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      const code = part.slice(1, -1);
      return link(code, code) ?? `<code>${esc(code)}</code>`;
    }
    const prose = replaceSlugRefs(esc(part), (slug) => (known.has(slug) ? `<a class="slug" href="#piece-${slug}">#${slug}</a>` : `#${slug}`)).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
    // Tags hold no word shaped like a symbol but their own attributes: only the text between them is read.
    return prose.split(/(<[^>]+>)/).map((chunk) => (chunk.startsWith('<') ? chunk : chunk.replace(/[A-Za-z_$][A-Za-z0-9_$]*/g, (word) => (BARE_SYMBOL.test(word) ? link(word, word) ?? word : word)))).join('');
  }).join('');
}

/** The places a piece has under `src/`: where a symbol its lines name is looked for first, and near which a
 *  local of that name is taken. */
const filesOf = (piece: PlanPiece | undefined) => [
  ...[...(piece?.sites ?? []), ...(piece?.statics ?? [])].map((x) => ({ file: x.file, line: x.line })),
  // A place that is code now is known by its file alone.
  ...[...(piece?.built.sites ?? []), ...(piece?.built.comments ?? [])].map((line) => ({ file: /^\S+ (\S+) /.exec(line)?.[1] ?? '', line: 1 })),
].filter((x) => layout.isApp(x.file));

/** What a line of the delta is, in the reader's words: the facet says how the plan stores it, this says what it is. */
const LINE_KIND: Record<string, string> = { statement: 'statement', reason: 'reason', question: 'question', text: 'text', waivers: 'waiver', pointers: 'planned elsewhere', lots: 'lot', cases: 'journey case', steps: 'story step', tests: 'test to write', [UNPLANNED]: 'beyond the plan', [NOTES]: 'note', [REPRODUCTIONS]: 'reproduction', [BESIDE]: 'at no place of the plan' };
const commentKind = (file: string, removes: boolean) => (removes ? 'test goes' : layout.isTest(file) ? 'test changes' : file.endsWith('.sql') ? 'migration' : /\.(?:md|html)$/.test(file) ? 'doc' : 'code');

/**
 * One unit's differences from the approved plan, as rows. `+` is in the plan now and was not approved; `−` was
 * approved and is no longer in the plan; a `−` and a `+` at the same place are one rewording, drawn `was` then
 * `now`. Each row opens with what the line is (`code`: a place the feature changes; `test to write`, `test
 * written`, `test changes`, `test goes`; `statement`, `reason`; `file`, a file a commit changed that no place
 * of the plan names). A line the plan still holds is drawn from its place: the file
 * and line as a link, the function, the clause's symbols. A line that is gone is its text.
 */
function deltaLinesHtml(lines: DeltaLine[], d: Pick<UnitDelta, 'kind' | 'name'>, plan: Plan, index: SourceIndex, moved = false): string {
  const piece = d.kind === 'piece' ? plan.pieces.find((x) => `#${x.slug}` === d.name) : undefined;
  const inline = (t: string) => codeInline(t, plan, filesOf(piece), index);
  const file = (f: string) => (existsSync(join(ROOT, f)) ? srcLink(f, 1, 1, basename(f), ` title="${esc(f)}"`) : esc(f));
  const fn = (f: string, name: string) => {
    const at = functionPlace(index, f, name);
    return at ? srcLink(at.file, at.line, at.column, name) : `<code>${esc(name)}</code>`;
  };
  const tag = (change: string) => (change === 'added' ? ' <span class="badge">new function</span>' : change === 'removed' ? ' <span class="badge">deleted</span>' : '');
  interface Row { sign: '+' | '−'; kind: string; html: string; at: string }
  const row = (facet: string, line: string, sign: Row['sign']): Row => {
    const site = /^(changed|added|removed|evidence) (\S+) in (\S+) — (.*)$/.exec(facet === 'sites' ? line : '');
    if (site) {
      const x = sign === '+' ? piece?.sites.find((o) => siteLineOf(o) === line) : undefined;
      // A place that was built and that its edit takes back: the code no longer does what the clause says.
      const back = sign === '−' && (piece?.takenBack.sites.includes(line) ?? false);
      return { sign, kind: back ? 'taken back' : 'code', at: `sites ${site[2]} ${site[3]}`, html: `${x ? placeLink(x.file, x.line, x.column) : file(site[2])} in ${fn(site[2], site[3])}${tag(site[1])} — ${inline(site[4])}` };
    }
    const comment = /^(changes|removes) (\S+) — (.*)$/.exec(facet === 'comments' ? line : '');
    if (comment) {
      const xs = sign === '+' ? (piece?.statics ?? []).filter((o) => `${o.removes ? 'removes' : 'changes'} ${o.file} — ${o.text}` === line) : [];
      const where = xs.length ? xs.map((x) => `${placeLink(x.file, x.line, x.column)}${x.on ? ` <small>${inline(x.on.replace(/^(?:it|test|describe) /, ''))}</small>` : ''}`).join(' · ') : file(comment[2]);
      const back = sign === '−' && (piece?.takenBack.comments.includes(line) ?? false);
      return { sign, kind: back ? 'taken back' : commentKind(comment[2], comment[1] === 'removes'), at: `comments ${comment[2]}`, html: `${where} — ${inline(comment[3])}` };
    }
    const test = /^(narrative|server|unit) (\S+) — (.*)$/.exec(facet === 'tests' ? line : '');
    if (test) {
      const t = sign === '+' ? piece?.todos.find((o) => `${o.tier} ${o.file} — ${o.title}${o.rule ? ` [${o.rule}]` : ''}` === line) : undefined;
      return { sign, kind: t?.written ? 'test written' : 'test to write', at: `tests ${test[2]}`, html: `${t ? placeLink(t.file, t.line, t.column) : file(test[2])} <small>${test[1]}</small> — ${inline(test[3])}` };
    }
    // A reproduction as written: its body as approved, and its body now when it was edited since.
    const reproduced = /^(\S+) — (.*) ⇒ (\S+)$/.exec(facet === REPRODUCTIONS ? line : '');
    if (reproduced) {
      const t = piece?.todos.find((o) => reproductionKeyOf(o) === `${reproduced[1]} — ${reproduced[2]}`);
      return { sign, kind: 'reproduction', at: `${REPRODUCTIONS} ${reproduced[1]} ${reproduced[2]}`, html: `${t ? placeLink(t.file, t.line, t.column) : file(reproduced[1])} — ${inline(reproduced[2])} <small>its body ${sign === '+' ? 'as it stands' : 'as approved'}: <code>${esc(reproduced[3])}</code></small>` };
    }
    // What a commit did and the plan did not say — a test it deleted, a file of the product it changed — and a
    // planned place it took off and wrote nothing at.
    // What a lot changed at no place of the plan, in a file the plan names: a function, or lines of a file
    // with none. Listed, and asked about only when an edit names it.
    const beside = /^(function|lines) (\S+) (?:in (\S+) )?— (.*)$/.exec(facet === BESIDE ? line : '');
    if (beside) return { sign, kind: 'at no place', at: `${BESIDE} ${line}`, html: `${file(beside[2])}${beside[3] ? ` in ${fn(beside[2], beside[3])}` : ''} — ${inline(beside[4])}` };
    const beyond = /^(file|test|place) (\S+) — (.*)$/.exec(facet === UNPLANNED ? line : '');
    if (beyond) return { sign, kind: beyond[1] === 'test' ? 'test goes' : beyond[1] === 'place' ? 'not built' : 'file', at: `${UNPLANNED} ${line}`, html: `${file(beyond[2])} — ${inline(beyond[3])}` };
    return { sign, kind: LINE_KIND[facet] ?? facet, at: facet, html: inline(line) };
  };
  const rows = lines.map((l) => row(l.facet, l.text, l.sign));
  const draw = (r: Row, cls: string, sign: string) => `<div class="dl ${cls}"><span class="sign">${sign}</span><span class="facet">${esc(r.kind)}</span><span>${r.html}</span></div>`;
  const drawn = new Set<Row>();
  return rows.map((r) => {
    if (drawn.has(r)) return '';
    const here = rows.filter((o) => o.at === r.at);
    // One line out and one line in at the same place: the place was reworded.
    if (here.length === 2 && here[0].sign !== here[1].sign) {
      const was = here.find((o) => o.sign === '−')!;
      const now = here.find((o) => o.sign === '+')!;
      drawn.add(was).add(now);
      return `${draw(was, 'rem', 'was')}${draw(now, 'add', 'now')}`;
    }
    return moved ? draw(r, 'moved', '→') : draw(r, r.sign === '+' ? 'add' : 'rem', r.sign);
  }).join('');
}

/** What moved from a piece to another, word for word: the same thing is planned, by another piece and maybe
 *  in another lot. Of second order: it is listed once, under where it went, and nothing is asked. */
function movesHtml(plan: Plan, index: SourceIndex): string {
  if (plan.moves.length === 0) return '';
  const lot = (name: string) => {
    const n = (plan.doc?.lots ?? []).findIndex((l) => l.pieces.includes(name.slice(1)));
    return n < 0 ? '' : ` <small>lot ${n + 1}</small>`;
  };
  const chip = (name: string) => `<a class="slug" href="#piece-${name.slice(1)}">${esc(name)}</a>${lot(name)}`;
  const row = (m: PlanMove) => `<div class="moverow"><div class="route">${chip(m.from)} → ${chip(m.to)}</div>${deltaLinesHtml([{ facet: m.facet, sign: '+', text: m.text }], { kind: 'piece', name: m.to }, plan, index, true)}</div>`;
  return `<details class="pbox moves"><summary><b>${plural(plan.moves.length, 'thing')} moved between pieces, unchanged</b> — the same is planned, by another piece: nothing to answer</summary>${plan.moves.map(row).join('')}</details>`;
}

/** The legend of the delta's rows. */
const DELTA_LEGEND = 'An edit at a time: what moved in bold, why, then the lines that edit comes to, then the commits it names: a hash opens its commit in VS Code, every file it changed in one diff. <span class="dl add inline"><span class="sign">+</span></span> in the plan now, not in what you approved · <span class="dl rem inline"><span class="sign">−</span></span> approved, no longer in the plan · <b>was / now</b> one place reworded · <b>file</b>, <b>test goes</b> on a <span class="dl add inline"><span class="sign">+</span></span> line with no place in the plan: what a commit did beyond it · <b>not built</b> a planned place taken off, in a function that gained no line since, or a file its commits added nothing to · <b>taken back</b> a place that read as built, which its edit names: the code does not do what its clause said · <b>at no place</b> a function the lot changed, or lines above a template\'s first place, that no place of the plan names: shown, and asked about only when an edit names it · <b>reproduction</b>, was / now: a test you approved as the bug\'s reproduction was edited since, by more than its declaration. A place that became code is no difference: it is listed with its piece, as built.';

/** The reviewer's answer to one item, and the buttons that give it. The page posts to the local app, which
 *  writes `plan-feedback.json`; opened as a file, the buttons are off and say where to open it. */
function verdictHtml(item: ReviewItem, plan: Plan): string {
  const given = plan.feedback[item.key];
  const state = given ? (given.verdict === 'approved' ? `approved` : `not approved: ${given.note}`) : '';
  const [yes, no, ask] = item.kind === 'question' ? ['Yes, as proposed', 'Answer…', 'Your answer'] : ['Approve', 'Not this…', 'What should change'];
  return `<div class="verdict" data-feature="${esc(plan.feature)}" data-key="${item.key}" data-unit="${esc(item.unit)}" data-what="${esc(item.what)}" data-state="${given?.verdict ?? ''}">`
    + `<button type="button" data-act="approve">${yes}</button><button type="button" data-act="open">${no}</button>`
    + `<span class="vstate">${esc(state)}</span><span class="vhint" hidden>open this page through <code>npm run comprehension</code> to answer here</span>`
    + `<span class="vform" hidden><textarea rows="2" placeholder="${ask}">${given?.verdict === 'refused' ? esc(given.note) : ''}</textarea><button type="button" data-act="send">Send</button></span></div>`;
}

/** A question that stands in `plan.md`, with the reviewer's answer under it. */
const askHtml = (item: ReviewItem, text: string, plan: Plan, id: string, commits = '') => `<div class="edit" id="${id}"><p class="ask"><span class="askmark">to confirm</span> ${text}</p>${commits}${verdictHtml(item, plan)}</div>`;

/** A piece's question on its card, of the plan page and of the delivery page: answered where it is stated, from
 *  the first draft on. The commits it names are listed under it: what was built the proposed way. */
function pieceAskHtml(piece: PlanPiece, plan: Plan): string {
  const item = pieceQuestion(piece);
  const ask = piece.doc?.ask;
  return item && ask ? askHtml(item, `<b>${planInline(ask.question, plan)}</b> ${planInline(ask.detail, plan)}`, plan, `ask-${piece.slug}`, namedCommitsHtml(ask.commits, plan, piece.slug)) : '';
}

/**
 * What of a unit is not as approved, an edit at a time: marked "changed" as a question is marked "to confirm",
 * then what moved, in bold, then why, then the lines that
 * edit comes to, then the commits it names, then the reviewer's answer. A question the unit raises is no line of it: it is drawn on the
 * piece's card. The lines no edit names follow — every line of a unit that says no `Changed:`; under several
 * edits they are flagged, since `--check` fails on them.
 */
function unitDeltaHtml(d: UnitDelta, plan: Plan, index: SourceIndex): string {
  const piece = plan.pieces.find((x) => `#${x.slug}` === d.name);
  const files = filesOf(piece);
  const items = editItems(d);
  const said = (c: PlanChange) => `<p class="chg"><span class="askmark">changed</span> ${c.what ? `<b>${codeInline(c.what, plan, files, index)}.</b> ` : ''}${codeInline(c.why, plan, files, index)} <small>${srcLink(plan.doc!.file, c.line, 1, 'plan.md')}</small></p>`;
  const need = d.reason === 'needed' ? `<p class="note red">Not as approved, and its section of plan.md says no <code>Changed:</code> — <code>--check</code> fails on it.</p>` : '';
  const edits = d.edits.map((e, n) => `<div class="edit">${said(e.change)}${e.lines.length ? `<div class="plines">${deltaLinesHtml(e.lines, d, plan, index)}</div>` : ''}${namedCommitsHtml(e.change.commits, plan, piece?.slug ?? null)}${verdictHtml(items[n], plan)}</div>`).join('');
  // A note is drawn with its piece, as a note: it is no line to answer.
  const lines = d.unclaimed.filter((l) => !isOwnNotice(l.facet));
  // A line no edit has to name is listed with no flag: what the lot changed at no place of the plan.
  const owed = d.edits.length > 1 && lines.some((l) => !asksNoEdit(l.facet));
  const loose = lines.length ? `${owed ? '<p class="note red">Lines no edit names:</p>' : ''}<div class="plines">${deltaLinesHtml(lines, d, plan, index)}</div>` : '';
  return `${need}${edits}${loose}`;
}

/** Where the review stands, and the one button that approves the plan once every item is approved and no
 *  question stands. Drawn while there is something to answer, and for a plan never approved. */
function reviewBarHtml(plan: Plan): string {
  const items = reviewItems(plan);
  if (items.length === 0 && plan.approved !== null) return '';
  const of = (verdict: string) => items.filter((i) => plan.feedback[i.key]?.verdict === verdict).length;
  const [yes, no] = [of('approved'), of('refused')];
  const asks = items.filter((i) => i.kind === 'question').length;
  const ready = yes === items.length && asks === 0;
  const blocked = ready ? '' : asks ? ` ${plural(asks, 'question')} still ${asks === 1 ? 'stands' : 'stand'} in plan.md: an answer becomes a statement there first.` : ' Every item is approved first.';
  const standing = items.length === 0 ? '<b>Nothing to answer.</b> '
    : `<b>${plural(items.length, 'item')} to answer</b> — ${yes} approved, ${no} not approved, ${items.length - yes - no} not read. Your answers go to <code>${esc(featureFolder(plan.feature))}/${FEEDBACK_FILE}</code>; the agent reads them with <code>npm run map -- feedback ${esc(plan.feature)}</code>. `;
  return `<div class="pbox review">${standing}`
    + `<button type="button" id="approve-plan" data-feature="${esc(plan.feature)}"${ready ? '' : ' disabled'}>Approve the plan</button> <span id="approve-state">${blocked}</span></div>`;
}

/** The answers' behaviour, the same on the plan page and the delivery page. */
const REVIEW_SCRIPT = `<script>
(function () {
  var served = location.protocol.indexOf('http') === 0;
  var post = function (path, body) { return fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); };
  document.querySelectorAll('.verdict').forEach(function (box) {
    var form = box.querySelector('.vform'), state = box.querySelector('.vstate'), area = form.querySelector('textarea');
    if (!served) { box.querySelector('.vhint').hidden = false; box.querySelectorAll('button').forEach(function (b) { b.disabled = true; }); return; }
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('button');
      if (!b) return;
      if (b.dataset.act === 'open') { form.hidden = false; area.focus(); return; }
      var verdict = b.dataset.act === 'approve' ? 'approved' : 'refused', note = verdict === 'refused' ? area.value.trim() : '';
      if (verdict === 'refused' && !note) { area.focus(); return; }
      post('/__feedback', { feature: box.dataset.feature, key: box.dataset.key, unit: box.dataset.unit, what: box.dataset.what, verdict: verdict, note: note }).then(function (res) {
        if (!res.ok) return res.text().then(function (t) { state.textContent = 'not saved: ' + t; });
        box.dataset.state = verdict; form.hidden = true;
        state.textContent = verdict === 'approved' ? 'approved' : 'not approved: ' + note;
      });
    });
  });
  var go = document.getElementById('approve-plan');
  if (go) {
    if (!served) go.disabled = true;
    go.addEventListener('click', function () {
      post('/__approve', { feature: go.dataset.feature }).then(function (res) { return res.text().then(function (t) { document.getElementById('approve-state').textContent = res.ok ? ' approved: ' + t : ' not approved: ' + t; }); });
    });
  }
})();
</script>`;

// ── What is built ──

/** A piece's notes: what it was built with that no line of the plan says, for whoever reads the code or builds
 *  on it. Read, never answered; one written since the approval is marked. */
function notesHtml(piece: PlanPiece, plan: Plan, inline: (text: string) => string): string {
  const fresh = new Set((plan.delta ?? []).filter((d) => d.name === `#${piece.slug}`).flatMap((d) => d.facets.filter((f) => f.facet === NOTES).flatMap((f) => f.added)));
  return (piece.doc?.notes ?? []).map((n) => `<p class="built-note"><span class="notemark">note</span> ${n.what ? `<b>${inline(n.what)}.</b> ` : ''}${inline(n.detail)}${fresh.has(n.text) ? ' <span class="badge">since approval</span>' : ''} <small>${srcLink(plan.doc!.file, n.line, 1, 'plan.md')}</small></p>`).join('');
}

/** The tests a commit of the piece deleted or changed as a comment of the plan said: the titles that comment
 *  stood on. The approval holds the comment's words, git the test it stood on. */
const builtTitles = (piece: PlanPiece, file: string, removes: boolean, text: string) => piece.commits.flatMap((c) => c.planned).filter((x) => x.file === file && x.removes === removes && x.text === text).map((x) => x.title);

/** Where a piece stands: nothing of it started, some of it code, or all of it — no place and no test left. */
function pieceState(piece: PlanPiece): { left: number; toWrite: number; built: number; started: boolean; done: boolean } {
  const left = piece.sites.length + piece.statics.length;
  const toWrite = piece.todos.filter(isOpenTest).length;
  // Evidence that went was no place to build: it started the piece, and is no place of it.
  const built = piece.built.sites.filter(isBuiltPlace).length + piece.built.comments.length;
  const started = built + piece.built.sites.length + piece.todos.filter((t) => t.written).length + piece.commits.length > 0;
  return { left, toWrite, built, started, done: started && left + toWrite === 0 };
}

/**
 * What the approval held of a piece and is code now, a row a line: the file and the function where the change
 * stands today, then the clause as approved. A comment on a test is read in the lot's ledger, beside the other
 * tests, and is left out when `tests` is false.
 */
function builtLinesHtml(piece: PlanPiece, plan: Plan, index: SourceIndex, tests = true): string {
  const inline = (t: string) => codeInline(t, plan, filesOf(piece), index);
  const file = (f: string) => (existsSync(join(ROOT, f)) ? srcLink(f, 1, 1, basename(f), ` title="${esc(f)}"`) : `<span title="${esc(f)} is deleted">${esc(basename(f))}</span>`);
  const row = (mark: string, where: string, clause: string) => `<div class="pline built"><span class="mark done">${mark}</span><span class="where">${where}</span><span class="clause">${clause}</span></div>`;
  const rows: string[] = [];
  for (const line of piece.built.sites) {
    const m = /^(changed|added|removed) (\S+) in (\S+) — (.*)$/.exec(line);
    if (!m) continue;
    const at = markOf(piece, line) ?? functionPlace(index, m[2], m[3]);
    rows.push(row('built', `${at ? placeLink(at.file, at.line, at.column) : file(m[2])} <code>${esc(m[3])}</code>${placeId(Object.keys(piece.ids).find((place) => piece.ids[place] === line))}${m[1] === 'added' ? ' <span class="badge">new function</span>' : ''}`, inline(m[4])));
  }
  for (const line of piece.built.comments) {
    const m = /^(changes|removes) (\S+) — (.*)$/.exec(line);
    if (!m) continue;
    const onTest = layout.isTest(m[2]);
    if (onTest && !tests) continue;
    const titles = onTest ? builtTitles(piece, m[2], m[1] === 'removes', m[3]) : [];
    rows.push(row(m[1] === 'removes' ? 'deleted' : onTest ? 'changed' : 'built', `${file(m[2])}${titles.length ? ` <small>${titles.map(esc).join(' · ')}</small>` : ''}`, inline(m[3])));
  }
  return rows.join('');
}

/** A commit's subject, short: its `[TAG]` taken off, cut at the first dash and at 16 words. */
function subjectHead(subject: string): string {
  const w = subject.replace(/^\[[A-Z]+\]\s*/, '').split(' — ')[0].split(/\s+/);
  return w.length > 16 ? `${w.slice(0, 16).join(' ')} …` : w.join(' ');
}

/** The commits that deliver a piece, oldest first: the hash, the subject, then each file it touched as a link to
 *  the first line it changed there, the product's code first. A commit made since the approval says so: what it
 *  did beyond the plan is in the piece's delta until the next approval. They stand in blocks (`commitBlocksHtml`). */
function commitsHtml(piece: PlanPiece, plan: Plan): string {
  if (piece.commits.length === 0) return '';
  return `<div class="commits">${commitBlocksHtml(piece.commits, plan, piece.slug)}</div>`;
}

/** Commits in blocks that each read as one diff (`commitBlocks`), oldest first; a block of several commits opens
 *  as that diff: the `commits` route of the plan-review-links extension, each file from before the block to what
 *  it left. The commits are one block, unless another commit changed one of their files between two of them:
 *  the list then says which commit, and which file, before the block that follows. `home` is the piece they are
 *  listed for, the title of the diff with the feature. */
function commitBlocksHtml(commits: PieceCommit[], plan: Plan, home: string | null): string {
  const blocks = commitBlocks(commits, plan.history);
  const shaLink = (sha: string) => `<a class="csha" href="vscode://local.plan-review-links/commit?sha=${sha}" title="Open the commit in VS Code — in a terminal: git show ${sha.slice(0, 8)}"><code>${sha.slice(0, 8)}</code></a>`;
  const list = (items: string[]) => (items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`);
  const parted = (block: CommitBlock) => {
    const others = block.after.map((touch) => {
      const pieces = commitsNamed(plan.commits, touch.sha)[0]?.pieces ?? [];
      return `${shaLink(touch.sha)}${pieces.length ? ` <small>of ${pieces.map((x) => `#${esc(x)}`).join(' ')}</small>` : ''} changed ${list(touch.files.map((f) => `<code title="${esc(f)}">${esc(basename(f))}</code>`))}`;
    });
    return `<p class="cpart">Not one diff with the commits above: between them, ${others.join('; ')}.</p>`;
  };
  const title = encodeURIComponent(home === null ? plan.feature : `${plan.feature}#${home}`);
  return blocks.map((block, n) => {
    const shas = block.commits.map((c) => c.sha.slice(0, 12)).join(',');
    const first = block.commits[0].sha.slice(0, 8);
    const last = block.commits[block.commits.length - 1].sha.slice(0, 8);
    const whole = blocks.length === 1 ? `The ${block.commits.length} commits` : `These ${block.commits.length} commits`;
    const open = block.commits.length < 2 ? ''
      : `<p class="cblock"><a class="csum" href="vscode://local.plan-review-links/commits?shas=${shas}&amp;title=${title}" title="Open in VS Code what these commits come to, each file once: from before the first of them that changed it to what the last left. No other commit changed these files between them — in a terminal, a file at a time: git diff ${first}^ ${last} -- &lt;file&gt;">${whole} as one diff</a></p>`;
    return `${n > 0 ? parted(block) : ''}${open}${block.commits.map((c) => commitRowHtml(c, plan, home)).join('')}`;
  }).join('');
}

/** One commit: its hash, which opens it in the editor with every file it changed in one diff (the `commit`
 *  route of the plan-review-links extension, which finds the commit in the open workspace), its subject, the
 *  pieces it names beside `home`, the piece it is listed for, and its files. */
function commitRowHtml(c: PieceCommit, plan: Plan, home: string | null): string {
  const named = filesNamed(plan.snapshot);
  const product = (f: string) => layout.isProduct(f);
  const fileHtml = (x: PieceCommit['files'][number]) => `<span class="cfile">${x.line === null ? `<s title="${esc(x.file)}">${esc(basename(x.file))}</s>` : placeLink(x.file, x.line)} <small>+${x.added} −${x.removed}${product(x.file) && !named.has(x.file) ? ' · no place of the plan names it' : ''}</small></span>`;
  const files = [...c.files].sort((a, b) => Number(product(b.file)) - Number(product(a.file)));
  const list = files.map(fileHtml).join('');
  const others = c.pieces.filter((x) => x !== home);
  const short = c.sha.slice(0, 8);
  return `<div class="crow"><a class="csha" href="vscode://local.plan-review-links/commit?sha=${c.sha}" title="Open the commit in VS Code, every file it changed in one diff — in a terminal: git show ${short}"><code>${short}</code></a><span>${esc(subjectHead(c.subject))}${others.length ? ` <small>${home !== null && c.pieces.includes(home) ? 'also' : 'a commit of'} ${others.map((x) => `#${esc(x)}`).join(' ')}</small>` : ''}${c.sinceApproval ? ' <span class="badge">since approval</span>' : ''}</span>`
    + `${files.length > 8 ? `<details class="cfiles"><summary>${plural(files.length, 'file')}</summary>${list}</details>` : `<div class="cfiles">${list}</div>`}</div>`;
}

/** The commits a paragraph names, under it: what was built as it says. They stand in blocks, oldest first, as a
 *  piece's do (`commitBlocksHtml`), whatever order the paragraph names them in. A hash no commit of the feature
 *  has, or that several open with, says so after them; `--check` fails on it. */
function namedCommitsHtml(hashes: string[], plan: Plan, home: string | null): string {
  if (hashes.length === 0) return '';
  const found = hashes.map((hash) => ({ hash, commits: commitsNamed(plan.commits, hash) }));
  const named = new Set(found.filter((x) => x.commits.length === 1).map((x) => x.commits[0].sha));
  const commits = plan.commits.filter((c) => named.has(c.sha));
  const flags = found.filter((x) => x.commits.length !== 1).map(({ hash, commits: all }) =>
    `<div class="crow"><code>${esc(hash.slice(0, 8))}</code><span class="flag">${all.length === 0 ? 'no commit of the feature has this hash' : `${all.length} commits of the feature open with this hash`}</span></div>`);
  return `<div class="commits named">${commits.length ? commitBlocksHtml(commits, plan, home) : ''}${flags.join('')}</div>`;
}

/** A lot's tests: to write, to change, to delete — each deletion beside what holds it — then its journey cases.
 *  What is done stays listed, greyed: a test written, and a test a commit deleted or changed as planned. */
function ledgerHtml(plan: Plan, lot: PlanLot | null, pieces: PlanPiece[], index: SourceIndex): string {
  const inline = (piece: PlanPiece, text: string) => codeInline(text, plan, filesOf(piece), index);
  const chip = (slug: string) => `<a class="slug" href="#piece-${slug}">#${slug}</a>`;
  const isNew = (piece: PlanPiece, line: string, facet: string) => (plan.delta ?? []).some((d) => d.name === `#${piece.slug}` && d.facets.some((f) => f.facet === facet && f.added.includes(line)));
  const fresh = '<span class="badge">since approval</span>';
  const title = (piece: PlanPiece, site: StaticSite) => (site.on ? inline(piece, site.on.replace(/^(?:it|test|describe) /, '')) : '<small>the code under the comment</small>');
  const todos = pieces.flatMap((piece) => piece.todos.map((t) => ({ piece, t })));
  const inTests = pieces.flatMap((piece) => piece.statics.filter((x) => layout.isTest(x.file)).map((x) => ({ piece, x })));
  const going = inTests.filter(({ x }) => x.removes);
  // A comment that stands on a planned test is a note on that test, not one more test that changes: how it is to
  // be written, or that it is an existing case extended and retitled (its note ends "no case is added"), which
  // is then a test that changes and no test to write. Each test is listed once.
  const fullTitle = (t: PlanTodo) => `${t.feature}#${t.slug}: ${t.title}${t.rule ? ` [${t.rule}]` : ''}`;
  const notes = new Map<PlanTodo, StaticSite[]>();
  const changing = inTests.filter(({ x }) => {
    if (x.removes) return false;
    const stoodOn = /^(?:it|test) "(.*)"$/.exec(x.on ?? '')?.[1];
    const target = stoodOn === undefined ? undefined : todos.find(({ t }) => fullTitle(t) === stoodOn);
    if (!target) return true;
    notes.set(target.t, [...(notes.get(target.t) ?? []), x]);
    return false;
  });
  const extends_ = (t: PlanTodo) => (notes.get(t) ?? []).some((x) => /\bno case is added\b/.test(x.text));
  const notesHtml = (piece: PlanPiece, t: PlanTodo, lead: string) => (notes.get(t) ?? []).map((x) => `<br><small>${lead}${inline(piece, x.text)}</small>`).join('');
  const cases = lot ? plan.journeyCases.filter((c) => lot.screens.includes(c.screen)) : [];
  const block = (head: string, rows: string[]) => {
    const done = rows.filter((r) => r.startsWith('<div class="lrow done"')).length;
    return rows.length ? `<h3>${head} — ${rows.length}${done ? `, ${done} done` : ''}</h3>${rows.join('')}` : '';
  };
  // What a commit already did as the plan said: the approval holds the comment's words, git the test.
  const builtTests = pieces.flatMap((piece) => piece.built.comments.flatMap((line) => {
    const m = /^(changes|removes) (tests\/\S+) — (.*)$/.exec(line);
    return m ? [{ piece, removes: m[1] === 'removes', file: m[2], text: m[3], titles: builtTitles(piece, m[2], m[1] === 'removes', m[3]) }] : [];
  }));
  const builtRow = (b: typeof builtTests[number]) => `<div class="lrow done"><span class="mark">${b.removes ? 'deleted' : 'changed'}</span><span><b>${b.titles.map((t) => inline(b.piece, t)).join(' · ') || '<small>the test the comment stood on</small>'}</b><br>${inline(b.piece, b.text)}</span><span class="where">${existsSync(join(ROOT, b.file)) ? srcLink(b.file, 1, 1, basename(b.file), ` title="${esc(b.file)}"`) : esc(basename(b.file))} ${chip(b.piece.slug)}</span></div>`;
  const builtCases = lot ? plan.builtCases.flatMap((line) => {
    const m = /^(.*) · (\S+) — (.*)$/.exec(line);
    return m && lot.screens.includes(m[2]) ? [`<div class="lrow done"><span class="mark">written</span><span>${clauseInline(m[3])}</span><span class="where"><small>${esc(m[2])}</small></span></div>`] : [];
  }) : [];
  // A reproduction was written before the approval: it is no test to write. It is owed until it passes.
  const reproduces = ({ piece, t }: typeof todos[number]) => t.reproduction || piece.reproduced.includes(reproductionKeyOf(t));
  const out = [
    block('Reproductions, to make pass', todos.filter(reproduces).map(({ piece, t }) => `<div class="lrow${t.reproduction ? '' : ' done'}"><span class="mark">${t.reproduction ? 'fails today' : 'passes'}</span><span>${inline(piece, t.title)}${t.rule ? ` <span class="rule">${esc(t.rule)}</span>` : ''}</span><span class="where">${placeLink(t.file, t.line, t.column)} ${chip(piece.slug)}</span></div>`)),
    block('Tests to write', todos.filter((x) => !extends_(x.t) && !reproduces(x)).map(({ piece, t }) => `<div class="lrow${t.written ? ' done' : ''}"><span class="mark">${t.written ? 'written' : t.tier}</span><span>${inline(piece, t.title)}${t.rule ? ` <span class="rule">${esc(t.rule)}</span>` : ''} ${isNew(piece, `${t.tier} ${t.file} — ${t.title}${t.rule ? ` [${t.rule}]` : ''}`, 'tests') ? fresh : ''}${notesHtml(piece, t, 'how it is written: ')}</span><span class="where">${placeLink(t.file, t.line, t.column)} ${chip(piece.slug)}</span></div>`)),
    block('Tests that change', [...todos.filter(({ t }) => extends_(t)).map(({ piece, t }) => `<div class="lrow"><span class="mark">change</span><span><b>${inline(piece, t.title)}</b>${t.rule ? ` <span class="rule">${esc(t.rule)}</span>` : ''}${notesHtml(piece, t, 'an existing test, extended and retitled — ')}</span><span class="where">${placeLink(t.file, t.line, t.column)} ${chip(piece.slug)}</span></div>`), ...changing.map(({ piece, x }) => `<div class="lrow"><span class="mark">change</span><span><b>${title(piece, x)}</b><br>${inline(piece, x.text)} ${isNew(piece, `changes ${x.file} — ${x.text}`, 'comments') ? fresh : ''}</span><span class="where">${placeLink(x.file, x.line, x.column)} ${chip(piece.slug)}</span></div>`), ...builtTests.filter((b) => !b.removes && b.titles.length).map(builtRow)]),
    block('Tests that go', going.map(({ piece, x }) => `<div class="lrow go"><span class="mark">delete</span><span><b>${title(piece, x)}</b><br>${inline(piece, x.text)} ${isNew(piece, `removes ${x.file} — ${x.text}`, 'comments') ? fresh : ''}</span><span class="where">${placeLink(x.file, x.line, x.column)} ${chip(piece.slug)}</span></div>`).concat(builtTests.filter((b) => b.removes).map(builtRow))),
    block('Journey cases, written last', [...cases.map((c) => `<div class="lrow"><span class="mark">journey</span><span>${clauseInline(c.title)}</span><span class="where">${placeLink(c.file, c.line, c.column)} <small>${esc(c.screen)}</small></span></div>`), ...builtCases]),
  ].join('');
  return out ? `<div class="pbox ledger">${out}</div>` : '<p class="legend">No test planned, changed or removed.</p>';
}

/** A piece on the delivery page: its statement, a link to its card on the plan page, and what of it is not as approved. */
function deliveryPieceHtml(piece: PlanPiece | undefined, slug: string, plan: Plan, index: SourceIndex): string {
  const d = (plan.delta ?? []).find((x) => x.kind === 'piece' && x.name === `#${slug}`);
  const card = `<a class="slug big" href="${esc(plan.feature)}.html#piece-${slug}" title="its card on the plan page">#${slug}</a>`;
  if (!piece) return `<section class="piece" id="piece-${slug}"><header>${card}<small>nothing of it is planned any more: its sites are code</small></header>${d ? `${unitDeltaHtml(d, plan, index)}` : ''}</section>`;
  const { left, toWrite, built, started, done } = pieceState(piece);
  const state = done ? `<b class="ok">built</b>${piece.commits.length ? `, in ${plural(piece.commits.length, 'commit')}` : ' · <span class="flag">no commit names it</span>'}`
    : `${plural(left, 'place')} and ${plural(toWrite, 'test')} to go${started ? ` · ${plural(built, 'place')} built` : ''}`;
  const builtLines = builtLinesHtml(piece, plan, index, false);
  return `
<section class="piece${d ? ' moved' : ''}${done ? ' built' : ''}" id="piece-${slug}">
  <header>${card}<small>${state}${d ? ` · <b>${d.state === 'new' ? 'new' : 'modified'} since your approval</b>` : ' · as approved'}</small></header>
  ${piece.doc ? `<p class="what">${codeInline(piece.doc.what, plan, filesOf(piece), index)}</p>` : ''}
  ${notesHtml(piece, plan, (t) => codeInline(t, plan, filesOf(piece), index))}
  ${pieceAskHtml(piece, plan)}
  ${d ? `${unitDeltaHtml(d, plan, index)}` : ''}
  ${fixedBugHtml(piece, plan)}
  ${builtLines ? `<div class="plines">${builtLines}</div>` : ''}
  ${commitsHtml(piece, plan)}
</section>`;
}

/**
 * The delivery page of a plan: what the reviewer reads to approve again, then the lots in order. On top, every
 * unit that is not as approved — the pieces as links to their place in a lot, the rest in full. Then a lot a
 * section: its reason, what it still owes, its tests (to write, to change, to delete beside what holds each),
 * and its pieces with what moved in each. Drawn once the plan is approved or has a delivery.
 */
export function renderDeliveryPage(plan: Plan, stories: Story[], index: SourceIndex): string {
  const generatedAt = new Date().toISOString();
  const doc = plan.doc!;
  const lots = doc.lots;
  const delta = plan.delta ?? [];
  const inLot = new Set(lots.flatMap((l) => l.pieces));
  const loose = plan.pieces.filter((x) => !inLot.has(x.slug));
  const owes = (lot: PlanLot) => {
    const left = lotLeft(plan, lot);
    const pieces = plan.pieces.filter((x) => lot.pieces.includes(x.slug));
    const built = pieces.filter((x) => pieceState(x).done).length;
    return left.sites + left.tests + left.cases === 0 ? 'delivered' : `${plural(left.sites, 'place')}, ${plural(left.tests, 'test')} and ${plural(left.cases, 'journey case')} to go${built ? ` · ${built} of ${plural(pieces.length, 'piece')} built` : ''}`;
  };
  const unitLink = (d: UnitDelta) => (d.kind === 'piece' ? `<a class="slug${d.reason === 'needed' ? ' ask' : ''}" href="#piece-${d.name.slice(1)}">${esc(d.name)}</a>` : `<a href="#unit-${anchorFor(d.name)}">${esc(d.name)}</a>`);
  const count = (d: UnitDelta) => d.facets.map((f) => `${esc(f.facet === 'sites' ? 'code' : f.facet === 'comments' ? 'tests and types' : f.facet === 'tests' ? 'tests to write' : LINE_KIND[f.facet] ?? f.facet)}${f.added.length ? ` +${f.added.length}` : ''}${f.removed.length ? ` −${f.removed.length}` : ''}`).join(', ');
  const others = delta.filter((d) => d.kind !== 'piece');
  // The rules are drawn on the plan page: a waiver to confirm is answered here too, under the bar.
  const answers = `${reviewBarHtml(plan)}${doc.waivers.filter((w) => w.toConfirm).map((w) => askHtml(waiverQuestion(w), `<b>No test holds <span class="rule">${esc(w.rule)}</span>.</b> ${planInline(w.reason, plan)}`, plan, `ask-rule-${w.rule}`)).join('')}`;
  const since = plan.approved === null
    ? `<h2 id="since">Never approved</h2><p class="pbox">On the reviewer's word: <code>${esc(typed(config.commands.tool, SELF))} --approve ${esc(plan.feature)}</code>. From then on this block lists what moved.</p>${answers}`
    : `
<h2 id="since">Since your approval — ${delta.length === 0 ? 'nothing moved' : `${plural(delta.length, 'unit')} not as approved`}</h2>
<p class="legend">Approved on ${esc(plan.approved.approvedOn)} at <code>${esc(plan.approved.base.slice(0, 8))}</code>. Everything below compares the plan as it stands with the plan you approved, never with the code. ${DELTA_LEGEND}${delta.length ? ` To approve again: <code>${esc(typed(config.commands.tool, SELF))} --approve ${esc(plan.feature)}</code>.` : ''}</p>
${answers}
${delta.length ? `<div class="pbox">${delta.map((d) => `<div class="pline"><span class="mark">${d.state === 'changed' ? 'modified' : d.state}</span><span class="where">${unitLink(d)}</span><span class="clause">${count(d)}${d.reason === 'needed' ? ' <span class="flag">no "Changed:"</span>' : ''}</span></div>`).join('')}</div>` : ''}
${movesHtml(plan, index)}
${others.map((d) => `<section class="piece moved" id="unit-${anchorFor(d.name)}"><header><b>${esc(d.name)}</b><small>${d.kind} · ${d.state === 'changed' ? 'modified' : d.state} since your approval</small></header>${unitDeltaHtml(d, plan, index)}</section>`).join('')}`;
  const lotHtml = (lot: PlanLot, n: number) => `
<h2 id="lot-${lot.slug}">Lot ${n} — ${esc(lot.slug)} <small>${lot.difficulty} · ${owes(lot)}</small></h2>
<p class="lede">${planInline(lot.reason, plan)}</p>
${ledgerHtml(plan, lot, plan.pieces.filter((x) => lot.pieces.includes(x.slug)), index)}
${lot.pieces.map((slug) => deliveryPieceHtml(plan.pieces.find((x) => x.slug === slug), slug, plan, index)).join('\n')}`;
  const body = `
<h1>${esc(doc.title.replace(/\s+[—–-]\s+plan$/i, ''))} — delivery</h1>
<p class="lede">What is not as you approved it, then the lots in the order they are delivered: one implementer and one review a lot, one commit a piece. A piece that is built lists the places that became code, each where it stands today, and its commits, which open as the one diff they come to. The design is on <a href="${esc(plan.feature)}.html">the plan page</a>.${lots.length ? ` ${lots.map((l, i) => `<a href="#lot-${l.slug}">${i + 1} · ${esc(l.slug)}</a>`).join(' → ')}` : ''}</p>
${since}
${lots.length ? lots.map((l, i) => lotHtml(l, i + 1)).join('\n') : `<h2>No delivery yet</h2><p class="pbox">plan.md holds no "## Delivery": the tasks stage writes it.</p>`}
${loose.length && lots.length ? `<h2 id="loose">In no lot</h2>${ledgerHtml(plan, null, loose, index)}${loose.map((x) => deliveryPieceHtml(x, x.slug, plan, index)).join('\n')}` : ''}
${REVIEW_SCRIPT}
`;
  const crumb = `comprehension · plans / ${esc(plan.feature)} / delivery · <b>generated</b> from ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'} at ${generatedAt}`;
  return pageHtml(`Delivery — ${plan.feature}`, crumb, body, 'the lots hand-written in plan.md § "Delivery", each <code>Changed:</code> in its section; the approval read from plan.approved.json; every other line from the <code>planned</code> calls, the <code>@planned</code> comments and the tagged test titles; a piece\'s commits from git, by the line <code>Piece: feature#piece</code> of their message.');
}

const anchorFor = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

export function renderNarrativePage(narrative: Narrative, stories: Story[], narratives: Narrative[], index: SourceIndex, backlinks: BacklinkIndex): string {
  const generatedAt = new Date().toISOString();
  const body = `
<h1>${esc(narrative.title)}</h1>
<p class="lede">${esc(narrative.summary)} <small>A product narrative, declared by ${srcLink(narrative.file, narrative.declaredAt, 1, narrative.file)}; nothing on this page is hand-written.</small></p>
${LINK_HINT}
<h2 id="structure">Rides on</h2>
${ridesOnHtml([narrative], narratives, index, PRODUCT_LINKS)}

<h2 id="narratives">Narrative</h2>
${narrativeHtml(narrative, stories, narratives, index, PRODUCT_LINKS, backlinks)}
`;
  const crumb = `comprehension · narratives / ${esc(narrative.slug)} · <b>generated</b> from ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'} at ${generatedAt} · <a href="../index.html">every page</a>`;
  return pageHtml(narrative.title, crumb, body, 'no hand-written input; the narrative from the test that declares it; every step, link, chip, stop and value from the run, every symbol link from the source index, every "rides on" from the mechanisms\' own stories, every debt / rule / convention marker from the pages that name the code.');
}

export function renderMechanismPage(mechanism: Narrative, stories: Story[], narratives: Narrative[], index: SourceIndex, backlinks: BacklinkIndex): string {
  const generatedAt = new Date().toISOString();
  const body = `
<h1>${esc(mechanism.title)}</h1>
<p class="lede">${esc(mechanism.summary)} <small>A mechanism narrative: the sites are the mechanism's own code, declared by ${srcLink(mechanism.file, mechanism.declaredAt, 1, mechanism.file)}; nothing on this page is hand-written.</small></p>
${LINK_HINT}
<h2 id="narratives">Narrative</h2>
${narrativeHtml(mechanism, stories, narratives, index, MECHANISM_LINKS, backlinks)}
`;
  const crumb = `comprehension · mechanisms / ${esc(mechanism.slug)} · <b>generated</b> from ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'} at ${generatedAt} · <a href="../index.html">every page</a>`;
  return pageHtml(mechanism.title, crumb, body, 'no hand-written input; the narrative from the test that declares it; every step, link, chip, stop and value from the run, every symbol link from the source index.');
}

/** A generated page, as the index lists it: its path from the folder the list is read from, and its own title. */
export interface ListedPage { href: string; title: string }

/** Every generated page on disk, by kind, each with the path from `from` and the title it gives itself. A spec page
 *  is listed when it is a generated one: a feature folder may hold a hand-written `spec.html` of an earlier method. */
export function generatedPages(from: string): Array<{ kind: string; pages: ListedPage[] }> {
  const htmlOf = (dir: string, keep: (f: string) => boolean = () => true) => (existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith('.html') && !f.endsWith('.skeleton.html') && keep(f)).sort().map((f) => join(dir, f)) : []);
  // A page's own title, without what every generated page's title says.
  const titled = (file: string): ListedPage => ({ href: relative(from, file), title: /<title>([^<]*)<\/title>/.exec(readFileSync(file, 'utf8'))?.[1].replace(/^.*? comprehension — | \(generated\)$/g, '').trim() || relative(from, file) });
  const features = join(ROOT, FEATURES);
  const specs = existsSync(features) ? readdirSync(features).map((f) => join(features, f, 'spec.html')).filter((f) => existsSync(f) && readFileSync(f, 'utf8').includes('<meta name="generator"')).sort() : [];
  return [
    { kind: 'Narratives', pages: htmlOf(NARRATIVES_DIR) },
    { kind: 'Mechanisms', pages: htmlOf(MECHANISMS_DIR) },
    { kind: 'Plans', pages: htmlOf(PLANS_DIR, (f) => !f.endsWith('-delivery.html')) },
    { kind: 'Deliveries', pages: htmlOf(PLANS_DIR, (f) => f.endsWith('-delivery.html')) },
    { kind: 'Journeys', pages: htmlOf(join(ROOT, JOURNEYS)) },
    { kind: 'Specs', pages: specs },
  ].map(({ kind, pages }) => ({ kind, pages: pages.map(titled) })).filter((group) => group.pages.length > 0);
}

/** The list of every generated page, by kind. `prefix` goes before each path: `/` where a server serves it from the
 *  documents' folder, nothing in the file under the pages' folder. */
export function renderIndexPage(groups: Array<{ kind: string; pages: ListedPage[] }>, prefix = ''): string {
  const list = groups.map(({ kind, pages }) => `<h2>${kind}</h2><ul>${pages.map((x) => `<li><a href="${esc(prefix + x.href)}">${esc(x.title)}</a> <small>${esc(x.href)}</small></li>`).join('')}</ul>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="generator" content="${esc(SELF)}"><title>${esc(config.name)} — generated pages</title>
<style>body{font:15px/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem}h2{font-size:1rem;margin:1.4rem 0 .3rem}ul{margin:0;padding-left:1.2rem}small{color:#6b7280;margin-left:.4rem}</style></head>
<body><h1>${esc(config.name)} — generated pages</h1>${HUB ? `<p>${HUB}</p>` : ''}${list || '<p>No page yet: the first render follows the first test run.</p>'}</body></html>
`;
}

/** `diffs` are the database diffs of the plans' proposed migrations (`planDbDiffs`, the one part that is async
 *  and wants the local stack); a plan page drawn without them says so under the piece. `sources` is the scan
 *  both were made from, when the caller already has it. */
export function render(source: SourceReader = openSource(), diffs: DbDiffs = new Map(), sources: PlanSources = readPlanSources()): { stories: number; pages: string[] } {
  const stories = readStories();
  const index = new SourceIndex(source);
  index.realign(stories);
  const narratives = deriveNarratives(stories, index);
  const backlinks = buildBacklinks(index, ROOT);
  const pages: string[] = [];
  // One page per narrative, in the folder of its kind; a page whose narrative is gone is removed.
  for (const [dir, kind] of [[NARRATIVES_DIR, 'product'], [MECHANISMS_DIR, 'mechanism']] as const) {
    mkdirSync(dir, { recursive: true });
    const own = narratives.filter((n) => n.kind === kind);
    const kept = new Set(own.map((n) => `${n.slug}.html`));
    // A `*.skeleton.html` is a hand-written head of an earlier version of these pages: never generated, never removed here.
    for (const f of readdirSync(dir)) if (f.endsWith('.html') && !f.endsWith('.skeleton.html') && !kept.has(f)) rmSync(join(dir, f));
    for (const n of own) {
      const out = join(dir, `${n.slug}.html`);
      writeFileSync(out, kind === 'product' ? renderNarrativePage(n, stories, narratives, index, backlinks) : renderMechanismPage(n, stories, narratives, index, backlinks));
      pages.push(relative(ROOT, out));
    }
  }
  // One plan page per feature with a planned site of any kind; a page whose feature has none left is removed.
  const plans = derivePlans(stories, narratives, index, sources);
  mkdirSync(PLANS_DIR, { recursive: true });
  const delivered = (p: Plan) => p.doc !== null && (p.approved !== null || p.doc.lots.length > 0);
  const kept = new Set(plans.flatMap((p) => [`${p.feature}.html`, ...(delivered(p) ? [deliveryPage(p.feature)] : [])]));
  for (const f of readdirSync(PLANS_DIR)) if (f.endsWith('.html') && !kept.has(f)) rmSync(join(PLANS_DIR, f));
  for (const p of plans) {
    const out = join(PLANS_DIR, `${p.feature}.html`);
    writeFileSync(out, renderPlanPage(p, stories, narratives, index, diffs));
    pages.push(relative(ROOT, out));
    if (!delivered(p)) continue;
    const delivery = join(PLANS_DIR, deliveryPage(p.feature));
    writeFileSync(delivery, renderDeliveryPage(p, stories, index));
    pages.push(relative(ROOT, delivery));
  }
  writeFileSync(INDEX_PAGE, renderIndexPage(generatedPages(dirname(INDEX_PAGE))));
  pages.push(relative(ROOT, INDEX_PAGE));
  return { stories: stories.length, pages };
}

// ── `--strip`: what the archive of a feature takes off the code ────────────────

export interface StripReport {
  /** What was taken off, a file each, by the line it stood at. */
  files: Array<{ file: string; taken: Stripped['taken'] }>;
  /** The lines that still name the feature, outside its folder. `code`: in a test or a file of the product,
   *  where the tools would read it as a mark of a feature that no longer exists. */
  remains: Array<{ file: string; line: number; text: string; code: boolean }>;
  /** Whether the stack gives a strip: without one, everything is in `remains`. */
  stripped: boolean;
}

/**
 * Takes a feature's marks off the code, once its archive gate passes: each `built` call, the tag and the rule
 * of each test title, each planned screen of a journey (`Stack.strip`). Then reads every file outside the
 * feature's folder for a line that still names a tag of it or a path into the folder. Refuses, with nothing
 * written, while the gate fails: a mark is what a place still to build or a rule with no owner is read by.
 * With `write` false nothing is written, and the report says what would go and what would be left.
 */
export function stripFeature(feature: string, write: boolean, source: SourceReader = openSource()): StripReport {
  const folder = featureFolder(feature);
  // The tracked files and the new ones git does not ignore, the feature's own folder left out.
  let listed = '';
  try {
    listed = execFileSync('git', ['grep', '-l', '-z', '-I', '-F', '--untracked', '-e', feature, '--', '.', `:(exclude)${folder}`], { cwd: ROOT, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  } catch (error) {
    // `git grep` exits 1 when no file holds the word.
    if ((error as { status?: number }).status !== 1) throw error;
  }
  const files = listed.split('\0').filter((f) => f && existsSync(join(ROOT, f))).sort();
  const read = files.map((file) => {
    const text = readFileSync(join(ROOT, file), 'utf8');
    const done = strip(file, text, feature);
    return { file, text, after: done?.text ?? text, taken: done?.taken ?? [], stripped: done !== null };
  });
  const changed = read.filter((f) => f.taken.length > 0);
  if (changed.length) {
    const index = new SourceIndex(source);
    const stories = readStories();
    index.realign(stories);
    const plan = derivePlans(stories, deriveNarratives(stories, index), index).find((p) => p.feature === feature);
    // With its folder gone a feature has no gate left to pass: its marks name nothing, and they go.
    const failures = plan?.folderExists ? findings(plan, true).failures : [];
    if (failures.length) throw new Error(`comprehension-render --strip ${feature}: the archive gate does not pass, and nothing is taken off —\n  ${failures.join('\n  ')}`);
    if (write) for (const f of changed) writeFileSync(join(ROOT, f.file), f.after);
  }
  const isCode = (file: string) => layout.isTest(file) || layout.isProduct(file) || layout.isApp(file);
  return {
    files: changed.map((f) => ({ file: f.file, taken: f.taken })),
    remains: read.flatMap((f) => namesFeature(f.after, feature).map((l) => ({ file: f.file, ...l, code: isCode(f.file) }))),
    stripped: read.length === 0 || read.some((f) => f.stripped),
  };
}

// ── `--check`: symbols that did not link, gaps, dead actions, and two informative lines ──

/** Lists every backticked token of every canonical step that the rules did not resolve, with the reason;
 *  returns the gate's misses: a token that looks like a declared symbol and is not a watch key, a step
 *  before any cause, a cause with no step (unless it says "nothing follows"), a step after one that does. */
export function check(source: SourceReader = openSource(), archive: string | null = null): string[] {
  const index = new SourceIndex(source);
  const stories = readStories();
  index.realign(stories);
  const narratives = deriveNarratives(stories, index);
  const flagged: string[] = [];
  const calledHere = { total: 0, traced: 0, static: 0, caller: 0, sibling: 0, disagree: [] as string[] };
  for (const n of narratives) {
    console.log(`\n${n.kind} "${n.title}" — ${n.file}`);
    if (!n.canonical) {
      console.log(`  no story for its canonical case${n.canonicalTest ? ` "${n.canonicalTest}"` : ''}`);
      continue;
    }
    for (const step of n.steps) {
      const { tokens } = sentenceHtml(step.sentence, step.source, index, narrativeStories(n), n.steps.map((s) => s.source));
      const keys = watchKeys(step);
      const linked = tokens.filter((t) => t.resolution.linked);
      const unlinked = tokens.filter((t) => !t.resolution.linked);
      console.log(`  step ${step.n} ${step.id} — ${tokens.length} symbols, ${linked.length} linked, ${linked.filter((t) => t.calledHere).length} with "Open call"`);
      for (const t of linked) {
        if (!t.resolution.linked) continue;
        calledHere.total += 1;
        if (t.calledHere) calledHere[t.calledHere.how] += 1;
        const where = t.calledHere ? ` · open call ${t.calledHere.at.file}:${t.calledHere.at.line} (${t.calledHere.how}${t.calledHere.fn ? ` ${t.calledHere.fn}` : ''})` : ' · used by no function of the narrative nor a caller of the step';
        if (t.staticAt && t.tracedAt && t.staticAt.line !== t.tracedAt.line) calledHere.disagree.push(`${n.title}, step ${step.n} \`${t.name}\`: static :${t.staticAt.line}, traced :${t.tracedAt.line}`);
        console.log(`    linked   \`${t.name}\` → ${t.resolution.at.file}:${t.resolution.at.line} (rule ${t.resolution.rule})${where}`);
      }
      for (const t of unlinked) {
        if (t.resolution.linked) continue;
        const miss = index.looksDeclared.test(t.name) && !keys.has(t.name);
        if (miss) flagged.push(`${n.title}, step ${step.n} \`${t.name}\` — ${t.resolution.reason}`);
        console.log(`    ${miss ? 'MISS    ' : 'unlinked'} \`${t.name}\` — ${t.resolution.reason}${!miss && keys.has(t.name) ? ' (a watch key)' : ''}`);
      }
    }
    // Causes: every story of the narrative is held to "no step without a cause, no cause without a step".
    for (const story of [n.canonical, ...n.variants]) {
      // A story the collector cut short counts fewer stops than the run made: nothing derived from it holds.
      for (const c of story.capped ?? []) flagged.push(`capped: "${story.test}" hit ${c.file}:${c.line} ${c.kept + c.omitted} times and the collector kept ${c.kept} — a narrative's case must not loop over a narrated site`);
      const segments = deriveSegments(story);
      const shape = segments.map((s) => (s.event ? `${actor(s.event.sentence)}:${s.hits.length}${EXPECTS_SILENCE.test(s.event.sentence) ? ' (silent)' : ''}` : `GAP:${s.hits.length}`)).join(' → ');
      console.log(`  segments of "${story.test.slice(0, 60)}…": ${shape}`);
      if (segments[0] && segments[0].event === null) flagged.push(`gap: ${segments[0].hits.length} step hits before any event in "${story.test}"`);
      for (const s of segments) {
        if (!s.event) continue;
        const silent = EXPECTS_SILENCE.test(s.event.sentence);
        if (s.hits.length === 0 && !silent) flagged.push(`dead action: no step after "${s.event.sentence}" in "${story.test}"`);
        if (s.hits.length > 0 && silent) flagged.push(`not silent: ${s.hits.length} step hits after "${s.event.sentence}" in "${story.test}"`);
      }
    }
  }
  // Every `narrate` sentence under `src/`, crossed by a story or not, is held to its budget.
  for (const site of index.sitesUnder(config.source.app)) {
    if (site.sentence === null) continue;
    for (const over of overSentenceBudget(site.sentence)) flagged.push(`sentence: ${site.file}:${site.line} in ${site.fn} ${over}`);
  }
  console.log(`\ninfo: "Open call" — ${calledHere.traced + calledHere.static + calledHere.caller + calledHere.sibling} of ${calledHere.total} linked sentence symbols have one (${calledHere.traced} traced, ${calledHere.static} static, ${calledHere.caller} in the step's caller, ${calledHere.sibling} in another step's function); ${calledHere.disagree.length} where the static reference and the traced call line disagree${calledHere.disagree.length ? ':' : ''}`);
  for (const d of calledHere.disagree) console.log(`  ${d}`);
  // Plans (`findings` in plan.ts): a site whose feature folder is gone fails, a `[rule]` that names no rule
  // of spec.md, a rule with two owners, a `#slug` of plan.md that names no piece; a rule with no owner is
  // informative. `--archive <feature>` fails while any site of it remains.
  const plans = derivePlans(stories, narratives, index);
  for (const plan of plans) {
    console.log(`\nplan "${plan.feature}" — ${plural(plan.pieces.length, 'piece')}${plan.folderExists ? '' : ' (NO FOLDER)'}${plan.doc ? `, ${plan.pieces.filter((s) => s.doc).length} with a section in ${plan.doc.file}` : ', no plan.md'}`);
    for (const group of plan.groups) {
      console.log(`  ${group.kind === 'narrative' ? `in run order — ${group.narrative}` : group.kind === 'uncrossed' ? 'crossed by no narrative' : 'no runtime line'}`);
      for (const s of group.pieces) {
        const tiers = todosByTier(s);
        console.log(`    #${s.slug} — ${TIERS.map((t) => `${t} ${tiers[t].length}`).join(', ')}${s.doc?.ask ? ' · a point to confirm' : ''}${s.decidedIn.length ? ` · also in ${s.decidedIn.map((d) => `"${d.title}"`).join(', ')}` : ''}`);
        for (const site of s.sites) {
          const inside = site.crossedBy.map((c) => `${c.narrative}${c.step ? ` step ${c.step.n} (${c.step.how} ${c.step.label})` : ' (in no step)'}`).join('; ');
          const tests = site.reachedBy.reduce((n, r) => n + r.tests, 0);
          console.log(`      ${site.change} ${site.file}:${site.line} in ${site.fn} — ${site.change === 'added' ? `shell: ${site.signature}` : `${tests} test${tests === 1 ? '' : 's'} in ${site.reachedBy.length} file${site.reachedBy.length === 1 ? '' : 's'}${inside ? `; inside ${inside}` : ''}`}`);
        }
        for (const l of s.lands) {
          const place = builtPlaceOf(l.line);
          const step = narratives.find((n) => n.title === l.narrative)?.steps[l.step];
          if (place && step) console.log(`      built ${place.file} in ${place.fn} — inside ${l.narrative} step ${step.n} (${l.how} ${label(step, index)}, ${l.by === 'call' ? 'by its built call' : l.by === 'approved' ? 'as approved' : 'by its function'})`);
        }
        for (const site of s.statics) console.log(`      comment ${site.file}:${site.line}${site.on ? ` on ${site.on}` : ''}${s.sql.includes(site.file) ? ' (the proposed migration)' : ''}`);
      }
    }
    for (const r of plan.rules) if (r.owners.length) console.log(`  rule [${r.slug}] — owned by ${r.owners.map((o) => `${o.file}:${o.line}`).join(', ')}`);
    if (plan.journeyCases.length) console.log(`  journey cases of the spec to write — ${plan.journeyCases.length}: ${[...new Set(plan.journeyCases.map((c) => c.file))].map((f) => `${f}:${plan.journeyCases.filter((c) => c.file === f).map((c) => c.line).join(',')}`).join('; ')}`);
    for (const r of plan.rules) if (r.waiver) console.log(`  rule [${r.slug}] — held by no test, waived at ${plan.doc!.file}:${r.waiver.line}${r.waiver.toConfirm ? ' · to confirm' : ''}`);
    for (const lot of plan.doc?.lots ?? []) {
      const left = lotLeft(plan, lot);
      console.log(`  lot "${lot.slug}" (${lot.difficulty}) — ${left.sites + left.tests + left.cases === 0 ? 'delivered' : `${plural(left.sites, 'site')}, ${plural(left.tests, 'test')} and ${plural(left.cases, 'journey case')} to go`}: ${[...lot.pieces.map((x) => `#${x}`), ...lot.screens.map((x) => `@${x}`)].join(' ')}`);
    }
    for (const c of plan.commits) console.log(`  commit ${c.sha.slice(0, 8)} — ${c.pieces.map((x) => `#${x}`).join(' ')}${c.sinceApproval ? ', since the approval' : ''}: ${plural(c.files.length, 'file')}${c.planned.length ? `, ${plural(c.planned.length, 'test')} deleted or changed as planned` : ''}${c.deleted.length ? `, ${c.deleted.length} deleted beyond the plan` : ''}${c.untagged.length ? `, ${c.untagged.length} added under no planned title` : ''}`);
    if (plan.delta === null) console.log(plan.doc ? `  never approved — on the reviewer's word: ${typed(config.commands.tool, SELF)} --approve ${plan.feature}` : '');
    else {
      console.log(`  approved on ${plan.approved!.approvedOn} at ${plan.approved!.base.slice(0, 8)} — ${plan.delta.length === 0 ? 'as approved' : `${plural(plan.delta.length, 'unit')} not as approved`}`);
      for (const d of plan.delta) {
        console.log(`    ${d.state} ${d.kind} ${d.name}${d.reason === 'needed' ? ' — NO "Changed:"' : d.reason === 'given' ? ' — says why' : ''}`);
        for (const f of d.facets) for (const [sign, texts] of [['+', f.added], ['−', f.removed]] as const) for (const text of texts) console.log(`      ${sign} ${f.facet}: ${text}`);
      }
    }
    const found = findings(plan, archive === plan.feature);
    for (const line of found.info) console.log(`  info: ${line}`);
    flagged.push(...found.failures);
  }
  if (archive !== null && !plans.some((p) => p.feature === archive)) console.log(`\narchive ${archive}: no planned site remains`);
  // Informative, no exit code: a mechanism-folder site no mechanism story claims; a mechanism whose
  // canonical crosses a product-owned site.
  const mechanismStories = narratives.filter((n) => n.kind === 'mechanism').flatMap((n) => [n.canonical, ...n.variants]).filter((s): s is Story => s !== null);
  const claimed = new Set<string>();
  for (const s of mechanismStories) for (const h of s.hits) if (h.kind === 'step') claimed.add(index.identity(h.site).id);
  const unclaimed = index.sitesUnder(MECHANISM_FOLDERS).filter((s) => !claimed.has(s.id));
  console.log(`\ninfo: ${unclaimed.length} narrate site${unclaimed.length === 1 ? '' : 's'} under ${MECHANISM_FOLDERS.map((f) => `${f}*`).join(', ')} that no mechanism story claims${unclaimed.length ? ':' : ''}`);
  for (const s of unclaimed) console.log(`  ${s.id} (${s.file}:${s.line})`);
  const productOwned = new Map<string, Narrative>();
  for (const n of narratives) if (n.kind === 'product') for (const id of n.stepIds) productOwned.set(id, n);
  const owner = ownership(narratives);
  for (const m of narratives) {
    if (m.kind !== 'mechanism' || !m.canonical) continue;
    const crossed = m.steps.filter((s) => productOwned.has(s.id));
    if (crossed.length) console.log(`info: mechanism "${m.title}" crosses ${crossed.length} product-owned site${crossed.length === 1 ? '' : 's'}: ${crossed.map((s) => `${s.id} (${productOwned.get(s.id)!.title})`).join(', ')}`);
    const rides = new Map<Narrative, number>();
    for (const h of m.canonical.hits) {
      if (h.kind !== 'step') continue;
      const o = owner.get(index.identity(h.site).id);
      if (o && o !== m) rides.set(o, (rides.get(o) ?? 0) + 1);
    }
    for (const [o, n] of rides) console.log(`info: mechanism "${m.title}" rides on "${o.title}" (${n} hits on its sites, collapsed on its page)`);
  }
  // Informative, no exit code: the backlink index — a page token that looks declared and resolves to nothing
  // (the stale-entry detector, told apart by whether the word still appears in the code at all), and an
  // entry whose named symbols and files no story's hit or frame ever touched.
  const backlinks = buildBacklinks(index, ROOT);
  console.log(`\ninfo: backlink index — ${backlinks.entries.length} entries over ${PAGES_SUMMARY(backlinks)}, ${backlinks.byKey.size} keys (symbol or file) named by at least one entry`);
  const unresolved = unresolvedDeclaredLooking(backlinks, ROOT, index.looksDeclared);
  const stale = unresolved.filter((u) => u.appearsIn.length === 0);
  console.log(`info: ${unresolved.length} page token${unresolved.length === 1 ? '' : 's'} look declared and resolve to nothing — ${stale.length} appear nowhere in the code (stale?), ${unresolved.length - stale.length} appear but not as a top-level declaration under ${APP}:`);
  for (const u of unresolved) console.log(`  ${u.appearsIn.length ? `seen in ${u.appearsIn.join(', ')}` : 'NOWHERE'}  \`${u.token.name}\` — ${describeEntry(u.entry)}`);
  const hitKeys = new Set<string>();
  for (const s of stories) for (const h of s.hits) {
    for (const f of [h.site, ...h.stack]) {
      if (!layout.isApp(f.file)) continue;
      hitKeys.add(f.file);
      hitKeys.add(`${f.file}#${f.fn ?? f.mappedFn ?? '(anonymous)'}`);
    }
  }
  const untraced = untracedEntries(backlinks, hitKeys);
  console.log(`info: ${untraced.length} of ${backlinks.entries.filter((e) => e.keys.size).length} entries that name code name a symbol or file no story has ever hit (informative — it may be legitimately untraced):`);
  for (const e of untraced) console.log(`  ${describeEntry(e)} — names ${[...e.keys].map((k) => `\`${k.includes('#') ? k.split('#')[1] : k}\``).join(', ')}`);
  return flagged;
}

const PAGES_SUMMARY = (b: BacklinkIndex) => [...new Map(b.entries.map((e) => [e.page, b.entries.filter((x) => x.page === e.page).length]))].map(([p, n]) => `${relative(config.docs, p)} ${n}`).join(', ');

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (process.argv.includes('--approve')) {
    const feature = process.argv[process.argv.indexOf('--approve') + 1];
    if (!feature) throw new Error('comprehension-render --approve <feature>: the feature name is missing');
    const done = approve(feature);
    console.log(`comprehension-render --approve: ${done.file} — ${done.units} units${done.cleared ? `, ${done.cleared} "Changed:" paragraph${done.cleared === 1 ? '' : 's'} taken off plan.md` : ''}${done.answered.length ? `, ${done.answered.join(', ')} answered as proposed and written in` : ''}`);
  } else if (process.argv.includes('--strip')) {
    const feature = process.argv[process.argv.indexOf('--strip') + 1];
    if (!feature || feature.startsWith('--')) throw new Error('comprehension-render --strip <feature>: the feature name is missing');
    const dry = process.argv.includes('--dry-run');
    const report = stripFeature(feature, !dry);
    const KIND = { built: 'built call', title: 'test title', screen: 'planned screen' } as const;
    for (const f of report.files) {
      console.log(`${f.file}`);
      for (const t of f.taken) console.log(`  :${t.line} ${KIND[t.kind]} — ${t.was}`);
    }
    const count = (kind: keyof typeof KIND) => report.files.reduce((n, f) => n + f.taken.filter((t) => t.kind === kind).length, 0);
    console.log(`\ncomprehension-render --strip ${feature}: ${dry ? 'would take' : 'took'} off ${plural(count('built'), 'built call')}, the tag of ${plural(count('title'), 'test title')} and ${plural(count('screen'), 'planned screen')}, in ${plural(report.files.length, 'file')}${dry ? ' — nothing written (--dry-run)' : ''}`);
    if (!report.stripped) console.log(`  the stack gives no strip (\`Stack.strip\`): what names the feature is taken off by hand`);
    const elsewhere = report.remains.filter((r) => !r.code);
    if (elsewhere.length) {
      console.log(`\ninfo: ${plural(elsewhere.length, 'line')} outside the code still name${elsewhere.length === 1 ? 's' : ''} ${feature} — to read before its folder goes:`);
      for (const r of elsewhere) console.log(`  ${r.file}:${r.line} ${r.text.slice(0, 140)}`);
    }
    const left = report.remains.filter((r) => r.code);
    if (left.length) {
      console.error(`\ncomprehension-render --strip ${feature}: ${plural(left.length, 'line')} of the code still name${left.length === 1 ? 's' : ''} the feature${dry ? ' after the strip' : ''} — taken off by hand:\n  ${left.map((r) => `${r.file}:${r.line} ${r.text.slice(0, 140)}`).join('\n  ')}`);
      process.exit(1);
    }
    console.log(`\ncomprehension-render --strip ${feature}: no line of the code names the feature${dry ? ' once stripped' : ''}`);
  } else if (process.argv.includes('--check')) {
    const at = process.argv.indexOf('--archive');
    const archive = at >= 0 ? process.argv[at + 1] ?? null : null;
    if (at >= 0 && archive === null) throw new Error('comprehension-render --check --archive <feature>: the feature name is missing');
    // A bug's evidence is checked against what its reproductions see now, not against the last run on file.
    const reproductions = runReproductions(reproductionFiles(readPlanSources()));
    // A gate with nothing to judge has not passed: with no story every list below is empty.
    if (readStories().length === 0) {
      console.error(`comprehension-render --check: ${NO_STORIES}`);
      process.exit(1);
    }
    const flagged = check(undefined, archive);
    for (const run of reproductions.failed) {
      console.error(`\nplanned: ${reproductionsFailed(run)}`);
      flagged.push(`the reproductions did not run as expected — ${run.command}`);
    }
    if (flagged.length) {
      console.error(`\ncomprehension-render --check: ${flagged.length} finding${flagged.length === 1 ? '' : 's'} (a symbol that looks declared and did not link, a gap, a dead action, a cause that was not silent, a sentence over its budget, a plan out of order):\n  ${flagged.join('\n  ')}`);
      process.exit(1);
    }
    console.log('\ncomprehension-render --check: every symbol that looks declared is linked; every step has a cause and every cause a step; every sentence is within its budget; every planned site names a feature folder, every rule a test claims exists and has one owner, every #slug of a plan.md names a piece, every piece of a plan is within its budget of words, every new function is named by the site that will call it, every difference from an approved plan says why, every piece of a plan with a delivery is in one lot, every piece of a delivered lot is named by a commit, and no commit of a lot added a test under no planned title');
  } else {
    const sources = readPlanSources();
    // A plan's page shows what its reproductions see now: they run first, whole files.
    const reproductions = runReproductions(reproductionFiles(sources));
    if (reproductions.ran) console.log(`comprehension-render: ran the reproductions of ${reproductions.ran} test file${reproductions.ran === 1 ? '' : 's'}`);
    for (const run of reproductions.failed) console.error(`comprehension-render: ${reproductionsFailed(run)}`);
    if (readStories().length === 0) {
      // A cold start, not a failure: rendering would overwrite the pages of an earlier run with empty ones,
      // and `npm run docs` chains this script, so it says so and lets the chain go on.
      console.log(`comprehension-render: ${NO_STORIES}; no page rendered`);
    } else {
      // The one async part: the database diff of a plan's proposed migration.
      void planDbDiffs(sources).then((diffs) => {
        const { stories, pages } = render(undefined, diffs, sources);
        console.log(`comprehension-render: ${stories} stories → ${pages.join(', ')}`);
      });
    }
  }
}
