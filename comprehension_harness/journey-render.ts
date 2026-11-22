/**
 * journey-render.ts — a design journey's page, generated from a run of its journey test.
 *
 *   <the journeys' command>                     # writes specs/design/journeys-generated/<journey>/
 *   npm run journey:render                      # writes specs/design/journeys-generated/<journey>.html
 *                                               # and specs/features/<feature>/spec.html
 *
 * `npm run docs` runs it last, after the narrative pages. With no run on disk it renders nothing and says so.
 *
 * Reads what the stack's journey helper wrote for each journey — `journey.json`, one JSON per case
 * under `cases/`, the screens captured as HTML under `captures/`, the stylesheet under `css/` — and draws
 * one page. Nothing on it is declared here:
 *
 *  - the spine is the first case (lowest line): its screens in order, each with its capture in a frame,
 *    its `why`, and before it what led there — the action, the `event` it fired, the narrative steps the
 *    app crossed, each linked to its anchor on the narrative or mechanism page. The link is made by call
 *    site: the browser's hit is mapped to source coordinates by the collector, and the step it is comes
 *    from `render.ts`'s own derivation over the unit stories, so the two
 *    pages cannot disagree on what "step 5" is. Without stories the steps are listed unlinked;
 *  - a variant is any later case. It is attached by comparing its screen sequence with the spine's: a
 *    screen whose id the spine has and whose DOM differs is a DATA variant, drawn under that screen with
 *    the differing elements outlined; a screen whose id the spine lacks is an ACTION branch, drawn under
 *    the screen the variant was at before it; a screen identical to the spine's is where it joins and is
 *    not drawn again;
 *  - "what can be done from here" is the screen's controls as the accessibility tree names them, grouped
 *    by role and name. A control is WALKED when some case acted on it at that screen, with the screen that
 *    followed; the rest are listed as not walked;
 *  - a planned screen (`screen(…, { planned })`) is drawn against its mockup fragment, which must carry
 *    the screen's address (`data-journey-screen`), the lines that differ outlined on both sides;
 *  - a named server step (`serverStep`) is a boundary row under the cause that reached it: what the app
 *    sent, what the stub answered, and the test that pins what the real server does — one line, the rest
 *    behind a click.
 *
 * A feature's spec page is drawn from the same run: its `spec.md` (the intent), then each journey the feature plans
 * something on (`planned` on a screen, `todo` beside the cases), the changed screens today against their mockup with
 * the cases to add, the unchanged ones named and linked; then what those screens ride on (`Rides`): the narrative
 * steps crossed, what no narrative tells, the server steps a stub answered. A feature with no `spec.md` gets none.
 *
 * The page is a grid of cells, one per spine screen, as many per row as the window fits: on top of a cell what
 * led to the screen, under it the capture scaled down (the frame stays 400 × 800, the capture's viewport) with
 * its text in a narrow column beside it. What hangs under a screen — its planned comparison, its variants — is
 * a band across the row below that screen's, headed with the screen's number. A journey of one or two screens
 * is centred and drawn larger.
 *
 * The comparison of two captures is a line diff: a capture has one tag per line (`capture.ts`).
 * Captures are embedded as `srcdoc` frames, so styles do not leak either way and the page can restore
 * the scroll offsets a capture carries as attributes. The page is not committed (`.gitignore`).
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Cause, Control, JourneyCase, ScreenRecord, ServerCall, StorySite } from './stack';
import { blocksHtml, parseIntent } from './intent-md';
import { renderStamp } from './render-stamp';
import { FEATURES as FEATURES_FOLDER, JOURNEYS, MAP_DIR, PAGES, ROOT, config, featureFolder, typed } from './config';
import { openSource } from './project-stack';
import { NO_STORIES, SourceIndex, deriveNarratives, readStories, type Narrative } from './render';

const OUT = join(ROOT, JOURNEYS);
/** This script, from the root: an input of what it writes. */
const SELF = relative(ROOT, fileURLToPath(import.meta.url));
/** From a journey page to the narrative pages, and from a feature's spec page to the journey pages. A feature
 *  folder and the journeys' folder are both two folders under the documents', so one page's links serve the other. */
const TO_PAGES = relative(OUT, join(ROOT, PAGES));
const TO_JOURNEYS = relative(join(ROOT, featureFolder('a-feature')), OUT);

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
/** A file of the repo as a link VS Code opens, at the line when one is given. The pages are rendered for this checkout and never committed, so the path is absolute. */
const src = (file: string, line?: number | null, text?: string): string =>
  `<a class="src" href="vscode://file/${join(ROOT, file).split('/').map(encodeURIComponent).join('/')}${line ? `:${line}:1` : ''}">${esc(text ?? (line ? `${file}:${line}` : file))}</a>`;
/** Markdown-lite, as a narrate sentence: `**bold**` and backticks. */
const lite = (s: string) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');

// ── captures as lines ────────────────────────────────────────────────────────────────────────────────────

const STATE_ATTRS = / data-capture-(?:focus|scroll="[^"]*")/g;
const VOID = new Set(['area', 'br', 'col', 'embed', 'hr', 'img', 'input', 'meta', 'param', 'source', 'track', 'wbr', 'link']);
const OPEN = /<([a-z][a-z0-9-]*)(?:\s[^<]*)?$/;
const CLOSE = /<\/[a-z][a-z0-9-]*$/;

/** The body of a capture, one tag per line, state attributes dropped: what two captures are compared on. */
function comparable(html: string): string[] {
  const lines = html.replace(STATE_ATTRS, '').split('\n');
  return lines.slice(lines.findIndex((l) => /<body/.test(l)));
}

/** Whether `lines[from..to]` is a whole subtree or a run of them: every tag it opens it closes, and it closes no other. */
function balanced(lines: string[], from: number, to: number): boolean {
  let depth = 0;
  for (let k = from; k <= to; k++) {
    const open = OPEN.exec(lines[k]);
    if (open) { if (!VOID.has(open[1])) depth += 1; } else if (CLOSE.test(lines[k])) { depth -= 1; if (depth < 0) return false; }
  }
  return depth === 0;
}

/**
 * A run of unmatched lines inside repeated markup can sit anywhere along the repetition and be as short: a
 * removed list item reads as "the tail of one item and the head of the next", and an added row as "its first ten
 * lines, a matched closing tag, two more". Two runs are first joined when the matched lines between them repeat
 * an edge of one, so that moving it over them makes one whole subtree. Each run is then slid, where the lines
 * allow it, to the position at which it is a whole subtree — the element that was added or removed.
 */
function slide(lines: string[], only: number[]): number[] {
  const runs: Array<[number, number]> = [];
  for (const k of only) {
    const last = runs[runs.length - 1];
    if (last && last[1] === k - 1) last[1] = k;
    else runs.push([k, k]);
  }
  const joined: Array<[number, number]> = [];
  for (const run of runs) {
    const prev = joined[joined.length - 1];
    if (prev) {
      const gap = run[0] - prev[1] - 1;
      const steps = Array.from({ length: gap }, (_, i) => i);
      // The later run moved up over the gap, or the earlier one moved down over it.
      const up: [number, number] = [prev[0], run[1] - gap], down: [number, number] = [prev[0] + gap, run[1]];
      const pick = steps.every((i) => lines[run[0] - 1 - i] === lines[run[1] - i]) && balanced(lines, up[0], up[1]) ? up
        : steps.every((i) => lines[prev[1] + 1 + i] === lines[prev[0] + i]) && balanced(lines, down[0], down[1]) ? down
        : null;
      if (pick) { joined[joined.length - 1] = pick; continue; }
    }
    joined.push(run);
  }
  const taken = new Set(joined.flatMap(([from, to]) => Array.from({ length: to - from + 1 }, (_, i) => from + i)));
  const out: number[] = [];
  for (let [from, to] of joined) {
    if (!balanced(lines, from, to)) {
      const candidates: Array<[number, number]> = [];
      for (let f = from, t = to; f > 0 && lines[f - 1] === lines[t] && !taken.has(f - 1); ) candidates.push([--f, --t]);
      for (let f = from, t = to; t + 1 < lines.length && lines[t + 1] === lines[f] && !taken.has(t + 1); ) candidates.push([++f, ++t]);
      const better = candidates.find(([f, t]) => balanced(lines, f, t));
      if (better) [from, to] = better;
    }
    for (let i = from; i <= to; i++) out.push(i);
  }
  return out;
}

