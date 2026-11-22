/**
 * plan.ts — a feature's plan as data: the model `comprehension_harness/render.ts` draws as
 * `specs/comprehension_harness/plans/<feature>.html`, and the pure parts that build it (no source reader, no disk, no story file:
 * `comprehension_harness/tests/plan.test.ts` builds its inputs by hand).
 *
 * A plan is never written as a list. A piece is a slug, `<feature>#<slug>`, and every site tagged with it:
 *
 *  - a `planned('<feature>#<slug>', '<sentence>')` call on existing code, a
 *    `planned.remove(…)`, or the only body of an empty shell — read from the source by the stack's reader; `render.ts`
 *    reads from the stories which canonical story crosses each call, and when (`PlanSite`);
 *  - a test to write titled `<feature>#<slug>: <title> [rule-slug]` (a test declared with no body) in a test file of
 *    any tier (`scanTodos`). The tier is where the file stands: `narrative` in a folder of narrative tests,
 *    `server` for a test of the real server a server step names as its truth, `unit` otherwise (`Layout.tierOf`);
 *  - a comment that opens with the word `@planned` and the tag, where there is no runtime line — a type, the
 *    database's schema, a SQL file, a doc made stale (`scanPlannedComments`). The comment syntax is the file's own:
 *    `//` and block comments in TypeScript and CSS, `--` in SQL, an HTML comment in markdown and HTML, `#`
 *    elsewhere. A mention of the word in prose or in a string is not a comment and is not a site.
 *
 * Each fact has one home. A site says what changes at its place, in one clause. A test title says the behaviour
 * and its case. `specs/features/<feature>/plan.md` holds the rest: a title, a lead, then one `## #slug` section
 * per piece — its statement (the first paragraph), its reason (what follows), at most one paragraph opening
 * `To confirm:` for a point the reviewer must answer, its question in bold, and any paragraph opening `Note:`
 * for something the piece was built with that no line of the plan says and what follows stands on, its
 * point in bold: it is read, kept, and asks no answer. A section with any other title is a
 * decision across pieces; it names the pieces it concerns as `#slug`, and each piece lists the sections naming it.
 * `BUDGET` caps each piece in words, and `findings` fails what is over.
 *
 * The pieces are told in run order (`assemblePlans`): grouped by narrative, product narratives first, each piece
 * under the first narrative whose canonical story crosses one of its `planned` calls, in the order that story
 * first crosses them. Then the pieces whose calls no canonical story crosses (a shell is one), then the pieces
 * with no runtime line, both in file order.
 *
 * Ownership: each rule of `spec.md` § "Rules no screen shows" opens with a slug, and the one test that owns it
 * ends its title with `[slug]`. `findings` fails a `[slug]` that names no rule and a rule with two owners; a
 * rule with no owner is listed. A rule the plan gives no test is waived in `plan.md` § "Rules no test holds",
 * with the reason; it then has no owner, and a rule with both fails.
 */
import { sluggedItems, type Intent, type MdBlock, type MdSection } from './intent-md';
import type { Layout, Tier } from './layout';
import type { NarrativeKind, Stand, TitleReader } from './stack';

/** The piece of a plan a site belongs to: `<feature>#<slug>`, both kebab-case. */
export interface PlannedTag {
  /** The folder under `specs/features/`. */
  feature: string;
  /** The piece's name, unique per feature; every site tagged with it is one piece. */
  slug: string;
}

interface At {
  /** Relative to the repository root. */
  file: string;
  line: number;
  column: number;
}

/** A `planned` call, as the source states it and as the run saw it. */
export interface PlanSite extends PlannedTag, At {
  /** Unique per call: `planned:<feature>#<slug>@<file>:<line>`. */
  id: string;
  /** The function the call sits in. */
  fn: string;
  /** `changed`: on existing code. `removed`: `planned.remove`. `added`: the only body of a shell. */
  change: 'changed' | 'removed' | 'added';
  /** What changes at this place, in one clause (`BUDGET.clause`). The reason is `plan.md`'s, the cases the
   *  test titles'; the `narrate` sentence is written when the piece is implemented. */
  sentence: string;
  /** A shell's declaration text up to its body; null otherwise. */
  signature: string | null;
  /** The narratives whose canonical story crosses the call. `at` is the position of the first crossing among
   *  the story's hits; `step` the canonical step the change lands in (its number and label), null when none
   *  could be told. `how` says how it was told: `in`, the call sits in the step's own function; `via`, in a
   *  helper the step's sentence names or that the step's function called; `after`, in code that ran right after
   *  the step with no call between them the run could see (a child component, an awaited helper). */
  crossedBy: Array<{ narrative: string; at: number; step: { n: number; label: string; how: 'in' | 'via' | 'after' } | null }>;
  /** Every test that reaches the call, by file, with the titles: what the tasks stage reads before it plans a
   *  unit test, so that no case is written twice and a case a narrative now holds is deleted. */
  reachedBy: Array<{ file: string; tests: number; titles: string[] }>;
}

/** A `@planned` comment: a site with no runtime line. */
export interface StaticSite extends PlannedTag, At {
  /** What follows the tag, with the comment lines that continue it. */
  text: string;
  /** `@planned.remove`: what stands under the comment goes — an existing test a planned case now holds, a type.
   *  The text says what holds it instead. */
  removes: boolean;
  /** What the comment stands on, read off the first line of code under it: the name a declaration gives
   *  (`ruleBounds`), or the title of a test (`it "a tap moves the figure"`). Null when that line is
   *  neither, when a blank line parts them, and in a file the stack's title reader does not read. So a reader finds
   *  a comment site by the name of what it changes, and a removal says which test goes. */
  on: string | null;
}

export type { Tier };
export const TIERS: readonly Tier[] = ['narrative', 'server', 'unit'];

/** A test titled `<feature>#<slug>: <title> [rule]`: to write, or written with its tag kept. */
export interface PlanTodo extends PlannedTag, At {
  /** The title with the tag and the rule suffix taken off. */
  title: string;
  /** The rule of `spec.md` the test owns, as its title's `[slug]` suffix claims; null when it claims none. */
  rule: string | null;
  tier: Tier;
  /** False for a test to write, declared with no body. True for a test that exists and kept its tag — an implemented
   *  piece's test keeps `<feature>#<slug>: … [rule]` in its title until the feature is archived, so a rule's
   *  owner can still be read once nothing is planned any more. */
  written: boolean;
}

/** A case the spec declared in a journey test and nobody has written yet: `todo(<feature>, <screen>, <title>)`
 *  inside `journey('<name>', …)`. It is a criterion of the spec, tagged with the feature and with no piece: a
 *  journey case usually needs several pieces, and is written once they are in. */
export interface JourneyCase extends At {
  feature: string;
  journey: string;
  screen: string;
  title: string;
}

/** A `plan.md` section: a piece's own (`## #slug`), or a decision across pieces. */
export interface PlanSection extends MdSection {
  /** The section's anchor on the plan page. */
  anchor: string;
  /** The piece the section is titled after, `## #slug`; null for a decision across pieces. */
  piece: string | null;
  /** The `#slug`s its text names, in order, each once. */
  slugs: string[];
  /** Its paragraphs opening `Changed:`, the prefix taken off, one an edit: `what` moved since the approval
   *  (`PlanBaseline`), the paragraph's bold opening, and `why`, the rest. `text` is both, for the budget. A
   *  reason with no `what` leaves the reader asking which change it speaks of. */
  changed: PlanChange[];
}

/** One `Changed:` paragraph: `Changed: **what moved.** why → code "fragment"; test "fragment"`. The claims after
 *  the arrow name the lines of the delta the edit comes to, a kind and a fragment the line holds; a section with
 *  one paragraph needs none, every line is its. */
export interface PlanChange {
  what: string | null;
  why: string;
  /** What and why, the claims left out: what the budget counts. */
  text: string;
  claims: Array<{ kind: string; fragment: string }>;
  line: number;
}

/** The kinds a claim names a line by: a place in the code, a test (to write, changing or going), the piece's
 *  statement, its reason, a decision's text. */
export const CLAIM_KINDS = ['code', 'test', 'statement', 'reason', 'text'] as const;

export type Difficulty = 'easy' | 'standard' | 'hard';

/** One item of `plan.md` § "Delivery": the pieces one implementer delivers and one reviewer reads, a commit a
 *  piece. `- **the-slug** (hard) #piece #piece @screen — why these together, and why here`. */
export interface PlanLot {
  slug: string;
  /** What is left for the implementer, which picks its model; `standard` when the item says nothing. */
  difficulty: Difficulty;
  /** The pieces, in the order they are committed. */
  pieces: string[];
  /** The screens whose journey cases the lot writes last, `@screen`: the lot completes the pieces behind them. */
  screens: string[];
  reason: string;
  line: number;
}

/** What `plan.md` says of one piece, read off its `## #slug` section. */
export interface PlanPieceDoc {
  section: PlanSection;
  /** The statement: the section's first paragraph. */
  what: string;
  /** The reason, and what was refused: the blocks after the statement. */
  why: MdBlock[];
  /** A point the reviewer must answer: the paragraph opening `To confirm:`, its bold part the question. */
  ask: { question: string; detail: string; line: number } | null;
  /** What the piece was built with that no line of the plan says, and that a later lot or the reader of the
   *  code stands on: the paragraphs opening `Note:`, the bold part the point. A note asks no answer and no
   *  `Changed:`; it stays in the plan, and the approval holds it. */
  notes: PlanNote[];
}

export interface PlanNote {
  what: string | null;
  detail: string;
  /** What and detail, as written: the line the approval holds, and what the budget counts. */
  text: string;
  line: number;
}

/** Words at most. A piece over its budget fails `--check`: the page is read, so it stays short. */
export const BUDGET = { clause: 25, title: 20, what: 30, why: 60, ask: 60, changed: 40, lot: 40, note: 40, pointer: 40 } as const;

export const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

/** A `narrate` sentence: words at most, and bolds at most */
export const SENTENCE_BUDGET = { words: 60, bolds: 1 } as const;

/** What a `narrate` sentence is over, one line per budget; empty when it is within both. The `**` marks are
 *  not words. */
export function overSentenceBudget(sentence: string): string[] {
  const over: string[] = [];
  const n = words(sentence.replace(/\*\*/g, ''));
  const bolds = (sentence.match(/\*\*[^*]+\*\*/g) ?? []).length;
  if (n > SENTENCE_BUDGET.words) over.push(`tells its step in ${n} words, and the budget is ${SENTENCE_BUDGET.words} — a step tells its own line, and a branch is its test's`);
  if (bolds > SENTENCE_BUDGET.bolds) over.push(`holds ${bolds} bolds, and a sentence has ${SENTENCE_BUDGET.bolds} at most — the bold is the rule the step enacts`);
  return over;
}

