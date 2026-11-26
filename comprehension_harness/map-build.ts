/**
 * map-build — the narratives as data, for `comprehension_harness/map.mjs` (`npm run map`).
 *
 * The pages `render.ts` draws are for a person: 80 to 220 kB of HTML each. An agent asks one
 * question at a time and needs the answer in a screen of text. Both read the same derivation
 * (`deriveNarratives` over the stories of the last unit run); this script writes it once as JSON under
 * `map/narratives.json` of the project's cache, and the verbs of `map.mjs` only read that file, so a
 * question costs a process start and not a read of the whole source.
 *
 * Beside what the pages show (steps, branches told by a variant case, mechanisms ridden, the debts and
 * rules naming a step), the snapshot holds what the source reader can say about the code AROUND a step and
 * no run says (`SourceReader.around`): who refers to the step's function, and which functions it calls, each
 * marked as holding a `narrate` or not. That is the list of un-narrated code next to a narrative (`map around`).
 *
 * `inputs` lists every file the snapshot was read from with its modification time: `map.mjs` compares
 * them and rebuilds when one moved.
 *
 * Usage: npx tsx comprehension_harness/map-build.ts   (run by `map.mjs` when the snapshot is stale)
 */
import { existsSync, mkdirSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { MAP_DIR, STORIES_DIR, featureFolder, storyFile } from './config';
import { openSource, toolSources } from './project-stack';
import type { Neighbour } from './stack';
import { PAGES, buildBacklinks, markersFor } from './backlinks';
import { callersOf as sitesNaming, findings, lotLeft, reviewItems, type Plan, type ReviewItem } from './plan';
import { ROOT, SourceIndex, deriveNarratives, derivePlans, narrativePlanIssues, readPlanSources, readStories, type Narrative } from './render';

export { MAP_DIR };
export const NARRATIVE_MAP = join(MAP_DIR, 'narratives.json');

export type { Neighbour };

export interface MapStep {
  n: number;
  file: string;
  line: number;
  fn: string;
  sentence: string;
  /** The cause (`event`) the step answers in the canonical case, when one preceded it. */
  cause: string | null;
  stops: number;
  /** First and last line of the function the site sits in. */
  range: [number, number] | null;
  /** How many tests reach the site, in how many test files. */
  reachedBy: { tests: number; files: string[] };
  /** Debts, rules and conventions naming the step's function or file. */
  named: Array<{ kind: string; title: string; page: string; line: number; via: string }>;
  callers: Neighbour[];
  callees: Neighbour[];
}

export interface MapNarrative {
  intended?: { planned: boolean; steps: Array<{ id: string; n: number; file: string; line: number; fn: string; sentence: string; changes: string[]; planned: boolean }> };
  slug: string;
  kind: 'product' | 'mechanism';
  scope?: 'doc';
  title: string;
  summary: string;
  /** The declaring test file and its reference case. */
  file: string;
  line: number;
  canonical: string | null;
  variants: string[];
  steps: MapStep[];
  /** `narrate` sites the reference case does not reach and another case of the narrative does. */
  branches: Array<{ file: string; line: number; fn: string; sentence: string; toldBy: string }>;
  /** Mechanisms the reference case rides on, with the number of hits. */
  ridesOn: Array<{ slug: string; title: string; hits: number }>;
  /** For a mechanism: the narratives whose reference case hits it. */
  exercisedBy: string[];
  /** The step files edited after the run the steps were read from. Their sites were found again by sentence
   *  (`SourceIndex.realign`), so the steps are placed right; what the run observed may have changed since. */
  editedSince: string[];
}

export interface NarrativeMap {
  narrativeIssues: string[];
  builtAt: string;
  /** Each input's modification time; null for a file that was not there, so that writing it rebuilds the map. */
  inputs: Record<string, number | null>;
  narratives: MapNarrative[];
  /** Every feature with a `planned` call, an `@planned` comment or a tagged test to write, as `derivePlans` gives
   *  it (groups hold slugs here: the steps are in `steps`), with what `--check` would say of it. */
  plans: Array<Omit<Plan, 'groups' | 'snapshot'> & {
    groups: Array<{ kind: string; narrative: string | null; slugs: string[] }>;
    /** By the id of a shell: the sites whose clause names its function. */
    calledFrom: Record<string, Array<{ file: string; line: number; slug: string }>>;
    /** By lot: what it still owes (`lotLeft`). */
    lotsLeft: Record<string, { sites: number; tests: number; cases: number }>;
    /** What the reviewer answers on the pages (`reviewItems`); `feedback` holds the answers given, by key. */
    items: ReviewItem[];
    failures: string[];
    info: string[];
  }>;
  /** Story files whose sites no longer match the source: their test must be run again. */
  stale: string[];
}

const rel = (file: string) => relative(ROOT, file);

function build(): NarrativeMap {
  const index = new SourceIndex(openSource());
  const stories = readStories();
  index.realign(stories);
  const narratives = deriveNarratives(stories, index);
  const backlinks = buildBacklinks(index, ROOT);

  // Which tests reach each site, over every story of the run. A story whose site is no longer a `narrate`
  // line is older than the source: its file is listed, and the verbs say so.
  const reach = new Map<string, Map<string, Set<string>>>();
  const stale = new Set<string>();
  for (const story of stories) {
    for (const hit of story.hits) {
      if (hit.kind !== 'step') continue;
      let id: string;
      try { id = index.identity(hit.site).id; } catch { stale.add(story.file); continue; }
      const files = reach.get(id) ?? new Map<string, Set<string>>();
      reach.set(id, files);
      files.set(story.file, (files.get(story.file) ?? new Set<string>()).add(story.test));
    }
  }

  const owner = new Map<string, Narrative>();
  for (const n of narratives) if (n.kind === 'mechanism') for (const id of n.siteIds) if (!owner.has(id)) owner.set(id, n);
  const numbered = new Set(narratives.flatMap((n) => n.steps.map((s) => s.id)));

  const out: MapNarrative[] = narratives.map((n) => {
    const causes = new Map<string, string | null>();
    let cause: string | null = null;
    const rides = new Map<Narrative, number>();
    for (const hit of n.canonical?.hits ?? []) {
      if (hit.kind === 'event') { cause = hit.sentence; continue; }
      if (hit.kind !== 'step') continue;
      const id = index.identity(hit.site).id;
      if (!causes.has(id)) causes.set(id, cause);
      const m = owner.get(id);
      if (m && m !== n) rides.set(m, (rides.get(m) ?? 0) + 1);
    }
    const branches: MapNarrative['branches'] = [];
    const seen = new Set<string>();
    for (const story of n.variants) for (const hit of story.hits) {
      if (hit.kind !== 'step') continue;
      const site = index.identity(hit.site);
      if (numbered.has(site.id) || !n.siteIds.has(site.id) || seen.has(site.id)) continue;
      seen.add(site.id);
      branches.push({ file: site.file, line: site.line, fn: site.fn, sentence: hit.sentence, toldBy: story.test });
    }
    return {
      ...(n.intended ? { intended: { planned: n.intended.planned, steps: n.intended.sites.map((s) => ({
        id: s.id, n: n.intended!.ids.indexOf(s.id) + 1, file: s.file, line: s.line, fn: s.fn,
        sentence: s.sentence!, changes: s.narration!.changes, planned: s.narration!.planned,
      })) } } : {}),
      slug: n.slug,
      kind: n.kind,
      ...(n.scope ? { scope: n.scope } : {}),
      title: n.title,
      summary: n.summary,
      file: n.file,
      line: n.declaredAt,
      canonical: n.canonicalTest,
      variants: n.variants.map((v) => v.test),
      steps: n.steps.map((s) => {
        const around = index.around(s.source);
        const files = reach.get(s.id) ?? new Map<string, Set<string>>();
        return {
          n: s.n,
          file: s.source.file,
          line: s.source.line,
          fn: s.source.fn,
          sentence: s.sentence,
          cause: causes.get(s.id) ?? null,
          stops: s.stops.length,
          range: around?.range ?? null,
          reachedBy: { tests: [...files.values()].reduce((a, t) => a + t.size, 0), files: [...files.keys()].sort() },
          named: markersFor(backlinks, { fn: s.source.fn, file: s.source.file, linked: [] })
            .map(({ entry, via }) => ({ kind: entry.kind, title: entry.title, page: rel(entry.page), line: entry.line, via: via.tier })),
          callers: around?.callers ?? [],
          callees: around?.callees ?? [],
        };
      }),
      branches,
      ridesOn: [...rides].map(([m, hits]) => ({ slug: m.slug, title: m.title, hits })),
      exercisedBy: [],
      editedSince: ((ranAt) => [...new Set([...n.steps.map((s) => s.source.file), ...branches.map((b) => b.file)])]
        .filter((f) => statSync(join(ROOT, f)).mtimeMs > ranAt).sort())(existsSync(storyFile(n.file)) ? statSync(storyFile(n.file)).mtimeMs : 0),
    };
  });
  for (const n of out) for (const r of n.ridesOn) out.find((m) => m.slug === r.slug)!.exercisedBy.push(n.slug);

  // What the snapshot was read from: the stories, the files holding a site, the narrative tests, the pages that name code.
  const inputs: Record<string, number | null> = {};
  const add = (file: string) => { const abs = join(ROOT, file); if (existsSync(abs)) inputs[file] = statSync(abs).mtimeMs; };
  if (existsSync(STORIES_DIR)) for (const f of readdirSync(STORIES_DIR)) add(rel(join(STORIES_DIR, f)));
  for (const file of index.siteFiles()) add(file);
  for (const n of out) for (const s of n.steps) for (const x of [...s.callers, ...s.callees]) add(x.file);
  for (const f of index.narrativeTestFiles()) add(f);
  for (const p of PAGES) add(p.page);
  for (const f of [...toolSources(), '.git/logs/HEAD']) add(f);

  // The plans: every file a site, a comment or a todo sits in is an input, and so are the feature's two markdown files.
  const sources = readPlanSources();
  const plans = derivePlans(stories, narratives, index, sources).map((plan) => {
    const { groups, snapshot: _snapshot, ...rest } = plan;
    for (const piece of plan.pieces) for (const x of [...piece.sites, ...piece.statics, ...piece.todos]) add(x.file);
    for (const c of plan.journeyCases) add(c.file);
    // A file of the folder that is not there yet is an input too: the day it is written, the map is rebuilt.
    for (const f of ['spec.md', 'plan.md', 'plan.approved.json', 'plan-feedback.json']) {
      const file = `${featureFolder(plan.feature)}/${f}`;
      inputs[file] = existsSync(join(ROOT, file)) ? statSync(join(ROOT, file)).mtimeMs : null;
    }
    const shells = plan.pieces.flatMap((x) => x.sites).filter((x) => x.change === 'added');
    return {
      ...rest,
      groups: groups.map((g) => ({ kind: g.kind, narrative: g.narrative, slugs: g.pieces.map((x) => x.slug) })),
      calledFrom: Object.fromEntries(shells.map((shell) => [shell.id, sitesNaming(plan, shell).map((x) => ({ file: x.file, line: x.line, slug: x.slug }))])),
      lotsLeft: Object.fromEntries((plan.doc?.lots ?? []).map((lot) => [lot.slug, lotLeft(plan, lot)])),
      items: reviewItems(plan),
      ...findings(plan),
    };
  });

  return { builtAt: new Date().toISOString(), inputs, narratives: out, plans, stale: [...stale].sort(), narrativeIssues: narrativePlanIssues(narratives, index) };
}

// A failure the tooling words itself (a story older than its source, a malformed tag) is one line: its message
// says what to do. Anything else is a defect of this script, and keeps its stack.
const map = (() => {
  try {
    return build();
  } catch (err) {
    if (!(err instanceof Error) || !/^comprehension-[a-z]+: /.test(err.message)) throw err;
    console.error(`map-build: ${err.message}`);
    process.exit(1);
  }
})();
/** A story file older than its source, and what clears it: its test run again, or the file deleted when its test
 *  is gone and nothing will write it again. */
const staleSaid = (file: string) => (existsSync(join(ROOT, file))
  ? `${file} — a step it crossed is no longer a \`narrate\` line: run its tests again`
  : `${file} — the test file is gone: delete ${rel(storyFile(file))}`);
mkdirSync(dirname(NARRATIVE_MAP), { recursive: true });
writeFileSync(NARRATIVE_MAP, JSON.stringify(map));
console.error(`map-build: ${rel(NARRATIVE_MAP)} — ${map.narratives.length} narratives, ${map.narratives.reduce((a, n) => a + n.steps.length, 0)} steps${map.stale.length ? `, ${map.stale.length} stale story file(s): ${map.stale.map(staleSaid).join('; ')}` : ''}`);