/** For each side, the indexes of the lines the other side has no match for: the common head and tail set aside,
 *  a longest common subsequence over what is left, each run then slid onto a whole subtree. */
function lineDiff(a: string[], b: string[]): { onlyA: number[]; onlyB: number[] } {
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head += 1;
  let tail = 0;
  while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail += 1;
  const A = a.slice(head, a.length - tail), B = b.slice(head, b.length - tail);
  const n = A.length, m = B.length, w = m + 1;
  const lcs = new Uint16Array((n + 1) * w);
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    lcs[i * w + j] = A[i] === B[j] ? lcs[(i + 1) * w + j + 1] + 1 : Math.max(lcs[(i + 1) * w + j], lcs[i * w + j + 1]);
  }
  const onlyA: number[] = [], onlyB: number[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { i++; j++; }
    else if (lcs[(i + 1) * w + j] >= lcs[i * w + j + 1]) onlyA.push(head + i++);
    else onlyB.push(head + j++);
  }
  while (i < n) onlyA.push(head + i++);
  while (j < m) onlyB.push(head + j++);
  return { onlyA: slide(a, onlyA), onlyB: slide(b, onlyB) };
}

/**
 * Stamps `data-jd` on the elements a set of differing lines belongs to: the outermost element opened in each
 * run of differing lines, and — for a line that only changes text — the element the text sits in.
 */
function mark(lines: string[], differing: number[]): string[] {
  const out = [...lines];
  const stamp = (at: number) => { out[at] = out[at].replace(OPEN, (tag) => (tag.includes(' data-jd') ? tag : tag.replace(/^<[a-z][a-z0-9-]*/, '$& data-jd'))); };
  const parentOf = (at: number): number | null => {
    let need = 0;
    for (let k = at - 1; k >= 0; k--) {
      const open = OPEN.exec(lines[k]);
      if (CLOSE.test(lines[k])) need += 1;
      else if (open && !VOID.has(open[1])) { if (need === 0) return k; need -= 1; }
    }
    return null;
  };
  let depth = 0;
  differing.forEach((at, k) => {
    if (k === 0 || differing[k - 1] !== at - 1) depth = 0;
    const open = OPEN.exec(lines[at]);
    if (open) {
      if (depth <= 0) { stamp(at); depth = 0; }
      if (!VOID.has(open[1])) depth += 1;
      // Text before the tag on the same line changed with it: the enclosing element holds it.
    } else if (CLOSE.test(lines[at])) {
      if (depth <= 0) { const parent = parentOf(at); if (parent !== null) stamp(parent); }
      depth -= 1;
    }
  });
  return out;
}

interface Comparison { a: string; b: string; linesA: number; linesB: number; onlyA: number; onlyB: number }

/** Two captures compared: each side's full text with its differing elements stamped, and the counts. */
function compare(htmlA: string, htmlB: string): Comparison {
  const split = (html: string) => { const lines = html.split('\n'); const at = lines.findIndex((l) => /<body/.test(l)); return { head: lines.slice(0, at), body: lines.slice(at) }; };
  const A = split(htmlA), B = split(htmlB);
  const ca = comparable(htmlA), cb = comparable(htmlB);
  const { onlyA, onlyB } = lineDiff(ca, cb);
  return {
    a: [...A.head, ...mark(A.body, onlyA)].join('\n'),
    b: [...B.head, ...mark(B.body, onlyB)].join('\n'),
    linesA: ca.length, linesB: cb.length, onlyA: onlyA.length, onlyB: onlyB.length,
  };
}

// ── the narrative index ──────────────────────────────────────────────────────────────────────────────────

/** Where a `narrate` site is told: a numbered step of a narrative's canonical case (`n`), or a branch that case does not take and another case of the narrative does (`branch`, that case's title). */
interface StepLink { narrative: Narrative; n: number | null; branch: string | null; href: string }

function narrativeIndex(): { linkOf: (site: StorySite, sentence: string) => StepLink | null; stories: number } {
  const stories = readStories();
  if (stories.length === 0) return { linkOf: () => null, stories: 0 };
  const index = new SourceIndex(openSource());
  index.realign(stories);
  const narratives = deriveNarratives(stories, index);
  const byId = new Map<string, StepLink>();
  for (const narrative of narratives) {
    const page = narrative.kind === 'product' ? `${TO_PAGES}/narratives/${config.productPage}.html` : `${TO_PAGES}/mechanisms/${narrative.slug}.html`;
    for (const step of narrative.steps) byId.set(step.id, { narrative, n: step.n, branch: null, href: `${page}#${narrative.slug}-step-${step.n}` });
  }
  // A canonical case takes one path. The `narrate` on a branch it does not take (the gate's offline exit, a
  // disabled live read) has no step number: it is told by the first other case of the narrative that reaches it.
  for (const narrative of narratives) {
    const page = narrative.kind === 'product' ? `${TO_PAGES}/narratives/${config.productPage}.html` : `${TO_PAGES}/mechanisms/${narrative.slug}.html`;
    for (const story of narrative.variants) for (const hit of story.hits) {
      if (hit.kind !== 'step') continue;
      const id = index.identity(hit.site).id;
      if (!byId.has(id) && narrative.siteIds.has(id)) byId.set(id, { narrative, n: null, branch: story.test, href: `${page}#${narrative.slug}` });
    }
  }
  return {
    stories: stories.length,
    // A capture names a site by its line too: it is found where it is now (`SourceIndex.siteNow`).
    linkOf: (site, sentence) => byId.get(index.siteNow(site.file, site.line, 'step', sentence)?.id ?? '') ?? null,
  };
}

// ── the journey ──────────────────────────────────────────────────────────────────────────────────────────

interface Loaded { dir: string; slug: string; cases: JourneyCase[]; html: (c: JourneyCase, s: ScreenRecord) => string }

function load(slug: string): Loaded {
  const dir = join(OUT, slug);
  const cases = readdirSync(join(dir, 'cases')).filter((f) => f.endsWith('.json')).sort()
    .map((f) => JSON.parse(readFileSync(join(dir, 'cases', f), 'utf8')) as JourneyCase)
    .sort((a, b) => a.line - b.line);
  // A return whose DOM is the first visit's wrote no file: it reads the first visit's.
  const html = (c: JourneyCase, s: ScreenRecord): string => readFileSync(join(dir, s.capture ?? c.screens[s.returnsTo!].capture!), 'utf8');
  return { dir, slug, cases, html };
}

const controlKey = (controls: Control[], c: Control) =>
  `${c.role ?? c.tag}|${c.name ?? ''}|${controls.filter((o) => o.i < c.i && o.role === c.role && o.name === c.name).length}`;

interface Walk { to: string | null; caseTitle: string; canonical: boolean; events: string[] }