export interface PlanDoc {
  file: string;
  title: string;
  lead: MdBlock[];
  /** The pieces' sections and the decisions across pieces; the waivers' section is not one of them. */
  sections: PlanSection[];
  /** The items of "## Rules no test holds". */
  waivers: PlanWaiver[];
  /** The items of "## Delivery", in delivery order; empty until the tasks stage has written the section. */
  lots: PlanLot[];
  /** The items of "## Planned elsewhere". */
  pointers: PlanPointer[];
}

/** A piece this plan relies on and does not hold: it is planned, built and approved in the plan of the same
 *  feature in another repository. `- **the-repository** #the-slug — what this plan relies on`. A plan is local
 *  to the changes of its repository; a pointer is how one that spans two says so. */
export interface PlanPointer {
  repository: string;
  slug: string;
  reason: string;
  line: number;
}

/** What the repository a pointer names says of the piece, read from its checkout. */
export interface PointerTarget {
  /** The piece's statement there; null when that plan holds no such piece. */
  statement: string | null;
  /** The day that plan was approved with the piece in it; null while it was not. */
  approvedOn: string | null;
  /** Its `plan.md`, as an absolute path, and the line of the piece's section. */
  source: string;
  line: number;
}

/** A rule of the spec the plan gives no test, with the reason: `- **the-rule** why no test`. The reviewer
 *  validates it. One whose reason opens `To confirm:` still waits for that. */
export interface PlanWaiver {
  rule: string;
  reason: string;
  toConfirm: boolean;
  line: number;
}

export interface PlanPiece {
  slug: string;
  /** The `planned` calls, in file order. */
  sites: PlanSite[];
  /** The `@planned` comments, in file order. */
  statics: StaticSite[];
  /** The planned tests of every tier, in file order (`todosByTier` groups them). */
  todos: PlanTodo[];
  /** The proposed migrations: the `.sql` files of the feature folder tagged for this piece. */
  sql: string[];
  /** The piece's own section of `plan.md`; null when the file has none for it. */
  doc: PlanPieceDoc | null;
  /** The decisions across pieces that name this one. */
  decidedIn: PlanSection[];
  /** What the approved plan held of the piece and is now code: the lines of its sites and of its comments, as
   *  approved, whose place holds no planned line any more. Empty until a delivery is approved: before that, a
   *  line that went was taken off the plan. A built line stays in the plan, so the approval is still read once
   *  the place is code. */
  built: { sites: string[]; comments: string[] };
  /** The commits that deliver the piece, oldest first: those whose message names it (`PieceCommit`). */
  commits: PieceCommit[];
}

/**
 * A commit that delivers a piece: its message holds the line `Piece: <feature>#<slug>`, once per piece it
 * delivers — one for a piece's own commit and for a fix of it, several for a lot's closing commit, which tells
 * the steps of each piece it names. Read from git by `comprehension_harness/commits.ts`.
 */
export interface PieceCommit {
  sha: string;
  subject: string;
  /** The pieces of the feature it names, in the order of the message. */
  pieces: string[];
  /** Made after the approval on file: what the lot check reads. An earlier one is covered by that approval. */
  sinceApproval: boolean;
  /** What it touched: the lines added and removed, and the first line it changed, null for a file it deleted. */
  files: Array<{ file: string; added: number; removed: number; line: number | null }>;
  /** Tests the lot added under no planned title — read from the approved code to the file as it stands
   *  (`testChanges`), so against the comments the approval held — and that this commit brought in. Empty for a
   *  commit the approval covers. */
  untagged: Array<{ file: string; title: string }>;
  /** Tests the lot deleted with no comment of the plan standing on them, read the same way, and that this
   *  commit took out. Empty for a commit the approval covers. */
  deleted: Array<{ file: string; title: string }>;
  /** Tests it deleted or changed as a comment of the plan said: the test, and the comment's words. */
  planned: Array<{ file: string; title: string; removes: boolean; text: string }>;
}

/** `narrative`: crossed by that narrative's canonical story, in run order. `uncrossed`: has a `planned` call no
 *  canonical story crosses. `static`: has no `planned` call. */
export interface PlanGroup {
  kind: 'narrative' | 'uncrossed' | 'static';
  narrative: string | null;
  pieces: PlanPiece[];
}

/** A rule of `spec.md` § "Rules no screen shows" and the tests that claim it. One owner is the rule, or a
 *  waiver of `plan.md` and no test. */
export interface PlanRule {
  slug: string;
  text: string;
  line: number;
  owners: PlanTodo[];
  waiver: PlanWaiver | null;
}

export interface Plan {
  feature: string;
  /** `specs/features/<feature>/` exists. */
  folderExists: boolean;
  /** `plan.md`, when the feature folder holds one. */
  doc: PlanDoc | null;
  /** The pieces as they are told. */
  groups: PlanGroup[];
  /** The same pieces, flat, in the order of `groups`. */
  pieces: PlanPiece[];
  /** `spec.md`, when the feature folder holds one: where `rules` were read. */
  rulesFile: string | null;
  rules: PlanRule[];
  /** A test whose `[slug]` names no rule of `spec.md`. */
  unknownRules: PlanTodo[];
  /** The spec's journey cases still to write, by file then line. */
  journeyCases: JourneyCase[];
  /** The journey cases the approved plan held and that are written: their lines as approved. Empty until a
   *  delivery is approved. */
  builtCases: string[];
  /** The approved plan holds a delivery: the plan is being implemented, and a place that went is code. */
  implementing: boolean;
  /** The commits that name a piece of the feature, oldest first. */
  commits: PieceCommit[];
  /** A commit names a piece the plan does not hold. */
  unknownCommitPieces: Array<{ sha: string; slug: string }>;
  /** False when the commit of the approval is not in this branch's history: no commit can be told to come
   *  after it, and the lot check reads none. */
  baseKnown: boolean;
  /** A waiver of `plan.md` that names no rule of `spec.md`. */
  unknownWaivers: PlanWaiver[];
  /** A `#slug` of `plan.md` that names no piece. */
  unknownRefs: Array<{ slug: string; section: string; line: number }>;
  /** A `#slug` of a lot that names no piece, planned or approved. */
  unknownLotPieces: Array<{ slug: string; lot: string; line: number }>;
  /** The pieces planned elsewhere, each with what its repository says of it; `target` is null when the
   *  configuration names no checkout of that repository, or none is there. */
  pointers: Array<PlanPointer & { target: PointerTarget | null }>;
  /** The plan as it stands, in the form it is approved in. */
  snapshot: PlanSnapshot;
  /** The approval on file, `plan.approved.json`; null while the plan was never approved. */
  approved: { file: string; base: string; approvedOn: string } | null;
  /** What differs from the approved plan, a unit at a time; null while there is no approval to differ from. */
  delta: UnitDelta[] | null;
  /** What one piece lost and another gained, word for word, since the approval: the same thing is planned, by
   *  another piece and maybe in another lot. It asks no reason and no answer. */
  moves: PlanMove[];
  /** The reviewer's answers on file, by item key (`reviewItems`); an answer whose key names no item is of an
   *  earlier wording. */
  feedback: PlanFeedback;
}

// ── The approved plan and what differs from it ─────────────────────────────────

export type UnitKind = 'piece' | 'decision' | 'waivers' | 'elsewhere' | 'delivery' | 'journey' | 'story';

/** One thing a reviewer approves, as lines by facet. No line holds a line number: moving code changes nothing. */
export interface SnapshotUnit {
  kind: UnitKind;
  /** `#slug` for a piece, the section's title for a decision, the narrative's title for a story. */
  name: string;
  facets: Record<string, string[]>;
}

export interface PlanSnapshot {
  units: SnapshotUnit[];
}

/** `specs/features/<feature>/plan.approved.json`: the plan as the reviewer approved it. Written by
 *  `comprehension-render --approve <feature>` on the reviewer's word and by nothing else. */
export interface PlanBaseline extends PlanSnapshot {
  feature: string;
  /** The commit the approval was given on: what the code and the tests were, for whoever compares them later. */
  base: string;
  approvedOn: string;
}

/** A unit that is not as approved. `reason`: `needed`, the change is one the reviewer must be told of and the
 *  unit's section says no `Changed:`; `given`, it does; `none`, the change asks for no reason. */
export interface UnitDelta {
  kind: UnitKind;
  name: string;
  state: 'new' | 'gone' | 'changed';
  facets: Array<{ facet: string; added: string[]; removed: string[] }>;
  reason: 'needed' | 'given' | 'none';
  /** The unit's `Changed:` paragraphs, each with the lines it comes to; empty until `groupEdits` has run. */
  edits: UnitEdit[];
  /** The lines no edit names: all of them when the unit says no `Changed:`, a raised question always. */
  unclaimed: DeltaLine[];
}

/** A line that moved from a piece to another, unchanged: `from` and `to` are `#slug`s. */
export interface PlanMove {
  facet: string;
  text: string;
  from: string;
  to: string;
}

/** One line of a delta: `+` in the plan now and not approved, `−` approved and no longer in the plan. */
export interface DeltaLine {
  facet: string;
  sign: '+' | '−';
  text: string;
}

export interface UnitEdit {
  change: PlanChange;
  lines: DeltaLine[];
  /** Its claims that name no line of the delta. */
  unmatched: string[];
}

/** One thing the reviewer answers on the pages: an edit of a unit, or a question that stands in `plan.md` — a
 *  piece's `To confirm:`, or a waiver that opens with it. `key` is its unit, its words and its lines hashed: an
 *  answer stands for the item as it was read, and an item reworded since is to read again. */
export interface ReviewItem {
  key: string;
  unit: string;
  kind: 'edit' | 'question';
  what: string;
  why: string;
}

/** `specs/features/<feature>/plan-feedback.json`: the reviewer's answers, by item key, written from the pages by
 *  the local app and read by the agent (`npm run map -- feedback <feature>`). An approval empties it. */
export type PlanFeedback = Record<string, { unit: string; what: string; verdict: 'approved' | 'refused'; note: string; at: string }>;

/** FNV-1a, in hex: short, stable, with no dependency. */
function hash(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) h = Math.imul(h ^ text.charCodeAt(i), 0x01000193);
  return (h >>> 0).toString(16).padStart(8, '0');
}

/** The edits of one unit that is not as approved, in the order its section says them. A unit that says no
 *  `Changed:` holds nothing to answer yet — `--check` fails on it. */
export const editItems = (d: UnitDelta): ReviewItem[] => d.edits.map((e) => ({
  key: hash([d.name, e.change.text, ...e.lines.map((l) => `${l.sign} ${l.facet} ${l.text}`)].join('\n')),
  unit: d.name, kind: 'edit', what: e.change.what ?? e.change.why, why: e.change.what ? e.change.why : '',
}));

const questionItem = (unit: string, what: string): ReviewItem => ({ key: hash(`${unit}\nquestion\n${what}`), unit, kind: 'question', what, why: '' });