/** Every control some case acted on, by the screen it was on: `<screen id>` → `<role|name|ordinal>` → where it led. */
function walks(cases: JourneyCase[]): Map<string, Map<string, Walk[]>> {
  const out = new Map<string, Map<string, Walk[]>>();
  cases.forEach((c, ci) => {
    const segments: Array<{ from: ScreenRecord; causes: Cause[]; to: string | null }> = [];
    c.screens.forEach((s, k) => { if (k > 0) segments.push({ from: c.screens[k - 1], causes: s.before, to: s.id }); });
    if (c.screens.length > 0) segments.push({ from: c.screens[c.screens.length - 1], causes: c.after, to: null });
    for (const { from, causes, to } of segments) {
      for (const cause of causes) {
        if (cause.kind !== 'action' || cause.control == null) continue;
        const control = from.controls.find((x) => x.i === cause.control);
        if (!control) continue;
        const byKey = out.get(from.id) ?? new Map<string, Walk[]>();
        out.set(from.id, byKey);
        const key = controlKey(from.controls, control);
        byKey.set(key, [...(byKey.get(key) ?? []), { to, caseTitle: c.title, canonical: ci === 0, events: cause.events.map((e) => e.sentence) }]);
      }
    }
  });
  return out;
}

/** Why an accessible name reads badly as an action, if it does. */
function nameFlags(c: Control, sameName: number): string[] {
  const flags: string[] = [];
  if (c.pointerOnly) return ['clickable, but no control in the accessibility tree'];
  if (!c.name) flags.push('unnamed');
  else {
    if (!/[\p{L}\p{N}]/u.test(c.name)) flags.push('symbol only');
    else if (/[▼▲▸▶◀←→↗✕]/u.test(c.name)) flags.push('glyph in the name');
    if (/\p{Extended_Pictographic}/u.test(c.name)) flags.push('emoji in the name');
  }
  if (sameName > 1) flags.push(`${sameName} controls share this name`);
  return flags;
}

/** A capture in a frame. `base` is the path from the page to the journey's folder, where its stylesheet is. */
function frame(html: string, base: string, label: string): string {
  const doc = html
    .replace(/href="[^"]*css\/(app-[a-f0-9]+\.css)"/, `href="${base}/css/$1"`)
    .replace('</head', '<style\n>[data-jd]{outline:2px solid #c026d3!important;outline-offset:1px;background-image:linear-gradient(#c026d314,#c026d314)!important}a[href]{pointer-events:none}</style\n></head');
  // The frame keeps the capture's own viewport (400 × 800) and is scaled down inside a wrapper of the scaled size.
  return `<div class="shot"><iframe class="cap" title="${esc(label)}" srcdoc="${esc(doc)}"></iframe></div>`;
}

/** What a cause is, as the rest of a sentence: "opens …", "taps …", "400 ms pass — …". `from` is the screen an action was taken on. */
function causeWhat(cause: Cause, from: ScreenRecord | null): string {
  const control = cause.kind === 'action' && cause.control != null ? from?.controls.find((c) => c.i === cause.control) : undefined;
  return cause.kind === 'open'
    ? `opens <code>${esc(cause.navigations[0] ?? cause.url)}</code>`
    : cause.kind === 'time'
    ? `${cause.elapsed!.ms} ms pass — ${lite(cause.elapsed!.why)}`
    : `${esc(cause.type === 'click' ? 'taps' : cause.type === 'keydown' ? `presses ${cause.key} on` : `${cause.type}s`)} ${control
      ? `<span class="ctl">${esc(control.role ?? control.tag)} “${esc(control.name ?? control.text)}”</span>`
      : `<span class="ctl">${esc(cause.on?.tag ?? '')} “${esc(cause.on?.ariaLabel ?? cause.on?.text ?? '')}”</span>`}`;
}

interface Pair { what: string; lines: number; changed: number }

/** The features that plan something at a screen: a mockup of it, or a case to add there. */
const featuresAt = (c: JourneyCase, s: ScreenRecord): string[] =>
  [...new Set([...(s.planned ? [s.planned.feature] : []), ...(c.journey.todos ?? []).filter((t) => t.screen === s.id).map((t) => t.feature)])];

/**
 * What a feature plans at a screen: today's capture against the mockup, the elements that differ outlined on both
 * sides, then the cases the feature will add there (`todo`). `base` is the path from the page to the journey's folder.
 */
function plannedBlock(J: Loaded, c: JourneyCase, s: ScreenRecord, feature: string, base: string): { html: string; pair: Pair | null } {
  const planned = s.planned?.feature === feature ? s.planned : undefined;
  const todos = (c.journey.todos ?? []).filter((t) => t.feature === feature && t.screen === s.id);
  const cases = todos.length === 0 ? '' : `<div class="todos"><b>${todos.length} case${todos.length === 1 ? '' : 's'} to add here</b> <small>${src(c.journey.file)}</small><ul>${todos.map((t) => `<li>${lite(t.title)} <small>${src(c.journey.file, t.line, `line ${t.line}`)}</small></li>`).join('')}</ul></div>`;
  const head = `<h4>Planned — <code>${esc(feature)}</code></h4>`;
  if (!planned) return { html: `<div class="planned"><div class="note">${head}<p>No mockup of this screen.</p>${cases}</div></div>`, pair: null };
  const path = join(ROOT, planned.mockup);
  if (!existsSync(path)) return { html: `<div class="planned"><div class="note">${head}<p class="bad">The mockup ${src(planned.mockup)} does not exist.</p>${cases}</div></div>`, pair: null };
  // A mockup is an edited copy of a capture and links the stylesheet of the day it was copied: it is drawn with today's.
  const mockup = readFileSync(path, 'utf8').replace(/<!--[\s\S]*?-->\n?/, '').replace(/css\/app-[a-f0-9]+\.css/, s.css);
  const address = `${J.slug}#${s.id}`;
  const carries = new RegExp(`data-journey-screen="${address}"`).test(mockup);
  const cmp = compare(J.html(c, s), mockup);
  return {
    pair: { what: `${s.id} today → its ${feature} mockup`, lines: cmp.linesA, changed: cmp.onlyA + cmp.onlyB },
    html: `<div class="planned"><div class="pair"><figure><figcaption>today (captured)</figcaption>${frame(cmp.a, base, `${s.id} today`)}</figure><figure><figcaption>planned (mockup)</figcaption>${frame(cmp.b, base, `${s.id} planned`)}</figure></div>
      <div class="note">${head}<p>${esc(planned.what)}</p>${cases}
      <p class="facts"><small>mockup ${src(planned.mockup)} ${carries ? `carries <code>${esc(address)}</code>` : `<b class="bad">does not carry the address ${esc(address)}</b>`} · ${cmp.onlyA} line${cmp.onlyA === 1 ? '' : 's'} of today's capture gone, ${cmp.onlyB} new, of ${cmp.linesA} · the elements that differ are outlined</small></p></div></div>`,
  };
}

function render(slug: string, linkOf: (site: StorySite, sentence: string) => StepLink | null): { html: string; report: string[] } {
  const J = load(slug);
  const [spine, ...variants] = J.cases;
  if (!spine) throw new Error(`journey-render: ${slug} has no case — run its journey test`);
  const meta = spine.journey;
  const walked = walks(J.cases);
  /** `<role> "<name>" — <flag>` → the screens it was seen on. */
  const flaggedNames = new Map<string, Set<string>>();

  // Ids are addresses: unique on the spine, a second occurrence only as a declared return.
  const firstVisit = new Map<string, ScreenRecord>();
  for (const s of spine.screens) if (!firstVisit.has(s.id)) firstVisit.set(s.id, s);
  const pairs: Pair[] = [];

  const causeHtml = (cause: Cause, from: ScreenRecord | null, toUrl: string): string => {
    const what = causeWhat(cause, from);
    const url = cause.kind === 'action' ? (cause.navigations.length ? ` · URL → <code>${esc(cause.navigations[cause.navigations.length - 1])}</code>` : cause.url === toUrl ? ' · URL unchanged' : '') : '';
    const events = cause.events.map((e) => `<div class="event">fires <b>event</b> ${lite(e.sentence)} <small>${src(e.site.file, e.site.line)}</small></div>`).join('');
    // Steps by the narrative that owns each, in first-hit order.
    const groups = new Map<string, { narrative: Narrative | null; steps: Array<{ link: StepLink | null; site: StorySite; count: number }> }>();
    for (const step of cause.steps) {
      const link = linkOf(step.site, step.sentence);
      const key = link?.narrative.slug ?? '';
      const g = groups.get(key) ?? { narrative: link?.narrative ?? null, steps: [] };
      groups.set(key, g);
      g.steps.push({ link, site: step.site, count: step.count });
    }
    const crossed = [...groups.values()].sort((a, b) => Number(a.narrative?.kind !== 'product') - Number(b.narrative?.kind !== 'product')).map((g) => {
      const steps = g.steps.sort((a, b) => (a.link?.n ?? Infinity) - (b.link?.n ?? Infinity))
        .map((s) => (s.link?.n != null ? `<a href="${esc(s.link.href)}" title="${esc(s.site.file)}:${s.site.line} · ×${s.count}">step ${s.link.n}</a>`
          : s.link ? `the branch at ${src(s.site.file, s.site.line, `${s.site.fn ?? '?'}:${s.site.line}`)} <small>(told by its case “${esc(s.link.branch!)}”)</small>`
          : `<code title="×${s.count}">${esc(s.site.fn ?? '?')}</code> <small>${src(s.site.file, s.site.line)}</small>`)).join(', ');
      return g.narrative
        ? `<div class="crossed ${g.narrative.kind}">${g.narrative.kind === 'product' ? 'crosses' : 'rides on'} <b>${esc(g.narrative.title)}</b>: ${steps}</div>`
        : `<div class="crossed none">narrated, in no narrative's story: ${steps}</div>`;
    }).join('');
    // A capture written before `serverStep` existed has no list: it reached no named step.
    // The same request answered the same way is one row, counted: how often a page repeats a read varies from run to run.
    const calls = new Map<string, { call: ServerCall; times: number }>();
    for (const call of cause.server ?? []) {
      const key = JSON.stringify([call.name, call.method, call.path, call.sent, call.status, call.answered]);
      const seen = calls.get(key);
      if (seen) seen.times += 1;
      else calls.set(key, { call, times: 1 });
    }
    const server = [...calls.values()].map(({ call: c, times }) => `<details class="server"><summary><b>server · ${esc(c.name)}</b>${times > 1 ? ` <small>×${times}</small>` : ''} ${lite(c.does)}</summary>
        <small><code>${esc(c.method)} ${esc(decodeURIComponent(c.path))}</code>${c.sent === null ? '' : ` sent <code>${esc(JSON.stringify(c.sent))}</code>`} → answered ${c.status}${c.answered === null ? '' : ` <code>${esc(JSON.stringify(c.answered))}</code>`} · stubbed here; what the real server does is pinned by ${src(c.truth)}</small></details>`).join('');
    return `<div class="cause ${cause.kind}"><div class="what">${cause.kind === 'open' ? 'The case ' : cause.kind === 'time' ? '' : `The ${config.actor} `}${what}${url}</div>${events}${crossed}${server}</div>`;
  };

  const controlsHtml = (s: ScreenRecord): string => {
    const modal = s.controls.some((c) => c.inDialog);
    const scope = s.controls.filter((c) => !modal || c.inDialog);
    const behind = s.controls.length - scope.length;
    const groups = new Map<string, Control[]>();
    for (const c of scope) { const k = `${c.role ?? `(${c.tag})`}|${c.name ?? ''}`; groups.set(k, [...(groups.get(k) ?? []), c]); }
    let notWalked = 0;
    const rows = [...groups.values()].map((group) => {
      const c = group[0];
      const found = group.flatMap((g) => walked.get(s.id)?.get(controlKey(s.controls, g)) ?? []);
      const flags = nameFlags(c, group.length);
      for (const f of flags) {
        const key = `${c.role ?? c.tag} “${c.name ?? c.text}” — ${f.replace(/^\d+ controls share/, 'several controls share')}`;
        flaggedNames.set(key, (flaggedNames.get(key) ?? new Set()).add(s.id));
      }
      const to = found.length
        ? [...new Map(found.map((w) => [`${w.to}|${w.canonical}`, w])).values()].map((w) => `→ ${w.to ? `<a href="#${esc(w.to)}">${esc(w.to)}</a>` : 'stays'}${w.canonical ? '' : ` <small>(variant)</small>`}${w.events.length ? ` <small>· event</small>` : ''}`).join(' ')
        : c.disabled ? '<span class="muted">disabled here</span>' : '<span class="notwalked">not walked</span>';
      if (!found.length && !c.disabled) notWalked += group.length;
      return `<tr class="${found.length ? 'walked' : ''}"><td>${esc(c.role ?? `(${c.tag})`)}</td><td>“${esc(c.name ?? c.text)}”${group.length > 1 ? ` <small>×${group.length}</small>` : ''}${flags.map((f) => ` <span class="flag">${esc(f)}</span>`).join('')}</td><td>${to}</td></tr>`;
    }).join('');
    return `<details class="controls"${scope.length <= 14 ? ' open' : ''}><summary>What can be done from here — ${scope.length} control${scope.length === 1 ? '' : 's'}${modal ? ' in the sheet' : ''}, ${notWalked} not walked${behind ? ` <small>(${behind} more on the page behind the sheet: the accessibility tree still lists them)</small>` : ''}</summary><table>${rows}</table></details>`;
  };

  const facts = (c: JourneyCase, s: ScreenRecord) =>
    `<small class="facts"><code>${esc(s.url)}</code> · capture ${(s.bytes / 1024).toFixed(1)} kB · ${s.counts.elements} elements · ${s.counts.media} audio${s.counts.canvases ? ` · ${s.counts.canvases} canvas` : ''}${s.capture ? ` · <a href="${esc(`${slug}/${s.capture}`)}">open the capture</a>` : ''} · ${src(c.journey.file, c.line, `case line ${c.line}`)}</small>`;

  const plannedHtml = (c: JourneyCase, s: ScreenRecord): string[] => featuresAt(c, s).map((feature) => {
    const { html, pair } = plannedBlock(J, c, s, feature, slug);
    if (pair) pairs.push(pair);
    return html;
  });

  // Variants, attached by comparing screen sequences with the spine.
  const attached = new Map<string, string[]>();
  const attach = (at: string, html: string) => attached.set(at, [...(attached.get(at) ?? []), html]);
  for (const v of variants) {
    v.screens.forEach((s, k) => {
      const onSpine = firstVisit.get(s.id);
      if (onSpine) {
        const cmp = compare(J.html(spine, onSpine), J.html(v, s));
        if (cmp.onlyA + cmp.onlyB === 0) return; // where the variant joins the spine
        pairs.push({ what: `${s.id}: spine → variant “${v.title}”`, lines: cmp.linesA, changed: cmp.onlyA + cmp.onlyB });
        attach(s.id, `<div class="variant data">${frame(cmp.b, slug, `${s.id} — ${v.title}`)}
          <div class="note"><h4>Data variant — ${esc(v.title)}</h4><p class="why">${esc(s.why)}</p>
          <p class="facts"><small>same screen, other data · ${cmp.onlyB} line${cmp.onlyB === 1 ? '' : 's'} differ from the spine's capture (${cmp.linesB} lines), outlined in the frame · ${facts(v, s)}</small></p></div></div>`);
      } else {
        const from = k > 0 ? v.screens[k - 1] : null;
        const at = from && firstVisit.has(from.id) ? from.id : from ? from.id : spine.screens[0].id;
        attach(at, `<div class="variant action" id="${esc(s.id)}"><h4>Action branch — ${esc(v.title)}</h4>
          <div class="segment">${s.before.filter((c) => c.kind === 'action' || k === 0).map((c) => causeHtml(c, from, s.url)).join('')}</div>
          <div class="screen-body">${frame(J.html(v, s), slug, s.id)}<div class="side"><h3><code>${esc(slug)}#${esc(s.id)}</code></h3><p class="why">${esc(s.why)}</p>${facts(v, s)}${controlsHtml(s)}</div></div></div>`);
      }
    });
  }

  /** What hangs under a screen — its planned comparison, its variants — as one band across the row its cell is on. */
  const under = (label: string, items: string[]): string =>
    items.length === 0 ? '' : `<section class="under"><h4 class="of">Under ${label} — ${items.length} comparison${items.length === 1 ? '' : 's'}</h4><div class="items">${items.join('')}</div></section>`;

  // One cell per screen: what led to it on top, then the frame with its text beside. The cells flow in rows.
  const spineHtml = spine.screens.map((s, k) => {
    const from = k > 0 ? spine.screens[k - 1] : null;
    const led = s.before.map((c) => causeHtml(c, from, s.url)).join('');
    if (from) {
      const cmp = compare(J.html(spine, from), J.html(spine, s));
      pairs.push({ what: `${from.id} → ${s.id}${s.returnsTo !== null ? ' (return)' : ''}`, lines: cmp.linesA, changed: cmp.onlyA + cmp.onlyB });
    }
    if (s.returnsTo !== null) {
      const moved = s.movedSinceFirstVisit;
      return `<section class="screen return"><div class="segment">${led}</div>
        <div class="screen-body">${s.identicalToFirstVisit ? '' : frame(J.html(spine, s), slug, `${s.id} (return)`)}
          <div class="side"><h3>↩ back at <a href="#${esc(s.id)}"><code>${esc(s.id)}</code></a></h3><p class="why">${esc(s.why)}</p>
          <p class="facts"><small>${s.identicalToFirstVisit ? 'the DOM is the first visit\'s, element for element' : '<b class="bad">the DOM differs from the first visit</b>'}${moved?.focus ? ' · the focus is no longer where it was' : ''}${moved?.scroll ? ' · the scroll offset moved' : ''}</small></p></div>
        </div></section>`;
    }
    return `<section class="screen" id="${esc(s.id)}"><div class="segment">${led}</div>
        <div class="screen-body">${frame(J.html(spine, s), slug, s.id)}
          <div class="side"><h3><span class="n">${k + 1}</span> <code>${esc(slug)}#${esc(s.id)}</code></h3><p class="why">${esc(s.why)}</p>${facts(spine, s)}${controlsHtml(s)}</div>
        </div></section>
      ${under(`<span class="n">${k + 1}</span> <a href="#${esc(s.id)}"><code>${esc(s.id)}</code></a>`, [...plannedHtml(spine, s), ...(attached.get(s.id) ?? [])])}`;
  }).join('\n');

  // An action branch can itself be branched from: its attachments hang in a band of their own, after the spine.
  const orphans = [...attached.keys()].filter((id) => !firstVisit.has(id))
    .map((id) => under(`the branch <a href="#${esc(id)}"><code>${esc(id)}</code></a>`, attached.get(id)!)).join('');

  const path = [...spine.screens.map((s) => `<a href="#${esc(s.id)}">${esc(s.id)}</a>${s.returnsTo !== null ? ' ↩' : ''}`)].join(' → ');
  const branches = variants.map((v) => `<li>${esc(v.title)} <small>— ${v.screens.map((s) => esc(s.id)).join(' → ')}</small></li>`).join('');
  const noise = pairs.map((p) => `<tr><td>${esc(p.what)}</td><td>${p.changed}</td><td>${p.lines}</td></tr>`).join('');
  const report = [...flaggedNames].map(([what, screens]) => `${what} (${[...screens].join(', ')})`);
  const flagged = report.map((r) => `<li>${esc(r)}</li>`).join('');

  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(meta.name)} — journey</title>