/** A piece's question, in one line: what it asks, then the alternative. */
export const askLine = (ask: NonNullable<PlanPieceDoc['ask']>) => `${ask.question}${ask.detail ? ` ${ask.detail}` : ''}`;

/** The question a piece asks, as an item to answer; null when it asks none. */
export const pieceQuestion = (piece: PlanPiece): ReviewItem | null => (piece.doc?.ask ? questionItem(`#${piece.slug}`, askLine(piece.doc.ask)) : null);

/** A waiver that is to confirm, as an item to answer. */
export const waiverQuestion = (waiver: PlanWaiver): ReviewItem => questionItem(`no test for ${waiver.rule}`, waiver.reason);

/** What the reviewer has to answer: each edit, in the order of the delta, then each question that stands in
 *  `plan.md`, a piece's then a waiver's. A question is one from the first draft on: it needs no approval to
 *  have moved from. */
export function reviewItems(plan: Pick<Plan, 'delta' | 'pieces' | 'doc'>): ReviewItem[] {
  return [
    ...(plan.delta ?? []).flatMap(editItems),
    ...plan.pieces.flatMap((piece) => pieceQuestion(piece) ?? []),
    ...(plan.doc?.waivers ?? []).filter((w) => w.toConfirm).map(waiverQuestion),
  ];
}

// ── The tag ────────────────────────────────────────────────────────────────────

const KEBAB = '[a-z0-9]+(?:-[a-z0-9]+)*';
const PLANNED_TAG = new RegExp(`^(${KEBAB})#(${KEBAB})$`);

/** `<feature>#<slug>` or a loud error naming where it was written. */
export function parseTag(tag: string, where: string): PlannedTag {
  const m = PLANNED_TAG.exec(tag);
  const parsed = m ? { feature: m[1], slug: m[2] } : null;
  if (parsed === null) throw new Error(`comprehension-plan: ${where} — "${tag}" is not <feature>#<slug>, two kebab-case names around one #`);
  return parsed;
}

const byPlace = (a: At, b: At) => a.file.localeCompare(b.file) || a.line - b.line || a.column - b.column;

// ── `@planned` comments ────────────────────────────────────────────────────────

type Marker = '//' | '--' | '#' | '<!--' | '/*' | '*';

/** The comment syntaxes a file has, by its extension; a file with no comment syntax (JSON) has no site. */
function markersOf(file: string): readonly Marker[] {
  const ext = /\.([a-z0-9]+)$/i.exec(file)?.[1]?.toLowerCase() ?? '';
  if (['ts', 'tsx', 'js', 'jsx', 'mjs', 'cjs', 'css', 'scss'].includes(ext)) return ['//', '/*', '*'];
  if (ext === 'sql') return ['--', '/*', '*'];
  if (['md', 'html', 'htm', 'svg', 'xml'].includes(ext)) return ['<!--'];
  if (['json', 'snap'].includes(ext)) return [];
  return ['#'];
}

/** A comment opener at the start of the line or after a space, then the word. In a docblock the opener is the
 *  line's leading `*`. A backtick or a quote before the opener (prose, a string) is no comment. */
const PLANNED_COMMENT = /(^|\s)(\/\/|--|#|<!--|\/\*+|\*)\s*@planned(\.remove)?\b(.*)$/;
const CLOSER: Partial<Record<Marker, string>> = { '<!--': '-->', '/*': '*/' };
/** Comment lines a tag's text may run over. */
const MAX_TEXT_LINES = 6;

/** What a comment site stands on: what the first line under it that is not a comment opens, as the stack's
 *  title reader has it. Two comments stacked on one test stand on that test, both of them. */
function standUnder(markers: readonly Marker[], lines: string[], from: number, stands: Stand[]): Stand | null {
  let k = from;
  while (k < lines.length && markers.some((m) => lines[k].trimStart().startsWith(m))) k += 1;
  return stands.find((s) => s.line === k + 1) ?? null;
}

/** Every `@planned <feature>#<slug> <text>` comment of one file, and every `@planned.remove` one. A malformed
 *  tag throws with the file and line. */
export function scanPlannedComments(file: string, text: string, titles: TitleReader): StaticSite[] {
  return plannedComments(file, text, titles).map((c) => c.site);
}

/** The comments of `scanPlannedComments`, each with what it stands on. */
function plannedComments(file: string, text: string, titles: TitleReader): Array<{ site: StaticSite; stand: Stand | null }> {
  if (!text.includes('@planned')) return [];
  const allowed = markersOf(file);
  const lines = text.split('\n');
  const read = titles.read(file, text);
  const out: Array<{ site: StaticSite; stand: Stand | null }> = [];
  lines.forEach((raw, i) => {
    const m = PLANNED_COMMENT.exec(raw);
    if (!m) return;
    const marker = (m[2].startsWith('/*') ? '/*' : m[2]) as Marker;
    if (!allowed.includes(marker)) return;
    // A `*` is a comment only as a docblock's leading star.
    if (marker === '*' && raw.slice(0, m.index + m[1].length).trim() !== '') return;
    const closer = CLOSER[marker];
    const cut = (s: string) => (closer && s.includes(closer) ? s.slice(0, s.indexOf(closer)) : s).trim();
    const rest = cut(m[4]);
    const token = /^\S*/.exec(rest)![0].replace(/[:.,;]+$/, '');
    const tag = parseTag(token, `${file}:${i + 1}`);
    const words = [rest.slice(/^\S*/.exec(rest)![0].length).replace(/^\s*[—–-]\s*/, '').trim()];
    // The comment lines that continue it: the same line comment, the rest of a block.
    const closedHere = closer !== undefined && m[4].includes(closer);
    if (!closedHere) {
      for (let k = i + 1; k < lines.length && k <= i + MAX_TEXT_LINES; k += 1) {
        const next = lines[k];
        if (next.includes('@planned')) break;
        if (closer) {
          words.push(cut(next).replace(/^\*\s?/, ''));
          if (next.includes(closer)) break;
        } else if (marker === '*') {
          const star = /^\s*\*(?!\/)\s?(.*)$/.exec(next);
          if (!star || star[1].trim() === '' || star[1].trimStart().startsWith('@')) break;
          words.push(star[1].trim());
        } else {
          const same = next.trimStart();
          if (!same.startsWith(marker)) break;
          words.push(same.slice(marker.length).trim());
        }
      }
    }
    const stand = standUnder(allowed, lines, i + 1, read.stands);
    out.push({ site: { ...tag, file, line: i + 1, column: raw.indexOf('@planned') + 1, text: words.filter(Boolean).join(' '), removes: m[3] !== undefined, on: stand?.label ?? null }, stand });
  });
  return out;
}

// ── Planned tests ──────────────────────────────────────────────────────────────

const TODO_TAG = new RegExp(`^(${KEBAB}#${KEBAB}):\\s*`);
/** A title that opens like a tag and is not one: `Feature#3:`, `a#b#c:`. */
const TODO_TAG_LIKE = /^(\S+#\S*):(\s|$)/;
const RULE_SUFFIX = new RegExp(`\\s*\\[(${KEBAB})\\]$`);

/** A todo's title taken apart: the tag, the title, the rule it claims. Null when the title carries no tag. */
export function parseTodoTitle(title: string, where: string): (PlannedTag & { title: string; rule: string | null }) | null {
  const m = TODO_TAG.exec(title);
  if (!m) {
    const like = TODO_TAG_LIKE.exec(title);
    if (like) parseTag(like[1], where);
    return null;
  }
  const rest = title.slice(m[0].length);
  const rule = RULE_SUFFIX.exec(rest);
  return { ...parseTag(m[1], where), title: rule ? rest.slice(0, rule.index) : rest, rule: rule ? rule[1] : null };
}

/** The tagged cases of one test file, without their tier: a test to write whose title is
 *  `<feature>#<slug>: …`, and a test written, its tag kept until the archive. A test to
 *  write whose title opens like a tag and is not one throws; a written test is only read when its title is
 *  exactly a tag — many titles of a repository open `name#part:` for other reasons, and the caller keeps those
 *  of real features. */
export function scanTodos(file: string, text: string, titles: TitleReader): Array<Omit<PlanTodo, 'tier'>> {
  if (!text.includes('#')) return [];
  const out: Array<Omit<PlanTodo, 'tier'>> = [];
  for (const t of titles.read(file, text).tests) {
    if (!t.planned && !TODO_TAG.test(t.title)) continue;
    const parsed = parseTodoTitle(t.title, `${file}:${t.line}`);
    if (parsed) out.push({ ...parsed, file, line: t.line, column: t.column, written: !t.planned });
  }
  return out;
}

/** The cases a feature will add to a journey, declared in one journey test and written by nobody yet. */
export function scanJourneyCases(file: string, text: string, titles: TitleReader): JourneyCase[] {
  return titles.read(file, text).journeyCases;
}

export function todosByTier(piece: PlanPiece): Record<Tier, PlanTodo[]> {
  return { narrative: piece.todos.filter((t) => t.tier === 'narrative'), server: piece.todos.filter((t) => t.tier === 'server'), unit: piece.todos.filter((t) => t.tier === 'unit') };
}

// ── The tests a commit added and deleted ───────────────────────────────────────

/** The titles of one test file's tests that run, in file order: a test to write is left out. */
export function scanTitles(file: string, text: string, titles: TitleReader): string[] {
  return titles.read(file, text).tests.filter((t) => !t.planned).map((t) => t.title);
}

/**
 * What one commit did to the tests of one file, read against the plan the file carried before it. `before` and
 * `after` are the file's text on each side of the commit, empty when it did not exist.
 *
 *  - `planned`: a test a `@planned` comment of the feature stood on, and that comment is gone — the test was
 *    deleted (`@planned.remove`) or changed as planned;
 *  - `deleted`: a title that is gone with no such comment on it. A title also goes when its test is extended
 *    and retitled to a planned one, which the plan says in a note on that title ("no case is added"): as many
 *    deletions as such titles were written are not counted;
 *  - `untagged`: a title that came in with no `<feature>#<piece>:` tag. A test a comment planned to change may
 *    be retitled: as many arrivals as such tests lost their title are not counted. A tagged title is the plan's:
 *    planned, it was a todo; not planned, it is a line of the piece's delta.
 *
 * `came` and `gone` are every title that arrived and left, with no judgement: which commit moved a title.
 */
export function testChanges(feature: string, file: string, before: string, after: string, titles: TitleReader): { untagged: string[]; deleted: string[]; planned: Array<{ title: string; removes: boolean; text: string }>; came: string[]; gone: string[] } {
  const was = scanTitles(file, before, titles);
  const now = scanTitles(file, after, titles);
  const gone = linesOver(was, now);
  const came = linesOver(now, was);
  const key = (c: StaticSite) => `${c.removes} ${c.slug} ${c.on} ${c.text}`;
  const still = scanPlannedComments(file, after, titles).filter((c) => c.feature === feature).map(key);
  const done = plannedComments(file, before, titles).filter((c) => c.site.feature === feature && !still.includes(key(c.site)));
  const onTest = done.flatMap(({ site, stand }) => {
    const title = stand?.test ?? null;
    return title !== null && was.includes(title) ? [{ title, removes: site.removes, text: site.text }] : [];
  });
  // A planned title an existing test was extended into, and that is written now.
  const extended = done.filter(({ site, stand }) => !site.removes && /\bno case is added\b/.test(site.text) && came.includes(stand?.test ?? '')).length;
  const retitled = onTest.filter((c) => !c.removes && gone.includes(c.title)).length;
  const deleted = linesOver(gone, onTest.map((c) => c.title));
  const untagged = came.filter((title) => !TODO_TAG.test(title));
  return { planned: onTest, deleted: deleted.length <= extended ? [] : deleted, untagged: untagged.length <= retitled ? [] : untagged, came, gone };
}

// ── `plan.md` and the rules of `spec.md` ───────────────────────────────────────

const SLUG_REF = new RegExp(`(^|[\\s(\`])#(${KEBAB})(?![a-z0-9-])`, 'g');

/** The `#slug`s a text names, in order, each once. */
export function slugRefs(text: string): string[] {
  return [...new Set([...text.matchAll(SLUG_REF)].map((m) => m[2]))];
}

/** A text's `#slug`s replaced through `link`, the rest left as it is. */
export function replaceSlugRefs(text: string, link: (slug: string) => string): string {
  return text.replace(SLUG_REF, (_m, before: string, slug: string) => `${before}${link(slug)}`);
}

const ASK = /^To confirm:\s*/;
const CHANGED = /^Changed:\s*/;
const NOTE = /^Note:\s*/;

/** The facet of a piece that holds its notes. */
export const NOTES = 'notes';
/** The facets whose lines are their own notice: listed, drawn as what they are, named by no edit. */
export const isOwnNotice = (facet: string) => facet === 'question' || facet === NOTES;

/** A clause names a function when it holds it in backticks, alone or opening a call. */
export const names = (sentence: string, fn: string) => sentence.includes(`\`${fn}\``) || sentence.includes(`\`${fn}(`);

const anchorOf = (title: string) => `decision-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`;

const PIECE_TITLE = new RegExp(`^#(${KEBAB})$`);

export const WAIVERS_SECTION = 'Rules no test holds';

/** The items of "## Rules no test holds": a list and nothing else, each item opening with the rule's slug. */
function waiversOf(section: MdSection | undefined, file: string): PlanWaiver[] {
  if (!section) return [];
  const stray = section.blocks.find((b) => b.kind === 'p');
  if (stray) throw new Error(`comprehension-plan: ${file}:${stray.line} — "## ${WAIVERS_SECTION}" holds a list and nothing else: "- **the-rule** why no test holds it"`);
  const items = section.blocks.flatMap((b) => (b.kind === 'ul' ? b.items : []));
  const bare = items.find((i) => i.slug === null || i.text.replace(ASK, '').trim() === '');
  if (bare) throw new Error(`comprehension-plan: ${file}:${bare.line} — a waiver names its rule in bold, then says why no test holds it: "- **the-rule** the reason"`);
  const twice = items.find((r, i) => items.findIndex((o) => o.slug === r.slug) !== i);
  if (twice) throw new Error(`comprehension-plan: ${file}:${twice.line} — two waivers name [${twice.slug}]`);
  return items.map((i) => ({ rule: i.slug!, reason: i.text.replace(ASK, ''), toConfirm: ASK.test(i.text), line: i.line }));
}

export const DELIVERY_SECTION = 'Delivery';

const LOT_DIFFICULTY = /^\((easy|standard|hard)\)\s*/;
const LOT_MEMBER = new RegExp(`^([#@])(${KEBAB})(?![a-z0-9-])[\\s,]*`);

/** The items of "## Delivery": a list and nothing else. An item opens with the lot's slug in bold, then its
 *  difficulty when it is not `standard`, then its pieces and screens, then the reason. A `#slug` in the reason
 *  is a mention, not a member. */
function lotsOf(section: MdSection | undefined, file: string): PlanLot[] {
  if (!section) return [];
  const form = '"- **the-lot** (hard) #piece #piece @screen — why these together, and why here"';
  const stray = section.blocks.find((b) => b.kind === 'p');
  if (stray) throw new Error(`comprehension-plan: ${file}:${stray.line} — "## ${DELIVERY_SECTION}" holds a list and nothing else: ${form}`);
  const lots = section.blocks.flatMap((b) => (b.kind === 'ul' ? b.items : [])).map((item): PlanLot => {
    if (item.slug === null) throw new Error(`comprehension-plan: ${file}:${item.line} — a lot opens with its bold kebab-case slug: ${form}`);
    let rest = item.text;
    const difficulty = (LOT_DIFFICULTY.exec(rest)?.[1] ?? 'standard') as Difficulty;
    rest = rest.replace(LOT_DIFFICULTY, '');
    const pieces: string[] = [];
    const screens: string[] = [];
    for (let m = LOT_MEMBER.exec(rest); m; m = LOT_MEMBER.exec(rest)) {
      (m[1] === '#' ? pieces : screens).push(m[2]);
      rest = rest.slice(m[0].length);
    }
    const reason = rest.replace(/^[—–:-]\s*/, '').trim();
    if (pieces.length + screens.length === 0 || reason === '') throw new Error(`comprehension-plan: ${file}:${item.line} — lot "${item.slug}" names what it delivers, then says why: ${form}`);
    return { slug: item.slug, difficulty, pieces, screens, reason, line: item.line };
  });
  const twice = lots.find((l, i) => lots.findIndex((o) => o.slug === l.slug) !== i);
  if (twice) throw new Error(`comprehension-plan: ${file}:${twice.line} — two lots are named "${twice.slug}"`);
  return lots;
}

export const ELSEWHERE_SECTION = 'Planned elsewhere';

const POINTER = new RegExp(`^#(${KEBAB})(?![a-z0-9-])\\s*[—–:-]\\s*`);

/** The items of "## Planned elsewhere": a list and nothing else. An item opens with the repository in bold,
 *  then the piece's tag, then what this plan relies on. */
function pointersOf(section: MdSection | undefined, file: string): PlanPointer[] {
  if (!section) return [];
  const form = '"- **the-repository** #the-piece — what this plan relies on, and which pieces here stand on it"';
  const stray = section.blocks.find((b) => b.kind === 'p');
  if (stray) throw new Error(`comprehension-plan: ${file}:${stray.line} — "## ${ELSEWHERE_SECTION}" holds a list and nothing else: ${form}`);
  const pointers = section.blocks.flatMap((b) => (b.kind === 'ul' ? b.items : [])).map((item): PlanPointer => {
    const named = POINTER.exec(item.text);
    const reason = named ? item.text.slice(named[0].length).trim() : '';
    if (item.slug === null || !named || reason === '') throw new Error(`comprehension-plan: ${file}:${item.line} — a piece planned elsewhere names its repository in bold, then its tag, then says what this plan relies on: ${form}`);
    return { repository: item.slug, slug: named[1], reason, line: item.line };
  });
  const twice = pointers.find((p, i) => pointers.findIndex((o) => o.slug === p.slug) !== i);
  if (twice) throw new Error(`comprehension-plan: ${file}:${twice.line} — two pieces planned elsewhere are tagged #${twice.slug}`);
  return pointers;
}

const RESERVED_SECTIONS = [WAIVERS_SECTION, DELIVERY_SECTION, ELSEWHERE_SECTION];

export function planDocOf(intent: Intent, file: string): PlanDoc {
  const waivers = waiversOf(intent.sections.find((s) => s.title === WAIVERS_SECTION), file);
  const lots = lotsOf(intent.sections.find((s) => s.title === DELIVERY_SECTION), file);
  const pointers = pointersOf(intent.sections.find((s) => s.title === ELSEWHERE_SECTION), file);
  const sections = intent.sections.filter((s) => !RESERVED_SECTIONS.includes(s.title)).map((s) => {
    const texts = s.blocks.flatMap((b) => (b.kind === 'p' ? [b.text] : b.items.map((i) => i.text)));
    const piece = PIECE_TITLE.exec(s.title)?.[1] ?? null;
    if (piece === null && s.title.startsWith('#')) throw new Error(`comprehension-plan: ${file}:${s.line} — "## ${s.title}": a piece's section is titled with its tag alone, "## #the-slug"`);
    const changed = s.blocks.flatMap((b) => {
      if (b.kind !== 'p' || !CHANGED.test(b.text)) return [];
      const whole = b.text.replace(CHANGED, '');
      const arrow = whole.lastIndexOf(' → ');
      const text = arrow < 0 ? whole : whole.slice(0, arrow);
      const claims = arrow < 0 ? [] : whole.slice(arrow + 3).split(';').map((c) => c.trim()).filter(Boolean).map((c) => {
        const m = new RegExp(`^(${CLAIM_KINDS.join('|')})\\s+(?:"([^"]+)"|(\\S+))$`).exec(c);
        if (!m) throw new Error(`comprehension-plan: ${file}:${b.line} — "${c}" is no claim: after " → ", a kind (${CLAIM_KINDS.join(', ')}) and a fragment of the line, in double quotes when it holds a space, claims parted by ";"`);
        return { kind: m[1], fragment: m[2] ?? m[3] };
      });
      const bold = /^\*\*(.+?)\*\*\s*/.exec(text);
      return [{ what: bold ? bold[1].replace(/\.$/, '') : null, why: bold ? text.slice(bold[0].length) : text, text, claims, line: b.line }];
    });
    return { ...s, anchor: piece === null ? anchorOf(s.title) : `piece-${piece}`, piece, slugs: slugRefs(texts.join('\n')), changed };
  });
  const twice = sections.find((s, i) => sections.findIndex((o) => o.anchor === s.anchor) !== i);
  if (twice) throw new Error(`comprehension-plan: ${file}:${twice.line} — two sections are titled "${twice.title}"`);
  return { file, title: intent.title, lead: intent.lead, sections, waivers, lots, pointers };
}

/** A piece's section taken apart. It opens with a paragraph, the statement; at most one paragraph opens
 *  `To confirm:`. A paragraph opening `Changed:` is the section's (`PlanSection.changed`), not the reason's. */
export function pieceDocOf(section: PlanSection, file: string): PlanPieceDoc {
  const [first, ...rest] = section.blocks;
  if (!first || first.kind !== 'p' || ASK.test(first.text) || CHANGED.test(first.text) || NOTE.test(first.text)) throw new Error(`comprehension-plan: ${file}:${section.line} — "## ${section.title}" opens with its statement, one paragraph saying what the piece changes`);
  const asks = rest.filter((b): b is Extract<MdBlock, { kind: 'p' }> => b.kind === 'p' && ASK.test(b.text));
  if (asks.length > 1) throw new Error(`comprehension-plan: ${file}:${asks[1].line} — "## ${section.title}" holds ${asks.length} "To confirm:" paragraphs, and a piece asks one thing`);
  let ask: PlanPieceDoc['ask'] = null;
  if (asks[0]) {
    const text = asks[0].text.replace(ASK, '');
    const bold = /^\*\*(.+?)\*\*\s*/.exec(text);
    ask = { question: bold ? bold[1] : text, detail: bold ? text.slice(bold[0].length) : '', line: asks[0].line };
  }
  const notes = rest.flatMap((b): PlanNote[] => {
    if (b.kind !== 'p' || !NOTE.test(b.text)) return [];
    const text = b.text.replace(NOTE, '');
    const bold = /^\*\*(.+?)\*\*\s*/.exec(text);
    return [{ what: bold ? bold[1].replace(/\.$/, '') : null, detail: bold ? text.slice(bold[0].length) : text, text, line: b.line }];
  });
  return { section, what: first.text, why: rest.filter((b) => b !== asks[0] && !(b.kind === 'p' && (CHANGED.test(b.text) || NOTE.test(b.text)))), ask, notes };
}

export const RULES_SECTION = 'Rules no screen shows';

/** The rules of a `spec.md`: every item of its "Rules no screen shows" section, each opening with its slug. */
export function rulesOf(intent: Intent, file: string): Array<Omit<PlanRule, 'owners' | 'waiver'>> {
  const section = intent.sections.find((s) => s.title === RULES_SECTION);
  if (!section) return [];
  for (const b of section.blocks) {
    if (b.kind !== 'ul') continue;
    const bare = b.items.find((i) => i.slug === null);
    if (bare) throw new Error(`comprehension-plan: ${file}:${bare.line} — a rule of "${RULES_SECTION}" opens with its bold kebab-case slug: "- **the-slug** ${bare.text.slice(0, 30)}…"`);
  }
  const rules = sluggedItems(intent, RULES_SECTION).map((i) => ({ slug: i.slug!, text: i.text, line: i.line }));
  const twice = rules.find((r, i) => rules.findIndex((o) => o.slug === r.slug) !== i);
  if (twice) throw new Error(`comprehension-plan: ${file}:${twice.line} — two rules are named "${twice.slug}"`);
  return rules;
}

// ── The snapshot and the delta ─────────────────────────────────────────────────

/** A site, a comment and a test as a line of the snapshot: what the approval holds of each. */
export const siteLineOf = (x: PlanSite) => `${x.change} ${x.file} in ${x.fn} — ${x.sentence}`;
export const commentLineOf = (x: StaticSite) => `${x.removes ? 'removes' : 'changes'} ${x.file} — ${x.text}`;
export const testLineOf = (t: PlanTodo) => `${t.tier} ${t.file} — ${t.title}${t.rule ? ` [${t.rule}]` : ''}`;
const caseLineOf = (c: JourneyCase) => `${c.journey} · ${c.screen} — ${c.title}`;

const blockTexts = (blocks: MdBlock[]) => blocks.flatMap((b) => (b.kind === 'p' ? [b.text] : b.items.map((i) => `- ${i.slug ? `**${i.slug}** ` : ''}${i.text}`)));

/** The plan as lines. A piece is its statement, its reason, its sites and its comments — those still planned,
 *  then those that are code (`PlanPiece.built`) — and its tests, written or not; a piece whose every site was
 *  implemented and that has no tagged test is still its section. A decision is its text, `Changed:` paragraphs
 *  left out. A story is the steps of a narrative the plan lands in. */
export function snapshotOf(plan: Pick<Plan, 'pieces' | 'doc' | 'journeyCases'> & Partial<Pick<Plan, 'builtCases'>>, stories: Array<{ title: string; steps: string[] }>): PlanSnapshot {
  const units: SnapshotUnit[] = plan.pieces.map((piece) => ({
    kind: 'piece',
    name: `#${piece.slug}`,
    facets: {
      statement: piece.doc ? [piece.doc.what] : [],
      reason: piece.doc ? blockTexts(piece.doc.why) : [],
      sites: [...piece.sites.map(siteLineOf), ...piece.built.sites],
      comments: [...piece.statics.map(commentLineOf), ...piece.built.comments],
      tests: piece.todos.map(testLineOf),
      // An approved plan holds none: a question a later stage raises is a line of the delta.
      question: piece.doc?.ask ? [askLine(piece.doc.ask)] : [],
      // What it was built with, told for whoever builds on it: listed when new, and asks nothing.
      [NOTES]: (piece.doc?.notes ?? []).map((n) => n.text),
    },
  }));
  const doc = plan.doc;
  if (doc) {
    for (const section of doc.sections) {
      if (section.piece !== null) {
        if (plan.pieces.some((x) => x.slug === section.piece)) continue;
        const own = pieceDocOf(section, doc.file);
        units.push({ kind: 'piece', name: `#${section.piece}`, facets: { statement: [own.what], reason: blockTexts(own.why), sites: [], comments: [], tests: [] } });
      } else units.push({ kind: 'decision', name: section.title, facets: { text: blockTexts(section.blocks.filter((b) => !(b.kind === 'p' && CHANGED.test(b.text)))) } });
    }
    if (doc.waivers.length) units.push({ kind: 'waivers', name: WAIVERS_SECTION, facets: { waivers: doc.waivers.map((w) => `${w.rule} — ${w.toConfirm ? 'To confirm: ' : ''}${w.reason}`) } });
    // A pointer carries its reason, as a waiver and a lot do: one that moves is listed, and asks nothing more.
    if (doc.pointers.length) units.push({ kind: 'elsewhere', name: ELSEWHERE_SECTION, facets: { pointers: doc.pointers.map((p) => `${p.repository} #${p.slug} — ${p.reason}`) } });
    if (doc.lots.length) units.push({ kind: 'delivery', name: DELIVERY_SECTION, facets: { lots: doc.lots.map((l) => `${l.slug}${l.difficulty === 'standard' ? '' : ` (${l.difficulty})`} ${[...l.pieces.map((x) => `#${x}`), ...l.screens.map((x) => `@${x}`)].join(' ')} — ${l.reason}`) } });
  }
  const cases = [...plan.journeyCases.map(caseLineOf), ...(plan.builtCases ?? [])];
  if (cases.length) units.push({ kind: 'journey', name: 'Journey cases', facets: { cases } });
  for (const story of stories) units.push({ kind: 'story', name: story.title, facets: { steps: story.steps } });
  return { units };
}

/** The facets of a piece whose lost line is a change of the plan. A site or a comment that went was
 *  implemented, or dropped: the delta lists it and asks nothing. */
const LOSS_IS_A_CHANGE = ['statement', 'reason', 'tests'];
/** A question is its own notice: it is listed, and answered, and asks for no `Changed:` beside it. So is a
 *  note: it is listed, and read. */
const ASKS_NOTHING = ['question', NOTES];

/** A line of the unit tier: a unit title to write, or a comment on a test file that is neither a narrative's nor
 *  a journey's. It touches neither the product's code nor what a narrative tells. */
export const isUnitTestLine = (facet: string, line: string, layout: Layout) => (facet === 'tests' ? line.startsWith('unit ') : facet === 'comments' && layout.isUnitTest(/^\S+ (\S*)/.exec(line)?.[1] ?? ''));

/** The lines of `now` that `was` does not hold, each as many times as it is over. */
const linesOver = (now: string[], was: string[]) => {
  const left = [...was];
  return now.filter((line) => {
    const at = left.indexOf(line);
    if (at >= 0) left.splice(at, 1);
    return at < 0;
  });
};

/**
 * What differs from the approved plan, a unit at a time, in the order of the plan as it stands, then what is
 * gone. A reason is needed for a piece that gained a line of any facet or lost one of its statement, its reason
 * or its tests, and for a decision that is new or reads differently. The waivers, the lots, the journey cases
 * and the stories are listed and ask nothing: a waiver and a lot carry their reason, a story moves because the
 * plan is being implemented. A `To confirm:` a later stage adds is listed too, and is its own notice. While no
 * delivery is approved, the delivery and the unit tier (`isUnitTestLine`) are the tasks stage's output: they are
 * read on the delivery page, lot by lot, and are no line of the delta. A line one piece lost and another gained,
 * word for word, is a move: it leaves both deltas and is returned apart, of second order. `explained` says whether the unit's section holds a `Changed:`.
 */
export function diffSnapshots(approved: PlanSnapshot, now: PlanSnapshot, explained: (kind: UnitKind, name: string) => boolean, layout: Layout): { delta: UnitDelta[]; moves: PlanMove[] } {
  const key = (u: SnapshotUnit) => `${u.kind} ${u.name}`;
  const was = new Map(approved.units.map((u) => [key(u), u]));
  // Until a delivery is approved, what the tasks stage writes is its output and no change of the plan: the
  // delivery itself, the unit titles, the comments on unit tests. Once one is approved, a test nobody planned is
  // a change like another.
  const tasksOpen = !approved.units.some((u) => u.kind === 'delivery');
  const still = new Set(now.units.map(key));
  const raw = [
    ...now.units.map((u) => ({ kind: u.kind, name: u.name, state: (was.has(key(u)) ? 'changed' : 'new') as UnitDelta['state'], before: was.get(key(u)), after: u as SnapshotUnit | undefined })),
    ...approved.units.filter((u) => !still.has(key(u))).map((u) => ({ kind: u.kind, name: u.name, state: 'gone' as UnitDelta['state'], before: u as SnapshotUnit | undefined, after: undefined as SnapshotUnit | undefined })),
  ].filter((u) => !(tasksOpen && u.kind === 'delivery')).map((u) => ({
    ...u,
    facets: [...new Set([...Object.keys(u.after?.facets ?? {}), ...Object.keys(u.before?.facets ?? {})])]
      .map((facet) => ({ facet, added: linesOver(u.after?.facets[facet] ?? [], u.before?.facets[facet] ?? []), removed: linesOver(u.before?.facets[facet] ?? [], u.after?.facets[facet] ?? []) })),
  }));
  // A line one piece lost and another gained, word for word, moved: the same thing is planned, by another piece.
  const moves: PlanMove[] = [];
  const pieces = raw.filter((u) => u.kind === 'piece');
  for (const from of pieces) {
    for (const lost of from.facets) {
      for (const text of [...lost.removed]) {
        const to = pieces.find((u) => u !== from && u.facets.some((f) => f.facet === lost.facet && f.added.includes(text)));
        if (!to) continue;
        const gained = to.facets.find((f) => f.facet === lost.facet)!;
        lost.removed.splice(lost.removed.indexOf(text), 1);
        gained.added.splice(gained.added.indexOf(text), 1);
        moves.push({ facet: lost.facet, text, from: from.name, to: to.name });
      }
    }
  }
  const delta: UnitDelta[] = [];
  for (const u of raw) {
    const facets = u.facets
      .map((f) => ({ ...f, added: f.added.filter((line) => !(tasksOpen && isUnitTestLine(f.facet, line, layout))) }))
      .filter((f) => f.added.length + f.removed.length > 0);
    if (facets.length === 0 && u.state === 'changed') continue;
    const asks = u.state !== 'gone' && (u.kind === 'decision' || (u.kind === 'piece' && facets.some((f) => !ASKS_NOTHING.includes(f.facet) && (f.added.length > 0 || (f.removed.length > 0 && LOSS_IS_A_CHANGE.includes(f.facet))))));
    delta.push({ kind: u.kind, name: u.name, state: u.state, facets, reason: explained(u.kind, u.name) ? 'given' : asks ? 'needed' : 'none', edits: [], unclaimed: facets.flatMap(linesOf) });
  }
  return { delta, moves };
}

const linesOf = (f: UnitDelta['facets'][number]): DeltaLine[] => [...f.removed.map((text) => ({ facet: f.facet, sign: '−' as const, text })), ...f.added.map((text) => ({ facet: f.facet, sign: '+' as const, text }))];

/** Where a line of the delta stands: the function of a site, the file of a comment or of a test, else its facet.
 *  One line out and one line in at the same place are one rewording. */
export function placeOfLine(line: DeltaLine): string {
  // What a commit did beyond the plan is no rewording of anything: each line is its own place.
  if (line.facet === UNPLANNED) return `${UNPLANNED} ${line.text}`;
  const site = /^(?:changed|added|removed) (\S+) in (\S+) — /.exec(line.facet === 'sites' ? line.text : '');
  if (site) return `sites ${site[1]} ${site[2]}`;
  const filed = /^\S+ (\S+) — /.exec(line.facet === 'comments' || line.facet === 'tests' ? line.text : '');
  return filed ? `${line.facet} ${filed[1]}` : line.facet;
}

/** The kind a claim names a line by. */
export function kindOfLine(line: DeltaLine): string {
  if (line.facet === 'sites') return 'code';
  if (line.facet === 'tests') return 'test';
  if (line.facet === 'comments') return /^\S+ tests\//.test(line.text) ? 'test' : 'code';
  if (line.facet === UNPLANNED) return line.text.startsWith('test ') ? 'test' : 'code';
  return line.facet;
}

// ── What a lot's commits did beyond the plan ───────────────────────────────────

/** The facet of a piece's delta that holds what its commits did and the plan did not say. Its lines are read
 *  from git, never from the plan: no snapshot holds them, and an approval covers the commits made before it. */
export const UNPLANNED = 'unplanned';


/** The files a snapshot's pieces name: where a site, a comment or a test stands. */
export function filesNamed(snapshot: PlanSnapshot): Set<string> {
  const out = new Set<string>();
  for (const u of snapshot.units) {
    if (u.kind !== 'piece') continue;
    for (const line of u.facets.sites ?? []) out.add(/^\S+ (\S+) in /.exec(line)?.[1] ?? '');
    for (const line of [...(u.facets.comments ?? []), ...(u.facets.tests ?? [])]) out.add(/^\S+ (\S+) — /.exec(line)?.[1] ?? '');
  }
  out.delete('');
  return out;
}

/**
 * What the commits made since the approval did beyond the plan, or did not do, as lines by piece:
 *
 *  - a test deleted with nothing planned on it, and a file of the product's code that no place of the plan
 *    names (`named`: the approved plan's and the plan's as it stands) — under the first piece the commit names;
 *  - a place the approval held and the code no longer holds, in a file the piece's commits touched and added
 *    no line to: its planned line was taken off and nothing was written. The approval holds the clause, git
 *    what was written: neither alone tells a place built from a place dropped. A removal is not read this way
 *    (it adds nothing by design), nor a proposed migration, which moves to another folder.
 *
 * Each is a line of the piece's delta, so the piece's section says why in a `Changed:` and the reviewer answers
 * it like any other edit. A test file a commit only edits is no line: a literal that gains a field changes no
 * test. A file that holds several places, one built and one skipped, is not caught: the file gained lines.
 */
export function unplannedLines(commits: PieceCommit[], named: ReadonlySet<string>, layout: Layout, pieces: PlanPiece[] = []): Map<string, string[]> {
  const out = new Map<string, string[]>();
  const add = (slug: string, line: string) => {
    const lines = out.get(slug) ?? [];
    if (!lines.includes(line)) out.set(slug, [...lines, line]);
  };
  for (const c of commits) {
    if (!c.sinceApproval || c.pieces.length === 0) continue;
    for (const d of c.deleted) add(c.pieces[0], `test ${d.file} — deleted, and the plan removed no such test: ${d.title}`);
    for (const f of c.files) if (layout.isProduct(f.file) && !named.has(f.file)) add(c.pieces[0], `file ${f.file} — ${f.line === null ? 'deleted' : 'changed'}, and no place of the plan names it`);
  }
  for (const piece of pieces) {
    const since = piece.commits.filter((c) => c.sinceApproval);
    const addedTo = (file: string) => piece.commits.reduce((n, c) => n + (c.files.find((f) => f.file === file)?.added ?? 0), 0);
    for (const line of [...piece.built.sites, ...piece.built.comments]) {
      const m = /^(changed|added|changes) (\S+) (?:in \S+ )?— (.*)$/.exec(line);
      if (!m || (m[2].startsWith('specs/features/') && m[2].endsWith('.sql'))) continue;
      if (since.some((c) => c.files.some((f) => f.file === m[2])) && addedTo(m[2]) === 0) add(piece.slug, `place ${m[2]} — planned there, and the piece's commits added no line to the file: ${m[3]}`);
    }
  }
  return out;
}

/**
 * Gives each `Changed:` paragraph of a unit the lines it comes to, so the reviewer reads an edit, its reason
 * and its lines together. One paragraph: every line is its. Several: a line goes to the first paragraph a claim
 * of which has its kind and a fragment it holds — its text, or the title of the test a comment stands on — and
 * the other half of a rewording follows it. A raised question is no edit's.
 */
export function groupEdits(delta: UnitDelta, changes: PlanChange[], piece: PlanPiece | undefined): void {
  const lines = delta.facets.flatMap(linesOf);
  const claimable = lines.filter((l) => !isOwnNotice(l.facet));
  const holds = (l: DeltaLine) => `${l.text}${l.facet === 'comments' && l.sign === '+' ? ` ${(piece?.statics ?? []).filter((x) => `${x.removes ? 'removes' : 'changes'} ${x.file} — ${x.text}` === l.text).map((x) => x.on ?? '').join(' ')}` : ''}`;
  const owner = new Map<DeltaLine, PlanChange>();
  if (changes.length === 1) for (const l of claimable) owner.set(l, changes[0]);
  else {
    for (const l of claimable) {
      const by = changes.find((c) => c.claims.some((claim) => claim.kind === kindOfLine(l) && holds(l).includes(claim.fragment)));
      if (by) owner.set(l, by);
    }
    for (const l of claimable) {
      if (owner.has(l)) continue;
      const here = claimable.filter((o) => placeOfLine(o) === placeOfLine(l));
      const other = here.find((o) => o !== l);
      if (here.length === 2 && other && other.sign !== l.sign && owner.has(other)) owner.set(l, owner.get(other)!);
    }
  }
  delta.edits = changes.map((change) => ({
    change,
    lines: lines.filter((l) => owner.get(l) === change),
    unmatched: changes.length === 1 ? [] : change.claims.filter((claim) => !claimable.some((l) => claim.kind === kindOfLine(l) && holds(l).includes(claim.fragment))).map((claim) => `${claim.kind} "${claim.fragment}"`),
  }));
  delta.unclaimed = lines.filter((l) => !owner.has(l));
}

/** The sites whose clause names a shell's function: where the new code will be called from. */
export function callersOf(plan: Pick<Plan, 'pieces'>, shell: PlanSite): PlanSite[] {
  return plan.pieces.flatMap((piece) => piece.sites).filter((x) => x !== shell && names(x.sentence, shell.fn));
}

/** What a lot still owes: its pieces' open sites and tests, and the journey cases of its screens. All zero, it
 *  is delivered — nobody writes that down. */
export function lotLeft(plan: Pick<Plan, 'pieces' | 'journeyCases'>, lot: PlanLot): { sites: number; tests: number; cases: number } {
  const pieces = plan.pieces.filter((x) => lot.pieces.includes(x.slug));
  return {
    sites: pieces.reduce((n, x) => n + x.sites.length + x.statics.length, 0),
    tests: pieces.reduce((n, x) => n + x.todos.filter((t) => !t.written).length, 0),
    cases: plan.journeyCases.filter((c) => lot.screens.includes(c.screen)).length,
  };
}

// ── Assembly ───────────────────────────────────────────────────────────────────

/** What a feature folder holds beside its sites. */
export interface FeatureDocs {
  folderExists: boolean;
  /** `plan.md`, parsed. */
  plan: { file: string; intent: Intent } | null;
  /** `spec.md`, parsed. */
  spec: { file: string; intent: Intent } | null;
  /** `plan.approved.json`, when the plan was approved. */
  approved?: { file: string; baseline: PlanBaseline } | null;
  /** `plan-feedback.json`, when the reviewer has answered from the pages. */
  feedback?: PlanFeedback | null;
  /** The commits whose message names a piece of the feature, oldest first, and whether the commit of the
   *  approval is in this branch's history. */
  commits?: { list: PieceCommit[]; baseKnown: boolean } | null;
  /** What a repository says of a piece of this feature it plans; null when no checkout of it is known. */
  pointed?: (repository: string, slug: string) => PointerTarget | null;
}

export interface PlanInput {
  sites: PlanSite[];
  statics: StaticSite[];
  todos: PlanTodo[];
  /** The journey tests' `todo` cases, of every feature. A feature these alone name has a spec and no plan yet. */
  journeyCases?: JourneyCase[];
  /** Every narrative with a canonical story, in any order. `steps` is its story as lines, a step each
   *  (`<function> — <sentence>`): what a plan landing in it is approved against. */
  narratives: Array<{ title: string; kind: NarrativeKind; steps?: string[] }>;
  docs(feature: string): FeatureDocs;
  /** What the project's configuration says of a file: product code, a unit test. */
  layout: Layout;
}

/** One plan per feature any site names, the pieces in the order they are told. */
export function assemblePlans(input: PlanInput): Plan[] {
  const features = [...new Set([...input.sites, ...input.statics, ...input.todos].map((s) => s.feature))].sort();
  // Product narratives first: a piece is told where the learner's action crosses it, and under a mechanism only
  // when no product story does.
  const narratives = [...input.narratives].sort((a, b) => (a.kind === b.kind ? a.title.localeCompare(b.title) : a.kind === 'product' ? -1 : 1));
  return features.map((feature) => {
    const docs = input.docs(feature);
    const doc = docs.plan ? planDocOf(docs.plan.intent, docs.plan.file) : null;
    const bySlug = new Map<string, PlanPiece>();
    const pieceOf = (slug: string): PlanPiece => {
      let piece = bySlug.get(slug);
      if (!piece) {
        const own = doc?.sections.find((s) => s.piece === slug) ?? null;
        piece = {
          slug, sites: [], statics: [], todos: [], sql: [],
          doc: own ? pieceDocOf(own, doc!.file) : null,
          decidedIn: doc ? doc.sections.filter((s) => s.piece === null && s.slugs.includes(slug)) : [],
          built: { sites: [], comments: [] },
          commits: [],
        };
        bySlug.set(slug, piece);
      }
      return piece;
    };
    for (const s of input.sites.filter((x) => x.feature === feature).sort(byPlace)) pieceOf(s.slug).sites.push(s);
    for (const s of input.statics.filter((x) => x.feature === feature).sort(byPlace)) {
      const piece = pieceOf(s.slug);
      piece.statics.push(s);
      if (s.file.startsWith(`specs/features/${feature}/`) && s.file.endsWith('.sql') && !piece.sql.includes(s.file)) piece.sql.push(s.file);
    }
    for (const t of input.todos.filter((x) => x.feature === feature).sort(byPlace)) pieceOf(t.slug).todos.push(t);

    // Once a delivery is approved the plan is being implemented: a site or a comment the approval held and that
    // is gone became code, and the piece keeps its line as built — unless its place still holds a planned line
    // (it was reworded) or another piece now holds the line (it moved). A piece all built is still a piece.
    const approved = docs.approved ?? null;
    const approvedPieces = (approved?.baseline.units ?? []).filter((u) => u.kind === 'piece');
    const implementing = approved !== null && approved.baseline.units.some((u) => u.kind === 'delivery');
    if (implementing) {
      const heldBy = new Map<string, string>();
      for (const piece of bySlug.values()) for (const line of [...piece.sites.map(siteLineOf), ...piece.statics.map(commentLineOf)]) heldBy.set(line, piece.slug);
      for (const unit of approvedPieces) {
        const piece = pieceOf(unit.name.slice(1));
        const went = (facet: 'sites' | 'comments', held: string[]) => {
          const places = new Set(held.map((text) => placeOfLine({ facet, sign: '+', text })));
          return linesOver(unit.facets[facet] ?? [], held).filter((text) => !places.has(placeOfLine({ facet, sign: '−', text })) && (heldBy.get(text) ?? piece.slug) === piece.slug);
        };
        piece.built = { sites: went('sites', piece.sites.map(siteLineOf)), comments: went('comments', piece.statics.map(commentLineOf)) };
      }
    }
    const commits = docs.commits?.list ?? [];
    for (const c of commits) for (const slug of c.pieces) bySlug.get(slug)?.commits.push(c);

    const left = new Set(bySlug.values());
    const groups: PlanGroup[] = [];
    for (const n of narratives) {
      const first = (piece: PlanPiece) => Math.min(...piece.sites.flatMap((s) => s.crossedBy.filter((c) => c.narrative === n.title).map((c) => c.at)));
      const pieces = [...left].filter((piece) => Number.isFinite(first(piece))).sort((a, b) => first(a) - first(b));
      if (pieces.length === 0) continue;
      for (const s of pieces) left.delete(s);
      groups.push({ kind: 'narrative', narrative: n.title, pieces });
    }
    // A piece all built has no place left: it is told last, by its name.
    const place = (piece: PlanPiece): At | undefined => piece.sites[0] ?? [...piece.statics, ...piece.todos].sort(byPlace)[0];
    const inFileOrder = (pieces: PlanPiece[]) => pieces.sort((a, b) => {
      const [x, y] = [place(a), place(b)];
      return x && y ? byPlace(x, y) : x ? -1 : y ? 1 : a.slug.localeCompare(b.slug);
    });
    const uncrossed = inFileOrder([...left].filter((s) => s.sites.length > 0));
    const statics = inFileOrder([...left].filter((s) => s.sites.length === 0));
    if (uncrossed.length) groups.push({ kind: 'uncrossed', narrative: null, pieces: uncrossed });
    if (statics.length) groups.push({ kind: 'static', narrative: null, pieces: statics });

    const todos = [...bySlug.values()].flatMap((s) => s.todos).sort(byPlace);
    const waivers = doc?.waivers ?? [];
    const rules = docs.spec ? rulesOf(docs.spec.intent, docs.spec.file).map((r) => ({ ...r, owners: todos.filter((t) => t.rule === r.slug), waiver: waivers.find((w) => w.rule === r.slug) ?? null })) : [];
    const pieces = groups.flatMap((g) => g.pieces);
    const journeyCases = (input.journeyCases ?? []).filter((c) => c.feature === feature).sort(byPlace);
    // A piece the approved plan holds is still one once its last site is implemented: its section and its lot
    // go on naming it.
    const approvedSlugs = new Set(approvedPieces.map((u) => u.name.slice(1)));
    // A journey case the approval held and that is no `todo` any more was written.
    const openCases = journeyCases.map(caseLineOf);
    const builtCases = implementing ? linesOver(approved!.baseline.units.find((u) => u.kind === 'journey')?.facets.cases ?? [], openCases) : [];
    const known = (slug: string) => bySlug.has(slug) || approvedSlugs.has(slug);
    const pointers = (doc?.pointers ?? []).map((p) => ({ ...p, target: docs.pointed?.(p.repository, p.slug) ?? null }));
    // A section may name a piece planned elsewhere; a lot may not: it delivers what is planned here.
    const named = (slug: string) => known(slug) || pointers.some((p) => p.slug === slug);
    // The stories the plan is read against: of every narrative a site lands in, and of every one the approved
    // plan landed in, so that a story is still compared once the sites that crossed it are code.
    const landed = new Set([...pieces.flatMap((x) => x.sites.flatMap((s) => s.crossedBy.map((c) => c.narrative))), ...(approved?.baseline.units ?? []).filter((u) => u.kind === 'story').map((u) => u.name)]);
    const snapshot = snapshotOf({ pieces, doc, journeyCases, builtCases }, narratives.flatMap((n) => (landed.has(n.title) && n.steps ? [{ title: n.title, steps: n.steps }] : [])));
    const sectionOf = (kind: UnitKind, name: string) => (kind === 'piece' ? doc?.sections.find((x) => x.piece === name.slice(1)) : kind === 'decision' ? doc?.sections.find((x) => x.piece === null && x.title === name) : undefined);
    const explained = (kind: UnitKind, name: string) => (sectionOf(kind, name)?.changed.length ?? 0) > 0;
    const diffed = approved ? diffSnapshots(approved.baseline, snapshot, explained, input.layout) : null;
    // What the commits made since the approval did beyond the plan joins the delta of the piece each names.
    if (diffed && implementing) {
      for (const [slug, lines] of unplannedLines(commits, new Set([...filesNamed(approved!.baseline), ...filesNamed(snapshot)]), input.layout, [...bySlug.values()])) {
        if (!bySlug.has(slug)) continue;
        const name = `#${slug}`;
        let d = diffed.delta.find((x) => x.kind === 'piece' && x.name === name);
        if (!d) diffed.delta.push(d = { kind: 'piece', name, state: 'changed', facets: [], reason: 'none', edits: [], unclaimed: [] });
        d.facets.push({ facet: UNPLANNED, added: lines, removed: [] });
        d.reason = explained('piece', name) ? 'given' : 'needed';
      }
    }
    return {
      feature,
      folderExists: docs.folderExists,
      doc,
      groups,
      pieces,
      snapshot,
      approved: approved ? { file: approved.file, base: approved.baseline.base, approvedOn: approved.baseline.approvedOn } : null,
      delta: diffed ? diffed.delta.map((d) => {
        groupEdits(d, sectionOf(d.kind, d.name)?.changed ?? [], d.kind === 'piece' ? bySlug.get(d.name.slice(1)) : undefined);
        return d;
      }) : null,
      moves: diffed?.moves ?? [],
      feedback: docs.feedback ?? {},
      unknownLotPieces: doc ? doc.lots.flatMap((l) => l.pieces.filter((slug) => !known(slug)).map((slug) => ({ slug, lot: l.slug, line: l.line }))) : [],
      pointers,
      rulesFile: docs.spec?.file ?? null,
      rules,
      unknownRules: todos.filter((t) => t.rule !== null && !rules.some((r) => r.slug === t.rule)),
      unknownWaivers: waivers.filter((w) => !rules.some((r) => r.slug === w.rule)),
      journeyCases,
      builtCases,
      implementing,
      commits,
      unknownCommitPieces: commits.flatMap((c) => c.pieces.filter((slug) => !bySlug.has(slug)).map((slug) => ({ sha: c.sha, slug }))),
      baseKnown: docs.commits?.baseKnown ?? true,
      unknownRefs: doc ? doc.sections.flatMap((s) => [...new Set([...(s.piece === null ? [] : [s.piece]), ...s.slugs])].filter((slug) => !named(slug)).map((slug) => ({ slug, section: s.title, line: s.line }))) : [],
    };
  });
}

// ── What `--check` says of a plan ──────────────────────────────────────────────

const at = (s: At) => `${s.file}:${s.line}`;

/** `failures` exit 1; `info` is printed. A new function no site names fails, and so do a unit that is not as
 *  approved and says no `Changed:`, a `Changed:` standing on no difference, and a piece in no lot or in two once
 *  `plan.md` holds a "## Delivery". With `archive`, every planned call, comment and test to write left is a
 *  failure, and so are a journey case of the spec still a `todo` and a rule with neither an owner nor a waiver: an implemented piece holds code and a `narrate`, and its tests are
 *  written, still tagged. The archive then takes the tags off the titles. */
export function findings(plan: Plan, archive = false): { failures: string[]; info: string[] } {
  const failures: string[] = [];
  const info: string[] = [];
  const all = plan.pieces.flatMap((s) => [...s.sites, ...s.statics, ...s.todos]);
  const open = (s: PlanPiece) => [...s.sites, ...s.statics, ...s.todos.filter((t) => !t.written)];
  const left = plan.pieces.flatMap(open);
  if (!plan.folderExists) failures.push(`planned: specs/features/${plan.feature}/ does not exist, yet ${all.length} site${all.length === 1 ? '' : 's'} name${all.length === 1 ? 's' : ''} it (${all.map(at).join(', ')})`);
  // The budgets: each fact has one home, and each home is short.
  const over = (n: number, max: number, where: string, what: string, goes: string) => {
    if (n > max) failures.push(`planned: ${where} ${what} in ${n} words, and the budget is ${max} — ${goes}`);
  };
  for (const t of plan.unknownRules) failures.push(`planned: ${at(t)} claims [${t.rule}], which is no rule of ${plan.rulesFile ?? `specs/features/${plan.feature}/spec.md (no such file)`}`);
  for (const r of plan.rules) {
    if (r.owners.length > 1) failures.push(`planned: rule ${plan.feature} [${r.slug}] has ${r.owners.length} owners, and a rule has one — ${r.owners.map(at).join(', ')}`);
    if (r.waiver && r.owners.length) failures.push(`planned: rule ${plan.feature} [${r.slug}] has a test (${r.owners.map(at).join(', ')}) and a waiver (${plan.doc!.file}:${r.waiver.line}), and a rule has one or the other`);
    if (r.waiver) {
      over(words(r.waiver.reason), BUDGET.why, `${plan.doc!.file}:${r.waiver.line} [${r.slug}]`, 'says why no test holds it', 'one reason: what makes the rule true without a test');
      if (archive && r.waiver.toConfirm) failures.push(`archive ${plan.feature}: the waiver of [${r.slug}] still opens "To confirm:" (${plan.doc!.file}:${r.waiver.line})`);
    }
    if (r.owners.length === 0 && !r.waiver) (archive ? failures : info).push(archive ? `archive ${plan.feature}: rule [${r.slug}] is owned by no test (${plan.rulesFile}:${r.line})` : `rule [${r.slug}] has no owner yet (${plan.rulesFile}:${r.line})`);
  }
  for (const p of plan.pointers) {
    const where = `${plan.doc!.file}:${p.line}`;
    const there = `${p.repository}'s ${plan.feature}#${p.slug}`;
    over(words(p.reason), BUDGET.pointer, `${where} #${p.slug}`, 'says what the plan relies on', 'what is relied on, and which pieces stand on it: the piece is stated where it is planned');
    if (plan.pieces.some((x) => x.slug === p.slug)) failures.push(`planned: ${where} points at ${there}, and #${p.slug} is a piece of this plan too — a piece is planned here or there, under two tags when both repositories change`);
    if (p.target === null) info.push(`planned: ${where} points at ${there}, which is not checked — no checkout of ${p.repository} is named under "repositories" of the configuration, or none is there`);
    else if (p.target.statement === null) failures.push(`planned: ${where} points at ${there}, and the plan of that repository holds no such piece (${p.target.source})`);
  }
  for (const w of plan.unknownWaivers) failures.push(`planned: ${plan.doc!.file}:${w.line} waives [${w.rule}], which is no rule of ${plan.rulesFile ?? `specs/features/${plan.feature}/spec.md (no such file)`}`);
  for (const ref of plan.unknownRefs) failures.push(`planned: ${plan.doc!.file}:${ref.line} "${ref.section}" names #${ref.slug}, which is no piece of ${plan.feature}`);
  for (const s of plan.pieces) if (plan.doc && s.doc === null) info.push(`piece #${s.slug} has no section "## #${s.slug}" in ${plan.doc.file}`);
  const elsewhere = `the reason goes to plan.md's "## #slug" section, the cases to the test titles`;
  for (const s of plan.pieces) {
    for (const x of s.sites) over(words(x.sentence), BUDGET.clause, at(x), 'states its change', elsewhere);
    for (const x of s.statics) over(words(x.text), BUDGET.clause, at(x), 'states its change', elsewhere);
    for (const t of s.todos) over(words(t.title), BUDGET.title, at(t), 'is titled', 'a title names one behaviour, and its data is the test\'s');
    if (s.doc) {
      const where = `${plan.doc!.file}:${s.doc.section.line} #${s.slug}`;
      over(words(s.doc.what), BUDGET.what, where, 'states the piece', 'the statement is the first paragraph, the reason the next');
      over(s.doc.why.reduce((n, b) => n + (b.kind === 'p' ? words(b.text) : b.items.reduce((m, i) => m + words(i.text), 0)), 0), BUDGET.why, where, 'gives its reason', 'what the sites and the titles already say is not said again');
      if (s.doc.ask) over(words(`${s.doc.ask.question} ${s.doc.ask.detail}`), BUDGET.ask, `${plan.doc!.file}:${s.doc.ask.line} #${s.slug}`, 'asks its question', 'the question in bold, then the alternative');
      for (const n of s.doc.notes) {
        over(words(n.text), BUDGET.note, `${plan.doc!.file}:${n.line} #${s.slug}`, 'notes what it was built with', 'one point a note: a second point is a second "Note:"');
        if (n.what === null) failures.push(`planned: ${plan.doc!.file}:${n.line} #${s.slug} holds a note with no point — "Note: **the point.** what follows from it", so the reader knows what to keep before reading why`);
      }
    }
  }
  // A shell nobody names is drawn on no flow: the reviewer cannot see where the new code runs.
  for (const s of plan.pieces) {
    for (const x of s.sites) {
      if (x.change === 'added' && callersOf(plan, x).length === 0) failures.push(`planned: ${at(x)} the new \`${x.fn}\` (#${s.slug}) is named by no other site — the clause of the place that will call it names it in backticks, and the page draws it there`);
    }
  }
  // The approved plan: what differs from it says why, and a "Changed:" stands on a difference.
  const unitOf = (section: PlanSection) => (section.piece === null ? section.title : `#${section.piece}`);
  for (const d of plan.delta ?? []) {
    if (d.reason === 'needed') failures.push(`planned: ${d.kind === 'piece' ? d.name : `"${d.name}"`} is not as approved (${plan.approved!.file}: ${d.state === 'new' ? 'new' : d.facets.map((f) => `${f.facet}${f.added.length ? ` +${f.added.length}` : ''}${f.removed.length ? ` −${f.removed.length}` : ''}`).join(', ')}) and its section of ${plan.doc?.file ?? 'plan.md'} holds no "Changed:" — one paragraph saying why, which the reviewer reads before approving again`);
  }
  for (const d of plan.delta ?? []) {
    const where = d.kind === 'piece' ? d.name : `"${d.name}"`;
    for (const e of d.edits) for (const claim of e.unmatched) failures.push(`planned: ${plan.doc!.file}:${e.change.line} ${where} claims ${claim}, and no line of its delta is of that kind and holds that fragment`);
    const loose = d.edits.length > 1 ? d.unclaimed.filter((l) => !isOwnNotice(l.facet)) : [];
    if (loose.length) failures.push(`planned: ${where} holds ${d.edits.length} "Changed:" and ${loose.length} line${loose.length === 1 ? '' : 's'} of its delta that none of them names — an edit ends ' → kind "fragment"; …' naming its lines:${loose.map((l) => `\n      ${l.sign} ${kindOfLine(l)}: ${l.text}`).join('')}`);
  }
  for (const section of plan.doc?.sections ?? []) {
    for (const c of section.changed) {
      const where = `${plan.doc!.file}:${c.line} ${unitOf(section)}`;
      over(words(c.text), BUDGET.changed, where, 'says what moved and why', 'one edit a paragraph: a second edit is a second "Changed:"');
      if (c.what === null) failures.push(`planned: ${where} gives a reason and does not say what moved — "Changed: **what moved.** why", one edit a paragraph, so the reviewer knows which change the reason speaks of`);
      if (plan.delta === null) failures.push(`planned: ${where} says "Changed:" and the plan was never approved — there is nothing to have changed from`);
      else if (!plan.delta.some((d) => d.name === unitOf(section))) failures.push(`planned: ${where} says "Changed:" and is as approved (${plan.approved!.file}) — the paragraph goes`);
    }
  }
  // The delivery: every piece and every screen with a case to write is in one lot.
  const lots = plan.doc?.lots ?? [];
  if (lots.length) {
    const where = (l: PlanLot) => `${plan.doc!.file}:${l.line} lot "${l.slug}"`;
    for (const u of plan.unknownLotPieces) failures.push(`planned: ${plan.doc!.file}:${u.line} lot "${u.lot}" names #${u.slug}, which is no piece of ${plan.feature}`);
    for (const l of lots) over(words(l.reason), BUDGET.lot, where(l), 'gives its reason', 'why these pieces together and why here: what a piece says is not said again');
    const held = (name: string, what: string, inLots: PlanLot[]) => {
      if (inLots.length === 0) failures.push(`planned: ${what} ${name} is in no lot of "## ${DELIVERY_SECTION}" (${plan.doc!.file})`);
      if (inLots.length > 1) failures.push(`planned: ${what} ${name} is in ${inLots.length} lots, and it is delivered once — ${inLots.map((l) => `"${l.slug}"`).join(', ')}`);
    };
    for (const s of plan.pieces) held(`#${s.slug}`, 'piece', lots.filter((l) => l.pieces.includes(s.slug)));
    for (const screen of [...new Set(plan.journeyCases.map((c) => c.screen))]) held(`@${screen}`, 'the journey cases of', lots.filter((l) => l.screens.includes(screen)));
  }
  // The lots as delivered: what a commit did that the plan cannot hold as a line, and a piece no commit names.
  for (const u of plan.unknownCommitPieces) failures.push(`planned: the commit ${u.sha.slice(0, 8)} names #${u.slug}, which is no piece of ${plan.feature} — "Piece: ${plan.feature}#<piece>" names a piece of the plan`);
  for (const c of plan.commits.filter((x) => x.sinceApproval)) {
    for (const t of c.untagged) failures.push(`planned: ${t.file} — "${t.title}" was added by ${c.sha.slice(0, 8)} (#${c.pieces[0]}) under no planned title — a test beyond the plan is titled "${plan.feature}#<piece>: …" and its piece says why in a "Changed:", or it goes`);
  }
  if (plan.approved && !plan.baseKnown) info.push(`the commit of the approval, ${plan.approved.base.slice(0, 8)}, is not in this branch's history: the commits of the lots are not read against the plan`);
  for (const l of lots) {
    const left = lotLeft(plan, l);
    if (!plan.implementing || left.sites + left.tests + left.cases > 0) continue;
    const unnamed = plan.pieces.filter((x) => l.pieces.includes(x.slug) && x.commits.length === 0 && x.built.sites.length + x.built.comments.length + x.todos.length > 0);
    if (unnamed.length) failures.push(`planned: lot "${l.slug}" is delivered and no commit names ${unnamed.map((x) => `#${x.slug}`).join(', ')} — the message of a piece's commit ends with the line "Piece: ${plan.feature}#<piece>"`);
  }
  if (archive && plan.journeyCases.length) failures.push(`archive ${plan.feature}: ${plan.journeyCases.length} journey case${plan.journeyCases.length === 1 ? '' : 's'} of the spec remain${plan.journeyCases.length === 1 ? 's' : ''} to write — ${plan.journeyCases.map(at).join(', ')}`);
  if (archive && left.length) failures.push(`archive ${plan.feature}: ${left.length} planned site${left.length === 1 ? '' : 's'} remain${left.length === 1 ? 's' : ''} — ${plan.pieces.filter((s) => open(s).length).map((s) => `#${s.slug} at ${open(s).map(at).join(', ')}`).join('; ')}`);
  return { failures, info };
}