<style>${STYLE}</style></head><body><main${spine.screens.length <= 2 ? ` class="few" style="--n:${spine.screens.length}"` : ''}>
<div class="top">
<div class="crumb">design · journeys / ${esc(slug)} · <b>generated</b> from ${J.cases.length} case${J.cases.length === 1 ? '' : 's'} of ${src(meta.file)} · ${esc(renderStamp())} · clock fixed at ${esc(meta.now)}</div>
<h1>${esc(meta.name)}</h1>
<div class="intent"><p><b>Who</b> — ${esc(meta.who)}</p><p><b>Wants</b> — ${esc(meta.wants)}</p></div>
<div class="path"><b>Spine</b> — ${esc(spine.title)}: ${path}${branches ? `<ul>${branches}</ul>` : ''}</div>
</div>
<div class="spine">
${spineHtml}
${orphans}
</div>
<div class="end">
<div><h2>Names that read badly as actions</h2><ul>${flagged || '<li>none</li>'}</ul></div>
<div><h2>How far apart two captures are</h2>
<table><tr><td><b>pair</b></td><td><b>lines that differ (both sides)</b></td><td><b>lines in the first</b></td></tr>${noise}</table></div>
</div>
</main>
<script>${SCRIPT}</script>
</body></html>
`;
  return { html, report };
}

const STYLE = `
/* --s: how much a captured screen is scaled down. The frame itself stays 400 × 800, the capture's viewport. */
:root{--ink:#1c1917;--mute:#78716c;--line:#e7e5e4;--bg:#fafaf9;--accent:#b45309;--plan:#6d28d9;--var:#0f766e;--s:.7;--fw:calc(400px*var(--s));--fh:calc(800px*var(--s))}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}
main{padding:16px 16px 64px}
h1{font-size:24px;margin:0 0 4px}h3{margin:0 0 6px;font-size:15px}h4{margin:0 0 6px;font-size:14px}
code{font:12px ui-monospace,monospace;background:#f5f5f4;padding:1px 4px;border-radius:4px}small,.muted{color:var(--mute)}a{color:#1d4ed8}
a.src{color:inherit;text-decoration:underline dotted;font:12px ui-monospace,monospace;overflow-wrap:anywhere}
.top{max-width:1100px}.crumb{color:var(--mute);font-size:12.5px;margin-bottom:10px}.intent{border-left:3px solid var(--accent);padding:2px 12px;margin:10px 0}
.intent p{margin:2px 0}.path{margin:10px 0 14px;font-size:13.5px}.path ul{margin:4px 0 0}
/* The spine: one cell per screen, as many per row as fit. A cell is two rows of the grid — what led to the screen,
   then the screen — so the frames of a row start level. A band of comparisons takes a whole row under its screen's;
   the next screen then fills the place left beside it (dense), so the screens keep their order. */
.spine{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(540px,100%),1fr));grid-auto-flow:row dense;gap:12px}
.screen{grid-row:span 2;display:grid;grid-template-rows:subgrid;row-gap:0;min-width:0;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;scroll-margin-top:8px}
.screen.return{background:transparent;border-style:dashed}
.segment{padding:6px 12px 8px;background:var(--bg);border-bottom:1px solid var(--line);overflow-wrap:anywhere}
.segment::before{content:"What led here";display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.cause{padding:3px 0;font-size:13px;line-height:1.4}.cause .what{font-weight:600}.ctl{background:#fef3c7;border-radius:4px;padding:0 4px;font-weight:600}
.event,.crossed,.server{margin-left:12px;color:#44403c}.server{border-left:3px solid #0369a1;padding-left:8px;margin-top:4px}.server summary{cursor:pointer}.server>small{display:block;line-height:1.35}.server small code{font-size:11px}.crossed.mechanism,.crossed.none{color:var(--mute);font-size:12px}
.screen-body{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;padding:12px;min-width:0}
.shot{flex:none;box-sizing:content-box;width:var(--fw);height:var(--fh);overflow:hidden;border:1px solid #d6d3d1;border-radius:8px;background:#fff}
iframe.cap{display:block;width:400px;height:800px;border:0;transform:scale(var(--s));transform-origin:0 0}
/* The text beside a frame: a narrow column no taller than the frame, scrolling past that, with a shadow where more is hidden. */
.side,.note{flex:1 1 200px;min-width:0;max-height:calc(var(--fh) + 2px);overflow:auto;overflow-wrap:anywhere;font-size:13.5px;
  background:linear-gradient(#fff 30%,#fff0) top/100% 24px no-repeat local,linear-gradient(#fff0,#fff 70%) bottom/100% 24px no-repeat local,
    linear-gradient(#0000001f,#0000) top/100% 8px no-repeat scroll,linear-gradient(#0000,#0000001f) bottom/100% 8px no-repeat scroll}
.screen.return .side{background:none}
.n{display:inline-block;background:var(--ink);color:#fff;border-radius:99px;width:22px;height:22px;text-align:center;font-size:12.5px;line-height:22px}
.why{font-size:14.5px;margin:6px 0 8px}.facts{display:block;margin:4px 0}
.controls{margin-top:10px;font-size:12.5px}.controls summary{cursor:pointer;font-weight:600}
table{border-collapse:collapse;width:100%;margin-top:6px}td{border-top:1px solid var(--line);padding:3px 6px;vertical-align:top}
.controls td{overflow-wrap:normal}.controls td:nth-child(2){overflow-wrap:anywhere}.controls td:first-child{padding-left:0;color:var(--mute)}
tr.walked td{background:#f0fdf4}.notwalked{color:var(--mute);white-space:nowrap}.flag{background:#fee2e2;color:#991b1b;border-radius:4px;padding:0 4px;font-size:11.5px}
.under{grid-column:1/-1;min-width:0;background:#fff;border:1px dashed #d6d3d1;border-radius:12px;padding:8px 12px 12px}
.under .of{color:var(--mute);font-weight:600}
.under .items{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:flex-start}
.variant,.planned{flex:1 1 520px;max-width:640px;min-width:0;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start;border-left:3px solid var(--var);padding-left:12px}
.planned{flex-basis:820px;max-width:940px;border-left-color:var(--plan)}
.variant.action{display:block;flex-basis:600px;max-width:720px;scroll-margin-top:8px}.variant.action .segment{border:1px solid var(--line);border-radius:8px}.variant.action .screen-body{padding:12px 0 0}
.variant h4{color:var(--var)}.planned h4{color:var(--plan)}.bad{color:#b91c1c}
.pair{display:flex;gap:8px;flex-wrap:wrap}figure{margin:0}figcaption{font-size:12px;color:var(--mute);margin-bottom:2px}
.end{margin-top:28px;border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(auto-fit,minmax(min(440px,100%),1fr));gap:0 32px}.end h2{font-size:16px}.end>div{min-width:0;overflow-wrap:anywhere}
/* One screen per row and too narrow for text beside the frame: the text goes under it, at its full height. */
@media (max-width:560px){.side,.note{max-height:none;background:none}}
/* A journey of one or two screens: the cells take the middle of the window, and the screens are drawn larger. */
main.few{--s:.8;--fw:calc(400px*var(--s));--fh:calc(800px*var(--s));max-width:calc(var(--n)*772px + 20px);margin:0 auto}
main.few .spine{grid-template-columns:repeat(var(--n),minmax(0,1fr))}
@media (max-width:1123px){main.few .spine{grid-template-columns:minmax(0,1fr)}}
/* A feature's spec page: the intent as cards, then each changed screen as today against its mockup. */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:12px;margin:12px 0 4px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 14px;min-width:0;font-size:14px}
.rides{grid-template-columns:repeat(auto-fit,minmax(min(400px,100%),1fr))}.card ul ul{margin:2px 0 4px}.card .ctl{font-weight:500}
.card h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin:0 0 6px}.card p{margin:0 0 8px}.card ul{margin:0;padding-left:18px}.card li{margin:0 0 5px}
.card .slug{font:600 11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#4338ca;background:#eef2ff;border:1px solid #c7d2fe;border-radius:999px;padding:0 7px;margin-right:2px;white-space:nowrap}
.lead{color:var(--mute);margin:0 0 4px;font-size:13.5px}
h2.part{font-size:17px;margin:24px 0 2px}.changes{margin-top:8px}.change h3{font-size:16px;margin:0 0 4px}.change h3 small{font-weight:400}.change h3 small b{background:#ede9fe;border-radius:4px;padding:0 4px}
.changes{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(600px,100%),1fr));gap:12px}
.change{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px;min-width:0;scroll-margin-top:8px}
.change .planned{border-left:0;padding-left:0;max-width:none;margin-top:8px}.change .note{max-height:none;background:none}
.todos{margin-top:8px}.todos ul{margin:4px 0 0;padding-left:18px}.todos li{margin:0 0 5px}
`;

const SCRIPT = `
// A capture carries its scroll offsets as attributes and no script: the page applies them once a frame has laid out.
// A frame with outlined differences is scrolled to the first one instead, and its neighbour in a pair follows it.
const scrollers = (f) => [...f.contentDocument.querySelectorAll('[data-capture-scroll]')];
const settle = (f) => { try {
  for (const el of scrollers(f)) { const [t, l] = el.getAttribute('data-capture-scroll').split(',').map(Number); el.scrollTop = t; el.scrollLeft = l; }
  const first = f.contentDocument.querySelector('[data-jd]');
  // scrollIntoView reaches up through the frame into this page: the page is put back where the reader had it.
  if (first) { const x = scrollX, y = scrollY; first.scrollIntoView({ block: 'center' }); scrollTo(x, y); }
} catch {} };
const follow = (pair) => { try {
  const frames = [...pair.querySelectorAll('iframe.cap')];
  const lead = frames.find((f) => f.contentDocument.querySelector('[data-jd]'));
  if (!lead) return;
  for (const f of frames) if (f !== lead) scrollers(f).forEach((el, i) => { el.scrollTop = scrollers(lead)[i]?.scrollTop ?? el.scrollTop; });
} catch {} };
for (const f of document.querySelectorAll('iframe.cap')) {
  const done = () => { settle(f); const pair = f.closest('.pair'); if (pair) follow(pair); };
  f.addEventListener('load', done); done();
}
`;

// ── a feature's spec page ────────────────────────────────────────────────────────────────────────────────

const FEATURES = join(ROOT, FEATURES_FOLDER);
const GENERATED = '<meta name="generator" content="journey-render">';

/**
 * `spec.md` as HTML: its title, the lines under it, then one card per `##` section. A section holds paragraphs
 * and `- ` lists and nothing else: the intent is prose, and what has a structure is declared on the journeys.
 */
function intentOf(file: string): { title: string; lead: string; cards: string } {
  const inline = (t: string) => lite(t).replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2">$1</a>');
  // The parser is shared with the plan page (`intent-md.ts`); an item's slug — a rule's name — is drawn as a chip.
  const intent = parseIntent(readFileSync(file, 'utf8'), file);
  return {
    title: intent.title,
    lead: blocksHtml(intent.lead, inline),
    cards: intent.sections.map((sec) => `<section class="card"><h2>${esc(sec.title)}</h2>${blocksHtml(sec.blocks, inline)}</section>`).join(''),
  };
}

/** A feature's spec as data, written beside the page for `comprehension_harness/map.mjs` (`npm run map -- spec <feature>`). */
interface SpecMap {
  feature: string;
  builtAt: string;
  /** Every file the spec was read from, with its modification time: `map.mjs` rebuilds when one moved. */
  inputs: Record<string, number>;
  intent: string;
  journeys: Array<{
    slug: string; name: string; file: string; who: string; wants: string; now: string;
    path: string[];
    changed: Array<{ id: string; why: string; planned: { what: string; mockup: string } | null; todos: Array<{ title: string; line: number }> }>;
    unreached: Array<{ screen: string; title: string; line: number }>;
  }>;
  rides: {
    narratives: Array<{ slug: string; kind: string; title: string; at: Array<{ screen: string; to: number[]; from: number[] }>; branches: Array<{ file: string; line: number; fn: string | null; toldBy: string; at: string[] }> }>;
    orphans: Array<{ file: string; line: number; fn: string | null; at: string[] }>;
    silent: Array<{ what: string; at: string[] }>;
    server: Array<{ name: string; method: string; does: string; truth: string; at: string[] }>;
  };
}

/**
 * What a feature's changed screens ride on, read from the run: every case that reaches a changed screen is
 * followed from its opening to that screen, and through the segment that leaves it. Out come the narrative
 * steps crossed, with the branches a narrative's other cases tell (the plan's input); the server steps answered
 * by a stub, where the run saw nothing of the real path; and, drawn only when there is one, what was crossed
 * that no case of any narrative reaches — a `narrate` no narrative test crosses, or an action that crosses no
 * step of a product narrative (the narrate stage's queue).
 * Candidates, all three: a step crossed is not a step the feature changes, and a change with no screen
 * (a migration, a type) is on no list.
 */
class Rides {
  private narratives = new Map<string, {
    narrative: Narrative; page: string; href: Map<number, string>;
    at: Map<string, { to: Set<number>; from: Set<number> }>;
    branches: Map<string, { site: StorySite; told: string; at: Set<string> }>;
  }>();
  private orphans = new Map<string, { site: StorySite; at: Set<string> }>();
  private silent = new Map<string, Set<string>>();
  private server = new Map<string, { call: ServerCall; at: Set<string> }>();

  constructor(private linkOf: (site: StorySite, sentence: string) => StepLink | null) {}

  walk(J: Loaded, id: string): void {
    const address = `${J.slug}#${id}`;
    for (const c of J.cases) {
      const k = c.screens.findIndex((s) => s.id === id);
      if (k < 0) continue;
      c.screens.slice(0, k + 1).forEach((s, i) => { for (const cause of s.before) this.cause(address, 'to', cause, i > 0 ? c.screens[i - 1] : null); });
      for (const cause of c.screens[k + 1]?.before ?? c.after) this.cause(address, 'from', cause, c.screens[k]);
    }
  }

  private cause(address: string, side: 'to' | 'from', cause: Cause, from: ScreenRecord | null): void {
    let product = false;
    for (const step of cause.steps) {
      const link = this.linkOf(step.site, step.sentence);
      if (!link) {
        const key = `${step.site.file}:${step.site.line}`;
        const orphan = this.orphans.get(key) ?? { site: step.site, at: new Set<string>() };
        this.orphans.set(key, orphan);
        orphan.at.add(address);
        continue;
      }
      if (link.narrative.kind === 'product') product = true;
      const entry = this.narratives.get(link.narrative.slug) ?? { narrative: link.narrative, page: link.href.split('#')[0], href: new Map(), at: new Map(), branches: new Map() };
      this.narratives.set(link.narrative.slug, entry);
      if (link.n === null) {
        const key = `${step.site.file}:${step.site.line}`;
        const branch = entry.branches.get(key) ?? { site: step.site, told: link.branch!, at: new Set<string>() };
        entry.branches.set(key, branch);
        branch.at.add(address);
        continue;
      }
      entry.href.set(link.n, link.href);
      const at = entry.at.get(address) ?? { to: new Set<number>(), from: new Set<number>() };
      entry.at.set(address, at);
      at[side].add(link.n);
    }
    for (const call of cause.server ?? []) {
      const seen = this.server.get(call.name) ?? { call, at: new Set<string>() };
      this.server.set(call.name, seen);
      seen.at.add(address);
    }
    // A cause that crosses no step of a product narrative: what it ran is told nowhere.
    if (!product) {
      const what = `${cause.kind === 'open' ? 'the case ' : cause.kind === 'time' ? '' : `the ${config.actor} `}${causeWhat(cause, from)}`;
      this.silent.set(what, (this.silent.get(what) ?? new Set<string>()).add(`${side === 'to' ? 'before' : 'from'} ${address}`));
    }
  }

  /** The same facts as `html()`, plain: what `npm run map -- spec <feature>` prints for an agent. */
  data(): SpecMap['rides'] {
    const nums = (ns: Set<number>) => [...ns].sort((a, b) => a - b);
    return {
      narratives: [...this.narratives.values()].map((e) => ({
        slug: e.narrative.slug,
        kind: e.narrative.kind,
        title: e.narrative.title,
        at: [...e.at].map(([screen, at]) => ({ screen, to: nums(at.to), from: nums(at.from) })),
        branches: [...e.branches.values()].map((b) => ({ file: b.site.file, line: b.site.line, fn: b.site.fn ?? null, toldBy: b.told, at: [...b.at] })),
      })),
      orphans: [...this.orphans.values()].map((o) => ({ file: o.site.file, line: o.site.line, fn: o.site.fn ?? null, at: [...o.at] })),
      silent: [...this.silent].map(([what, at]) => ({ what: what.replace(/<[^>]+>/g, ''), at: [...at] })),
      server: [...this.server.values()].map((v) => ({ name: v.call.name, method: v.call.method, does: v.call.does, truth: v.call.truth, at: [...v.at] })),
    };
  }

  html(): string {
    const steps = (href: Map<number, string>, ns: Set<number>) => [...ns].sort((a, b) => a - b).map((n) => `<a href="${esc(href.get(n)!)}">${n}</a>`).join(' ');
    const code = (xs: Iterable<string>) => [...xs].map((x) => `<code>${esc(x)}</code>`).join(', ');
    const row = (kind: string) => [...this.narratives.values()].filter((e) => e.narrative.kind === kind).map((e) => `<li><b><a href="${esc(e.page)}#${esc(e.narrative.slug)}">${esc(e.narrative.title)}</a></b>
        <ul>${[...e.at].map(([address, at]) => `<li><code>${esc(address)}</code> — ${[at.to.size ? `to reach it, steps ${steps(e.href, at.to)}` : '', at.from.size ? `from it, steps ${steps(e.href, at.from)}` : ''].filter(Boolean).join('; ')}</li>`).join('')}${
          [...e.branches.values()].map((b) => `<li>the branch at ${src(b.site.file, b.site.line, `${b.site.fn ?? '?'}:${b.site.line}`)}, told by its case “${esc(b.told)}” — at ${code(b.at)}</li>`).join('')}</ul></li>`).join('');
    const product = row('product'), mechanisms = row('mechanism');
    const orphans = [...this.orphans.values()].map((o) => `<li><code>${esc(o.site.fn ?? '?')}</code> <small>${src(o.site.file, o.site.line)}</small> — a <code>narrate</code> crossed at ${code(o.at)}, reached by no case of any narrative</li>`).join('');
    const silent = [...this.silent].map(([what, at]) => `<li>${what} <small>— ${esc([...at].join(', '))}</small>: crosses no step of a product narrative</li>`).join('');
    const server = [...this.server.values()].map((v) => `<li><b>${esc(v.call.name)}</b> <small>${esc(v.call.method)}</small> — ${lite(v.call.does)} Pinned by ${src(v.call.truth)}; on the path of ${code(v.at)}</li>`).join('');
    return `<h2 class="part">What the change rides on — read from the run</h2>
<p class="lead">Every case that reaches a changed screen, followed from its opening to that screen and through the segment that leaves it. Candidates: a step crossed is not a step the feature changes, and a change with no screen (a migration, a type) is on no list.</p>
<div class="cards rides">
<section class="card"><h2>Narrative steps crossed — the plan's input</h2><ul>${product || '<li>none</li>'}</ul>${mechanisms ? `<p class="lead">Mechanisms ridden</p><ul>${mechanisms}</ul>` : ''}</section>
${orphans || silent ? `<section class="card"><h2>Crossed, told by no narrative — the narrate stage's queue</h2><ul>${orphans}${silent}</ul></section>` : ''}
<section class="card"><h2>Answered by a stub — the run did not see the server</h2><ul>${server || '<li>no server step on these paths</li>'}</ul></section>
</div>`;
  }
}

/**
 * The spec of a feature as a change to the journeys: its `spec.md`, then every journey the feature plans something
 * on — the spine named, the changed screens drawn today against their mockup with the cases to add. Which journeys
 * those are is read from the journey tests (`planned`, `todo`); nothing lists them.
 */
function renderSpec(feature: string, journeys: Loaded[], linkOf: (site: StorySite, sentence: string) => StepLink | null): { html: string; screens: number; cases: number; map: SpecMap } {
  const md = join(FEATURES, feature, 'spec.md');
  const intent = intentOf(md);
  let screens = 0, cases = 0;
  const rides = new Rides(linkOf);
  const mapJourneys: SpecMap['journeys'] = [];
  const sections = journeys.map((J) => {
    const spine = J.cases[0];
    const meta = spine.journey;
    const page = `${TO_JOURNEYS}/${J.slug}.html`;
    const base = `${TO_JOURNEYS}/${J.slug}`;
    const mine = (meta.todos ?? []).filter((t) => t.feature === feature);
    const first = spine.screens.filter((s, k) => spine.screens.findIndex((o) => o.id === s.id) === k);
    const changed = first.filter((s) => s.planned?.feature === feature || mine.some((t) => t.screen === s.id));
    const unreached = mine.filter((t) => !first.some((s) => s.id === t.screen));
    screens += changed.length; cases += mine.length;
    for (const s of changed) rides.walk(J, s.id);
    mapJourneys.push({
      slug: J.slug, name: meta.name, file: meta.file, who: meta.who, wants: meta.wants, now: meta.now,
      path: spine.screens.map((s) => s.id),
      changed: changed.map((s) => ({
        id: s.id, why: s.why,
        planned: s.planned?.feature === feature ? { what: s.planned.what, mockup: s.planned.mockup } : null,
        todos: mine.filter((t) => t.screen === s.id).map((t) => ({ title: t.title, line: t.line })),
      })),
      unreached: unreached.map((t) => ({ screen: t.screen, title: t.title, line: t.line })),
    });
    const path = spine.screens.map((s) => (changed.some((c) => c.id === s.id) && s.returnsTo === null
      ? `<b><a href="#${esc(J.slug)}--${esc(s.id)}">${esc(s.id)}</a></b>`
      : `<a href="${page}#${esc(s.id)}">${esc(s.id)}</a>${s.returnsTo !== null ? ' ↩' : ''}`)).join(' → ');
    const later = unreached.length === 0 ? '' : `<div class="todos"><b>At a screen this journey does not reach yet</b><ul>${unreached.map((t) => `<li><code>${esc(t.screen)}</code> — ${lite(t.title)} <small>${src(meta.file, t.line, `line ${t.line}`)}</small></li>`).join('')}</ul></div>`;
    if (changed.length === 0) return `<section class="change"><h3><a href="${page}">${esc(meta.name)}</a> <small>— ${path}</small></h3>${later}</section>`;
    return changed.map((s, k) => `<section class="change" id="${esc(J.slug)}--${esc(s.id)}">
        <h3><a href="${page}">${esc(meta.name)}</a> <small>— ${path}</small></h3>
        <p class="lead"><code>${esc(J.slug)}#${esc(s.id)}</code>, screen ${spine.screens.indexOf(s) + 1} of ${first.length} (${src(meta.file, spine.line, `case line ${spine.line}`)}). Today — ${esc(s.why)}</p>
        ${plannedBlock(J, spine, s, feature, base).html}${k === changed.length - 1 ? later : ''}</section>`).join('\n');
  }).join('\n');
  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">${GENERATED}
<title>${esc(intent.title)} — spec</title>
<style>${STYLE}</style></head><body><main>
<div class="crumb">features / ${esc(feature)} · spec · <b>generated</b> from ${src(`${featureFolder(feature)}/spec.md`, null, 'spec.md')} and ${journeys.map((J) => src(J.cases[0].journey.file, null, J.cases[0].journey.file.split('/').pop())).join(', ')} · ${esc(renderStamp())}</div>
<h1>${esc(intent.title)}</h1>
<div class="lead">${intent.lead}</div>
<div class="cards">${intent.cards}</div>
<h2 class="part">What changes on screen — ${screens} screen${screens === 1 ? '' : 's'} of ${journeys.length} journey${journeys.length === 1 ? '' : 's'}, ${cases} case${cases === 1 ? '' : 's'} to add</h2>
<p class="lead">Each changed screen today against its mockup, the elements that differ outlined. A journey's other screens are on its own page.</p>
<div class="changes">
${sections}
</div>
${rides.html()}
</main>
<script>${SCRIPT}</script>
</body></html>
`;
  const inputs: Record<string, number> = {};
  const input = (file: string) => { const abs = join(ROOT, file); if (existsSync(abs)) inputs[file] = statSync(abs).mtimeMs; };
  input(`${featureFolder(feature)}/spec.md`);
  input(SELF);
  for (const J of journeys) {
    input(J.cases[0].journey.file);
    for (const f of readdirSync(join(J.dir, 'cases'))) input(join(JOURNEYS, J.slug, 'cases', f));
  }
  const map: SpecMap = { feature, builtAt: new Date().toISOString(), inputs, intent: readFileSync(md, 'utf8'), journeys: mapJourneys, rides: rides.data() };
  return { html, screens, cases, map };
}

// A checkout no journey test has run on has nothing to draw. That is a cold start, not a failure:
// `npm run docs` ends with this script and makes no browser run, as it makes no unit run for the narratives.
const slugs = existsSync(OUT) ? readdirSync(OUT).filter((d) => existsSync(join(OUT, d, 'journey.json'))) : [];
if (slugs.length === 0) {
  console.log(`journey-render: no journey run on this checkout, no page rendered — ${typed(config.commands.journeys)}, then npm run journey:render`);
  process.exit(0);
}
const { linkOf, stories } = narrativeIndex();
if (stories === 0) console.warn(`journey-render: ${NO_STORIES}; narrative steps are listed unlinked`);
for (const slug of slugs) {
  const { html, report } = render(slug, linkOf);
  const out = join(OUT, `${slug}.html`);
  writeFileSync(out, html);
  console.log(`journey-render: ${out} (${(Buffer.byteLength(html) / 1024).toFixed(0)} kB)`);
  for (const line of report) console.log(`  name: ${line}`);
}

// A feature's spec page, for every feature a journey test plans something for.
const loaded = slugs.map(load).filter((J) => J.cases.length > 0);
const featuresOf = (J: Loaded) => new Set([...J.cases[0].screens.flatMap((s) => (s.planned ? [s.planned.feature] : [])), ...(J.cases[0].journey.todos ?? []).map((t) => t.feature)]);
for (const feature of [...new Set(loaded.flatMap((J) => [...featuresOf(J)]))].sort()) {
  const out = join(FEATURES, feature, 'spec.html');
  if (!existsSync(join(FEATURES, feature, 'spec.md'))) {
    console.warn(`journey-render: a journey plans screens for ${feature}, which has no ${featureFolder(feature)}/spec.md — no spec page`);
    continue;
  }
  if (existsSync(out) && !readFileSync(out, 'utf8').includes(GENERATED)) throw new Error(`journey-render: ${out} is hand-written — remove it before its feature's spec is rendered there`);
  const { html, screens, cases, map } = renderSpec(feature, loaded.filter((J) => featuresOf(J).has(feature)), linkOf);
  writeFileSync(out, html);
  mkdirSync(MAP_DIR, { recursive: true });
  writeFileSync(join(MAP_DIR, `spec-${feature}.json`), JSON.stringify(map));
  console.log(`journey-render: ${out} (${screens} screen${screens === 1 ? '' : 's'}, ${cases} case${cases === 1 ? '' : 's'}, ${(Buffer.byteLength(html) / 1024).toFixed(0)} kB)`);
}
