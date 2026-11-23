/**
 * plan — a feature's plan as data (`../plan.ts`) and the markdown it reads (`../intent-md.ts`).
 *
 * What is worth fencing: what a reader of the plan page trusts without checking — that a tag is read the same
 * wherever it is written, that a mention of the tag in prose is not counted as a site, that the pieces are told
 * in the order the run crosses them, and that the ownership check says "none", "one" and "two" truthfully.
 *
 * No source reader, no story file, no disk, no project's configuration: the inputs are built here, the test
 * files are read by the smallest title reader (`titles.ts`) and placed by a layout of this folder (`layout.ts`). The tag word is spelled through
 * `TAG` so that no fixture of this file is itself a site when the renderer scans `tests/`.
 */
import { describe, expect, it } from 'vitest';
import { parseIntent, sluggedItems } from '../intent-md';
import {
  BUDGET, SENTENCE_BUDGET, overSentenceBudget,
  assemblePlans, findings, parseTag, parseTodoTitle, replaceSlugRefs, rulesOf, slugRefs, todosByTier,
  lotLeft, planDocOf, reviewItems,
  type FeatureDocs, type PieceCommit, type PlanBaseline, type PlanInput, type PlanSite, type PlanTodo, type StaticSite,
} from '../plan';
import * as plan from '../plan';
import { LAYOUT } from './layout';
import { lineTitles } from './titles';

const TAG = `@${'planned'}`;

// The scans ask a stack's title reader what a file's tests are; here it is this folder's own.
const scanPlannedComments = (file: string, text: string) => plan.scanPlannedComments(file, text, lineTitles);
const scanTodos = (file: string, text: string) => plan.scanTodos(file, text, lineTitles);
const testChanges = (feature: string, file: string, before: string, after: string) => plan.testChanges(feature, file, before, after, lineTitles);
const tierOf = LAYOUT.tierOf;

describe('the tag', () => {
  it('is a feature and a slug, both kebab-case, around one #', () => {
    expect(parseTag('occurrence-cap#cut-to-cap', 'x.ts:1')).toEqual({ feature: 'occurrence-cap', slug: 'cut-to-cap' });
    expect(parseTag('f2#a', 'x.ts:1')).toEqual({ feature: 'f2', slug: 'a' });
  });

  it.each(['occurrence-cap', 'Feature#slug', 'feature#Cut_To', 'feature#', '#slug', 'a#b#c', 'a b#c', 'feature#-x'])('throws on "%s", naming where it was written', (tag) => {
    expect(() => parseTag(tag, 'src/a.ts:12')).toThrow(/src\/a\.ts:12 — .* is not <feature>#<slug>/);
  });
});

describe('scanPlannedComments', () => {
  const at = (sites: StaticSite[]) => sites.map((s) => `${s.feature}#${s.slug} ${s.file}:${s.line} | ${s.text}`);

  it('reads a line comment, the comment lines that continue it, and a trailing comment', () => {
    const text = [
      'export interface Prefs {',
      `  // ${TAG} demo#cap-column the cap, null for "All":`,
      '  // a smallint the server clamps.',
      '  rule: number;',
      `  cap: number | null; // ${TAG} demo#cap-type: joins the type`,
      '}',
    ].join('\n');
    expect(at(scanPlannedComments('src/prefs.ts', text))).toEqual([
      'demo#cap-column src/prefs.ts:2 | the cap, null for "All": a smallint the server clamps.',
      'demo#cap-type src/prefs.ts:5 | joins the type',
    ]);
  });

  it('reads a docblock line up to the next blank or tagged line', () => {
    const text = ['/**', ' * The schema.', ` * ${TAG} demo#dexie-version the store gains the column`, ' *   in version 12.', ' *', ' * Unrelated.', ' */'].join('\n');
    expect(at(scanPlannedComments('src/db.ts', text))).toEqual(['demo#dexie-version src/db.ts:3 | the store gains the column in version 12.']);
  });

  it('reads the comment syntax of the file: -- in SQL, an HTML comment in markdown', () => {
    expect(at(scanPlannedComments('specs/features/demo/078.sql', `-- ${TAG} demo#cap-column\n-- nullable, 1 to 20\nALTER TABLE t ADD c smallint;`))).toEqual(['demo#cap-column specs/features/demo/078.sql:1 | nullable, 1 to 20']);
    expect(at(scanPlannedComments('specs/conventions.md', `Text.\n<!-- ${TAG} demo#doc-settings — the section lists three figures,\n     and will list four -->\nMore.`))).toEqual(['demo#doc-settings specs/conventions.md:2 | the section lists three figures, and will list four']);
    expect(at(scanPlannedComments('supabase/README.md', `<!-- ${TAG} demo#doc-readme: one line -->`))).toEqual(['demo#doc-readme supabase/README.md:1 | one line']);
  });

  it('does not count a mention: prose, inline code, a string, another language\'s comment syntax', () => {
    expect(scanPlannedComments('specs/a.md', `A comment \`${TAG} demo#cut\` where there is no runtime line.\n// ${TAG} demo#cut is not a markdown comment\n\`<!-- ${TAG} demo#cut -->\` in backticks`)).toEqual([]);
    expect(scanPlannedComments('src/a.ts', `const doc = '${TAG} demo#cut';\nconst sql = '-- ${TAG} demo#cut';\nconst s = '//${TAG} demo#cut';`)).toEqual([]);
    expect(scanPlannedComments('src/a.ts', `/** The word ${TAG} in a sentence is no tag. */`)).toEqual([]);
    expect(scanPlannedComments('tests/a.json', `{ "x": "// ${TAG} demo#cut" }`)).toEqual([]);
  });

  it('throws on a malformed tag with the file and the line', () => {
    expect(() => scanPlannedComments('src/a.ts', `const a = 1;\n// ${TAG} demo cut-to-cap`)).toThrow(/src\/a\.ts:2 — "demo" is not <feature>#<slug>/);
    expect(() => scanPlannedComments('x.sql', `-- ${TAG} Demo#Cut`)).toThrow(/x\.sql:1/);
  });
});

describe('scanTodos', () => {
  const file = [
    "import { it } from 'vitest';",
    "describe('band', () => {",
    "  it.todo('demo#cut-to-cap: a due word lists its two latest sentences [rule-is-the-judge]');",
    "  test.todo('demo#cut-to-cap: a tie at the cut is read in reading order');",
    "  it.todo('not tagged at all');",
    "  it('demo#cut-to-cap: a test written keeps its tag [count-exceeds-list]', () => {});",
    "  it('auth#login: lists the due words', () => {});",
    "  it('Demo#3: opens like a tag and is not one', () => {});",
    "  it.todo('demo#save: returns [1, 2]');",
    '});',
  ].join('\n');

  it('reads the tag, the title and the rule a title ends with: a todo is a test to write, a tagged test one written', () => {
    expect(scanTodos('tests/domain/band.test.ts', file).map((t) => [`${t.feature}#${t.slug}`, t.line, t.title, t.rule, t.written])).toEqual([
      ['demo#cut-to-cap', 3, 'a due word lists its two latest sentences', 'rule-is-the-judge', false],
      ['demo#cut-to-cap', 4, 'a tie at the cut is read in reading order', null, false],
      ['demo#cut-to-cap', 6, 'a test written keeps its tag', 'count-exceeds-list', true],
      // Read here as any well-formed tag is; the caller keeps the written tests of features in flight.
      ['auth#login', 7, 'lists the due words', null, true],
      ['demo#save', 9, 'returns [1, 2]', null, false],
    ]);
  });

  it('throws on a title that opens like a tag and is not one', () => {
    expect(() => scanTodos('tests/a.test.ts', "it.todo('Demo#Cut: shouts');")).toThrow(/tests\/a\.test\.ts:1 — "Demo#Cut" is not <feature>#<slug>/);
    expect(parseTodoTitle('handles issue #12: fine', 'x:1')).toBeNull();
  });
});

describe('tierOf', () => {
  const truths = "const TRUTH = 'tests/db/user-preferences-column-posture.test.ts';";
  it('is where the file stands: a narrative, a server test a step names as its truth, else unit', () => {
    expect(tierOf('tests/narratives/review.test.tsx', truths)).toBe('narrative');
    expect(tierOf('tests/db/user-preferences-column-posture.test.ts', truths)).toBe('server');
    expect(tierOf('tests/db/other.test.ts', truths)).toBe('unit');
    expect(tierOf('tests/edge/split.test.ts', '')).toBe('unit');
    expect(tierOf('tests/domain/review.test.ts', truths)).toBe('unit');
  });
});

describe('parseIntent', () => {
  const md = ['# The cap', '', 'Lead line one', 'and two.', '', '## Rules no screen shows', '', '- **rule-a** The first rule,', '  continued.', '- **rule-b** The second.', '', '## Decision', '', '#cut-to-cap opens a paragraph and is no heading.'].join('\n');

  it('parses the title, the lead, the sections, and takes an item\'s slug off its text', () => {
    const intent = parseIntent(md, 'spec.md');
    expect(intent.title).toBe('The cap');
    expect(intent.lead).toEqual([{ kind: 'p', text: 'Lead line one and two.', line: 3 }]);
    expect(sluggedItems(intent, 'Rules no screen shows')).toEqual([
      { slug: 'rule-a', text: 'The first rule, continued.', line: 8 },
      { slug: 'rule-b', text: 'The second.', line: 10 },
    ]);
    expect(intent.sections[1].blocks).toEqual([{ kind: 'p', text: '#cut-to-cap opens a paragraph and is no heading.', line: 14 }]);
  });

  it('throws, with the line, on structure a section does not hold', () => {
    expect(() => parseIntent('# T\n\n## S\n\n### deeper', 'plan.md')).toThrow(/plan\.md:5/);
    expect(() => parseIntent('no title', 'plan.md')).toThrow(/plan\.md:1/);
  });

  it('holds every rule to a slug, and to a slug of its own', () => {
    expect(() => rulesOf(parseIntent('# T\n\n## Rules no screen shows\n\n- **rule-a** One.\n- A rule with no name.', 'spec.md'), 'spec.md')).toThrow(/spec\.md:6/);
    expect(() => rulesOf(parseIntent('# T\n\n## Rules no screen shows\n\n- **rule-a** One.\n- **rule-a** Two.', 'spec.md'), 'spec.md')).toThrow(/spec\.md:6 — two rules are named "rule-a"/);
    expect(rulesOf(parseIntent('# T\n\n## Other\n\n- x', 'spec.md'), 'spec.md')).toEqual([]);
  });
});

describe('slug references of plan.md', () => {
  it('finds each #slug once, in order, and leaves anchors and prose alone', () => {
    expect(slugRefs('Decided in #cut-to-cap (and #save). See `#cut-to-cap`; not a#b, not page.html#top.')).toEqual(['cut-to-cap', 'save']);
    expect(replaceSlugRefs('#a then (#b)', (s) => `<${s}>`)).toBe('<a> then (<b>)');
  });
});

// ── assembly ───────────────────────────────────────────────────────────────────

const site = (slug: string, file: string, line: number, crossedBy: PlanSite['crossedBy'] = [], change: PlanSite['change'] = 'changed'): PlanSite => ({
  feature: 'demo', slug, id: `planned:demo#${slug}@${file}:${line}`, file, line, column: 3, fn: 'fn', change, sentence: `${slug} happens.`, signature: change === 'added' ? 'export function fn()' : null,
  crossedBy, reachedBy: [], expect: null, distinct: [], seenBy: [],
});
const comment = (slug: string, file: string, line: number, removes = false): StaticSite => ({ feature: 'demo', slug, file, line, column: 4, text: `${slug} in a comment`, removes, on: null });
const todo = (slug: string, file: string, line: number, rule: string | null = null, tier: PlanTodo['tier'] = 'unit'): PlanTodo => ({ feature: 'demo', slug, file, line, column: 3, title: `${slug} is tested`, rule, tier, written: false, reproduction: false, run: null });
const crossed = (narrative: string, at: number) => ({ narrative, at, step: null });

const SPEC = '# Demo\n\n## Rules no screen shows\n\n- **owned-once** One owner.\n- **owned-twice** Two owners.\n- **owned-by-none** No owner.\n';
const PLAN = '# The plan\n\nLead.\n\n## Where the cap is applied\n\nIn the reader: #cut and #save.\n\n## The column\n\n- #cap-column is nullable.\n- #ghost is named and does not exist.\n';
const docs = (plan: string | null = PLAN, spec: string | null = SPEC, folderExists = true) => (feature: string): FeatureDocs => ({
  folderExists,
  plan: plan === null ? null : { file: `specs/features/${feature}/plan.md`, intent: parseIntent(plan, 'plan.md') },
  spec: spec === null ? null : { file: `specs/features/${feature}/spec.md`, intent: parseIntent(spec, 'spec.md') },
});
const NARRATIVES: PlanInput['narratives'] = [
  { title: 'The settings provider', kind: 'mechanism' },
  { title: 'The learner changes the rule', kind: 'product' },
  { title: 'The band under a sentence', kind: 'product' },
];
const assemble = (input: Partial<PlanInput>) => assemblePlans({ sites: [], statics: [], todos: [], narratives: NARRATIVES, docs: docs(), layout: LAYOUT, ...input });

describe('assemblePlans', () => {
  it('makes one piece of every site that shares a slug: calls, comments and tests of any tier', () => {
    const [plan] = assemble({
      sites: [site('cut', 'src/reader.ts', 40), site('cut', 'src/band.tsx', 12)],
      statics: [comment('cut', 'src/types.ts', 7)],
      todos: [todo('cut', 'tests/narratives/review.test.tsx', 90, null, 'narrative'), todo('cut', 'tests/db/prefs.test.ts', 5, null, 'server'), todo('cut', 'tests/domain/cut.test.ts', 3)],
    });
    expect(plan.feature).toBe('demo');
    expect(plan.pieces.map((s) => s.slug)).toEqual(['cut']);
    const [piece] = plan.pieces;
    expect(piece.sites.map((s) => s.file)).toEqual(['src/band.tsx', 'src/reader.ts']);
    expect(piece.statics.map((s) => s.file)).toEqual(['src/types.ts']);
    const tiers = todosByTier(piece);
    expect([tiers.narrative.length, tiers.server.length, tiers.unit.length]).toEqual([1, 1, 1]);
  });

  it('tells the pieces in run order: by narrative, product first, each piece where a canonical story first crosses it', () => {
    const [plan] = assemble({
      sites: [
        // The band's story crosses `cut` (at 9, through its second site) after `fetch` (at 4).
        site('cut', 'src/a.ts', 1, [crossed('The band under a sentence', 30)]),
        site('cut', 'src/z.ts', 1, [crossed('The band under a sentence', 9)]),
        site('fetch', 'src/b.ts', 1, [crossed('The band under a sentence', 4)]),
        // The settings story crosses `save`, then `mirror`; the mechanism crosses `save` too, earlier: told once.
        site('mirror', 'src/c.ts', 1, [crossed('The learner changes the rule', 8)]),
        site('save', 'src/d.ts', 1, [crossed('The settings provider', 1), crossed('The learner changes the rule', 5)]),
        // Only the mechanism crosses `gate`.
        site('gate', 'src/e.ts', 1, [crossed('The settings provider', 2)]),
      ],
    });
    expect(plan.groups.map((g) => [g.kind, g.narrative, g.pieces.map((s) => s.slug)])).toEqual([
      ['narrative', 'The band under a sentence', ['fetch', 'cut']],
      ['narrative', 'The learner changes the rule', ['save', 'mirror']],
      ['narrative', 'The settings provider', ['gate']],
    ]);
    expect(plan.pieces.map((s) => s.slug)).toEqual(['fetch', 'cut', 'save', 'mirror', 'gate']);
  });

  it('lists after them the pieces no canonical story crosses, then the pieces with no runtime line, in file order', () => {
    const [plan] = assemble({
      sites: [site('crossed', 'src/a.ts', 1, [crossed('The band under a sentence', 0)]), site('shell', 'src/new.ts', 3, [], 'added'), site('untold', 'src/lonely.ts', 9)],
      statics: [comment('type', 'src/types.ts', 7), comment('cap-column', 'specs/features/demo/078-cap.sql', 1), comment('cap-column', 'supabase/README.md', 40), comment('shell', 'src/types.ts', 2)],
      todos: [todo('test-only', 'tests/domain/x.test.ts', 4)],
    });
    expect(plan.groups.map((g) => [g.kind, g.pieces.map((s) => s.slug)])).toEqual([
      ['narrative', ['crossed']],
      ['uncrossed', ['untold', 'shell']],
      ['static', ['cap-column', 'type', 'test-only']],
    ]);
    // The feature folder's tagged .sql is the piece's proposed migration; a comment elsewhere is a plain site.
    expect(plan.pieces.find((s) => s.slug === 'cap-column')!.sql).toEqual(['specs/features/demo/078-cap.sql']);
    expect(plan.pieces.find((s) => s.slug === 'type')!.sql).toEqual([]);
  });

  it('links plan.md both ways: a section names its pieces, a piece lists the sections naming it', () => {
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1), site('save', 'src/b.ts', 1)], statics: [comment('cap-column', 'x.sql', 1), comment('orphan', 'src/t.ts', 1)] });
    expect(plan.doc!.title).toBe('The plan');
    expect(plan.doc!.sections.map((s) => [s.anchor, s.slugs])).toEqual([
      ['decision-where-the-cap-is-applied', ['cut', 'save']],
      ['decision-the-column', ['cap-column', 'ghost']],
    ]);
    const decided = (slug: string) => plan.pieces.find((s) => s.slug === slug)!.decidedIn.map((s) => s.title);
    expect(decided('cut')).toEqual(['Where the cap is applied']);
    expect(decided('cap-column')).toEqual(['The column']);
    expect(decided('orphan')).toEqual([]);
    expect(plan.unknownRefs).toEqual([{ slug: 'ghost', section: 'The column', line: 9 }]);
  });

  it('reads a piece\'s own section: its statement, its reason, the one point to confirm', () => {
    const md = [
      '# P', '', '## #cut', '', 'The reader cuts each word to the cap.', '', 'Two cuts, because of ties.', '', '- the first on stamps', '',
      'To confirm: **Ties are kept by the first cut.** The alternative reads every row.', '',
      '## #save', '', 'The cap is saved with the rule.', '', 'To confirm: a question with no bold part', '',
      '## Across', '', 'Both #cut and #save regenerate the snapshot.', '',
    ].join('\n');
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1), site('save', 'src/b.ts', 1), site('bare', 'src/c.ts', 1)], docs: docs(md, null) });
    const piece = (slug: string) => plan.pieces.find((s) => s.slug === slug)!;
    expect(piece('cut').doc).toMatchObject({
      what: 'The reader cuts each word to the cap.',
      why: [{ kind: 'p', text: 'Two cuts, because of ties.' }, { kind: 'ul', items: [{ text: 'the first on stamps' }] }],
      ask: { question: 'Ties are kept by the first cut.', detail: 'The alternative reads every row.', line: 11 },
      section: { anchor: 'piece-cut', piece: 'cut', line: 3 },
    });
    expect(piece('save').doc!.ask).toEqual({ question: 'a question with no bold part', detail: '', line: 17 });
    expect(piece('save').doc!.why).toEqual([]);
    expect(piece('bare').doc).toBeNull();
    // A piece's own section is not a decision across pieces; the section that names both is.
    expect(piece('cut').decidedIn.map((s) => s.title)).toEqual(['Across']);
    expect(plan.unknownRefs).toEqual([]);
  });

  it('refuses a piece section that does not open with its statement, asks twice, or is titled with more than its tag', () => {
    const one = (md: string) => () => assemble({ sites: [site('cut', 'src/a.ts', 1)], docs: docs(md, null) });
    expect(one('# P\n\n## #cut\n\n- a list first\n')).toThrow(/plan\.md:3 — "## #cut" opens with its statement/);
    expect(one('# P\n\n## #cut\n\nTo confirm: a question first\n')).toThrow(/opens with its statement/);
    expect(one('# P\n\n## #cut\n\nIt cuts.\n\nTo confirm: one\n\nTo confirm: two\n')).toThrow(/plan\.md:9 — "## #cut" holds 2 "To confirm:" paragraphs/);
    expect(one('# P\n\n## #cut the reader\n\nIt cuts.\n')).toThrow(/plan\.md:3 — "## #cut the reader": a piece's section is titled with its tag alone/);
  });

  it('gives each rule of spec.md its owners: none, one, two — and sets apart a claim on no rule', () => {
    const [plan] = assemble({
      docs: docs(null),
      todos: [
        todo('cut', 'tests/narratives/review.test.tsx', 10, 'owned-once', 'narrative'),
        todo('cut', 'tests/narratives/review.test.tsx', 11, 'owned-twice', 'narrative'),
        todo('save', 'tests/domain/save.test.ts', 4, 'owned-twice'),
        todo('save', 'tests/domain/save.test.ts', 5, 'not-a-rule'),
        todo('save', 'tests/domain/save.test.ts', 6),
      ],
    });
    expect(plan.rules.map((r) => [r.slug, r.owners.map((o) => `${o.file}:${o.line}`)])).toEqual([
      ['owned-once', ['tests/narratives/review.test.tsx:10']],
      ['owned-twice', ['tests/domain/save.test.ts:4', 'tests/narratives/review.test.tsx:11']],
      ['owned-by-none', []],
    ]);
    expect(plan.unknownRules.map((t) => t.rule)).toEqual(['not-a-rule']);

    const { failures, info } = findings(plan);
    expect(failures).toEqual([
      'planned: tests/domain/save.test.ts:5 claims [not-a-rule], which is no rule of specs/features/demo/spec.md',
      'planned: rule demo [owned-twice] has 2 owners, and a rule has one — tests/domain/save.test.ts:4, tests/narratives/review.test.tsx:11',
    ]);
    expect(info).toContain('rule [owned-by-none] has no owner yet (specs/features/demo/spec.md:7)');
    expect(info.some((line) => line.includes('owned-once'))).toBe(false);
  });

  it('a rule waived in plan.md needs no owner; a waiver and a test together fail, and so does a waiver of no rule', () => {
    const md = '# P\n\n## Rules no test holds\n\n- **owned-by-none** True by the order of the code: the cut is made before the read.\n- **owned-once** To confirm: A test would restate the code.\n- **ghost-rule** Names nothing.\n';
    const [plan] = assemble({
      docs: docs(md),
      todos: [todo('cut', 'tests/narratives/review.test.tsx', 10, 'owned-once', 'narrative')],
    });
    expect(plan.doc!.sections).toEqual([]);
    expect(plan.rules.map((r) => [r.slug, r.waiver && [r.waiver.reason, r.waiver.toConfirm, r.waiver.line]])).toEqual([
      ['owned-once', ['A test would restate the code.', true, 6]],
      ['owned-twice', null],
      ['owned-by-none', ['True by the order of the code: the cut is made before the read.', false, 5]],
    ]);
    const { failures, info } = findings(plan);
    expect(failures).toEqual([
      'planned: rule demo [owned-once] has a test (tests/narratives/review.test.tsx:10) and a waiver (specs/features/demo/plan.md:6), and a rule has one or the other',
      'planned: specs/features/demo/plan.md:7 waives [ghost-rule], which is no rule of specs/features/demo/spec.md',
    ]);
    expect(info).toContain('rule [owned-twice] has no owner yet (specs/features/demo/spec.md:6)');
    expect(info.some((line) => line.includes('owned-by-none'))).toBe(false);
    expect(findings(plan, true).failures).toContain('archive demo: the waiver of [owned-once] still opens "To confirm:" (specs/features/demo/plan.md:6)');
    expect(findings(plan, true).failures.some((line) => line.includes('[owned-by-none]'))).toBe(false);
  });

  it('refuses a waivers section that is not a list of named rules, and a reason over its budget', () => {
    const one = (md: string) => () => assemble({ sites: [site('cut', 'src/a.ts', 1)], docs: docs(md) });
    expect(one('# P\n\n## Rules no test holds\n\nSome prose.\n')).toThrow(/plan\.md:5 — "## Rules no test holds" holds a list and nothing else/);
    expect(one('# P\n\n## Rules no test holds\n\n- no rule named\n')).toThrow(/plan\.md:5 — a waiver names its rule in bold/);
    expect(one('# P\n\n## Rules no test holds\n\n- **owned-once** To confirm:\n')).toThrow(/a waiver names its rule in bold, then says why/);
    expect(one('# P\n\n## Rules no test holds\n\n- **owned-once** One.\n- **owned-once** Two.\n')).toThrow(/plan\.md:6 — two waivers name \[owned-once\]/);
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1)], docs: docs(`# P\n\n## Rules no test holds\n\n- **owned-once** ${'word '.repeat(61)}\n`) });
    expect(findings(plan).failures).toEqual(['planned: specs/features/demo/plan.md:5 [owned-once] says why no test holds it in 61 words, and the budget is 60 — one reason: what makes the rule true without a test']);
  });

  it('carries the spec\'s journey cases of its feature, and the archive fails while one remains', () => {
    // The cases as a stack's title reader gives them for a journey test (`TestFile.journeyCases`).
    const cases = [
      { feature: 'demo', journey: 'Change the rule', screen: 'rule-card', title: 'a fourth row sits under the three', file: 'tests/e2e/journeys/a.journey.spec.ts', line: 3, column: 3 },
      { feature: 'other', journey: 'Change the rule', screen: 'rule-card', title: 'not ours', file: 'tests/e2e/journeys/a.journey.spec.ts', line: 4, column: 3 },
    ];
    const [plan, ...rest] = assemble({ sites: [site('cut', 'src/a.ts', 1)], journeyCases: cases });
    // A feature only a journey case names has a spec and no plan yet: no plan is made for it.
    expect(rest).toEqual([]);
    expect(plan.journeyCases.map((c) => c.title)).toEqual(['a fourth row sits under the three']);
    expect(findings(plan).failures.some((line) => line.includes('journey case'))).toBe(false);
    expect(findings(plan, true).failures).toContain('archive demo: 1 journey case of the spec remains to write — tests/e2e/journeys/a.journey.spec.ts:3');
  });

  it('keeps features apart', () => {
    const plans = assemble({ sites: [site('cut', 'src/a.ts', 1), { ...site('cut', 'src/b.ts', 1), feature: 'other' }] });
    expect(plans.map((p) => [p.feature, p.pieces.length, p.pieces[0].sites[0].file])).toEqual([['demo', 1, 'src/a.ts'], ['other', 1, 'src/b.ts']]);
  });
});

describe('findings', () => {
  it('fails a site whose feature folder is gone and a #slug of plan.md that names no piece', () => {
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1)], docs: docs(PLAN, null, false) });
    const { failures, info } = findings(plan);
    expect(failures).toEqual([
      'planned: specs/features/demo/ does not exist, yet 1 site names it (src/a.ts:1)',
      'planned: specs/features/demo/plan.md:5 "Where the cap is applied" names #save, which is no piece of demo',
      'planned: specs/features/demo/plan.md:9 "The column" names #cap-column, which is no piece of demo',
      'planned: specs/features/demo/plan.md:9 "The column" names #ghost, which is no piece of demo',
    ]);
    expect(info).toEqual(['piece #cut has no section "## #cut" in specs/features/demo/plan.md']);
  });

  it('lists a piece with no section of its own in plan.md, and nothing when there is no plan.md', () => {
    const input = { sites: [site('cut', 'src/a.ts', 1)], statics: [comment('orphan', 'src/t.ts', 1)] };
    expect(findings(assemble({ ...input, docs: docs('# P\n\n## #cut\n\nThe reader cuts.\n', null) })[0])).toEqual({ failures: [], info: ['piece #orphan has no section "## #orphan" in specs/features/demo/plan.md'] });
    expect(findings(assemble({ ...input, docs: docs(null, null) })[0])).toEqual({ failures: [], info: [] });
  });

  it('fails a section titled after a piece no site carries', () => {
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1)], docs: docs('# P\n\n## #cut\n\nThe reader cuts.\n\n## #gone\n\nA piece that was dropped.\n', null) });
    expect(findings(plan).failures).toEqual(['planned: specs/features/demo/plan.md:7 "#gone" names #gone, which is no piece of demo']);
  });

  it('fails each piece over its budget, naming where the rest belongs', () => {
    const long = (n: number) => Array.from({ length: n }, (_, i) => `w${i}`).join(' ');
    const md = `# P\n\n## #cut\n\n${long(BUDGET.what + 1)}\n\n${long(BUDGET.why)}\n\n- one more\n\nTo confirm: **${long(BUDGET.ask)}** more\n`;
    const [plan] = assemble({
      sites: [{ ...site('cut', 'src/a.ts', 1), sentence: long(BUDGET.clause + 1) }, { ...site('cut', 'src/b.ts', 2), sentence: long(BUDGET.clause) }],
      statics: [{ ...comment('cut', 'src/t.ts', 3), text: long(BUDGET.clause + 2) }],
      todos: [{ ...todo('cut', 'tests/x.test.ts', 4), title: long(BUDGET.title + 1) }, { ...todo('cut', 'tests/x.test.ts', 5), title: long(BUDGET.title) }],
      docs: docs(md, null),
    });
    expect(findings(plan).failures.map((f) => f.split(' — ')[0])).toEqual([
      `planned: src/a.ts:1 states its change in ${BUDGET.clause + 1} words, and the budget is ${BUDGET.clause}`,
      `planned: src/t.ts:3 states its change in ${BUDGET.clause + 2} words, and the budget is ${BUDGET.clause}`,
      `planned: tests/x.test.ts:4 is titled in ${BUDGET.title + 1} words, and the budget is ${BUDGET.title}`,
      `planned: specs/features/demo/plan.md:3 #cut states the piece in ${BUDGET.what + 1} words, and the budget is ${BUDGET.what}`,
      `planned: specs/features/demo/plan.md:3 #cut gives its reason in ${BUDGET.why + 2} words, and the budget is ${BUDGET.why}`,
      `planned: specs/features/demo/plan.md:11 #cut asks its question in ${BUDGET.ask + 1} words, and the budget is ${BUDGET.ask}`,
    ]);
  });

  it('at the archive gate, fails while a site of any kind remains', () => {
    const [plan] = assemble({ sites: [site('cut', 'src/a.ts', 1)], statics: [comment('type', 'src/t.ts', 2)], todos: [todo('cut', 'tests/x.test.ts', 3)], docs: docs(null, null) });
    expect(findings(plan).failures).toEqual([]);
    expect(findings(plan, true).failures).toEqual(['archive demo: 3 planned sites remain — #cut at src/a.ts:1, tests/x.test.ts:3; #type at src/t.ts:2']);
  });

  it('at the archive gate, passes once nothing is planned and every rule is owned by a written test', () => {
    const spec = '# S\n\n## Rules no screen shows\n\n- **one-rule** A rule.\n- **other-rule** Another.\n';
    const written = (rule: string | null) => ({ ...todo('cut', 'tests/x.test.ts', rule === 'other-rule' ? 9 : 3, rule), written: true });
    const [unowned] = assemble({ todos: [written('one-rule')], docs: docs(null, spec) });
    expect(findings(unowned).failures).toEqual([]);
    expect(findings(unowned, true).failures).toEqual(['archive demo: rule [other-rule] is owned by no test (specs/features/demo/spec.md:6)']);
    const [done] = assemble({ todos: [written('one-rule'), written('other-rule')], docs: docs(null, spec) });
    expect(findings(done, true).failures).toEqual([]);
  });
});

describe('a bug', () => {
  // A reproduction is a written test declared to fail today; evidence is what it saw at a place of its piece.
  const reproduction = (line = 3): PlanTodo => ({ ...todo('cut', 'tests/x.test.ts', line), written: true, reproduction: true });
  // What a crossing should have seen is its own: the place says how it is computed, a run says its value.
  const evidence = (seen: unknown[] | null, expect: unknown = { due: 6 }): PlanSite => ({
    ...site('cut', 'src/a.ts', 1, [], 'evidence'), expect: expect === null ? null : "{'due': total - card}",
    seenBy: seen === null ? [] : [{ file: 'tests/x.test.ts', test: 'demo#cut: cut is tested', at: 0, crossings: seen.map((watch) => ({ watch, expect })) }],
  });
  const failed = (sites: PlanSite[], todos: PlanTodo[] = [reproduction()]) => findings(assemble({ sites, todos, docs: docs(null, null) })[0]);

  it('reads a reproduction as written and still owed: its lot is not delivered, and the archive gate holds', () => {
    const [plan] = assemble({ todos: [reproduction()], docs: docs('# P\n\n## #cut\n\nCuts.\n\n## Delivery\n\n- **a** #cut — why\n', null) });
    expect(lotLeft(plan, plan.doc!.lots[0])).toEqual({ sites: 0, tests: 1, cases: 0 });
    expect(findings(plan).failures).toEqual([]);
    expect(findings(plan, true).failures).toEqual(['archive demo: 1 planned site remains — #cut at tests/x.test.ts:3']);
  });

  it('holds a place that expects a value to a reproduction that saw another there', () => {
    expect(failed([evidence([{ due: 10 }])]).failures).toEqual([]);
    // One crossing in many is enough: the place is crossed for what works too.
    expect(failed([evidence([{ due: 6 }, { due: 10 }, { due: 6 }])]).failures).toEqual([]);
    expect(failed([evidence([{ due: 6 }, { due: 6 }])]).failures.map((f) => f.split(' — ')[0])).toEqual([
      "planned: src/a.ts:1 expects {'due': total - card}, and that is what the reproduction that crosses it saw at every crossing",
    ]);
    // A key the watch does not give is a value the place does not have; a crossing that expects nothing has none wrong.
    expect(plan.unexpected({ watch: { due: 6 }, expect: { due: 6, kind: 'card' } })).toEqual(['kind']);
    expect(plan.unexpected({ watch: null, expect: { due: 6 } })).toEqual(['due']);
    expect(plan.unexpected({ watch: { due: 10 }, expect: null })).toEqual([]);
  });

  it('holds a place whose crossings should each see their own value to two that saw the same', () => {
    // The bug is no crossing's own: it is a value two of them share, as two rows written under one id.
    const row = (seen: unknown[]): PlanSite => ({ ...evidence(seen, null), change: 'changed', distinct: ['id'] });
    const cpu = { id: 'row-footprint', of: 'cpu' };
    const ram = { id: 'row-footprint', of: 'ram' };
    const power = { id: 'row-power', of: 'cpu' };
    expect(plan.shared(['id'], [cpu, power, ram].map((watch) => ({ watch, expect: null }))).map((group) => group.map((c) => c.watch))).toEqual([[cpu, ram]]);
    expect(failed([row([cpu, power, ram])]).failures).toEqual([]);
    expect(failed([row([cpu, power])]).failures.map((f) => f.split(' — ')[0])).toEqual([
      'planned: src/a.ts:1 says each crossing sees its own id, and that is what the reproduction that crosses it saw at every crossing',
    ]);
    // Several keys are one value together; a crossing whose watch lacks one shares nothing; no key, no group.
    expect(plan.shared(['id', 'of'], [cpu, ram, cpu].map((watch) => ({ watch, expect: null })))).toHaveLength(1);
    expect(plan.shared(['id'], [{ watch: { of: 'cpu' }, expect: null }, { watch: null, expect: null }])).toEqual([]);
    expect(plan.shared([], [cpu, cpu].map((watch) => ({ watch, expect: null })))).toEqual([]);
    // What a place says is distinct is approved with its clause, as what it expects is.
    expect(plan.siteLineOf(row([]))).toBe('changed src/a.ts in fn — cut happens. ⇒ distinct id');
  });

  it('asks nothing of evidence that expects no value, and says which reproductions to run for one no story crosses', () => {
    expect(failed([evidence([{ due: 10 }], null)])).toEqual({ failures: [], info: [] });
    const unseen = failed([evidence(null)]);
    expect(unseen.failures).toEqual([]);
    expect(unseen.info).toEqual(['src/a.ts:1 (#cut) is crossed by no reproduction of its piece in the stories on file — run tests/x.test.ts, then check again']);
  });

  it('fails evidence of a piece that has no reproduction: nothing can have seen it', () => {
    expect(failed([evidence(null)], []).failures.map((f) => f.split(' — ')[0])).toEqual(['planned: src/a.ts:1 is evidence of #cut, which has no reproduction']);
  });

  it('approves what a place expects with its clause, and takes evidence that went for no place left unbuilt', () => {
    expect(plan.siteLineOf(evidence(null))).toBe("evidence src/a.ts in fn — cut happens. ⇒ {'due': total - card}");
    expect(plan.siteLineOf(evidence(null, null))).toBe('evidence src/a.ts in fn — cut happens.');
    // A place built is one its commits wrote at; evidence goes with the fix and nothing is written there.
    const lines = plan.unplannedLines([], new Set(), LAYOUT, [{ slug: 'cut', sites: [], statics: [], todos: [], sql: [], doc: null, bug: null, decidedIn: [], built: { sites: [plan.siteLineOf(evidence(null))], comments: [] }, commits: [{ sha: '1', subject: 's', pieces: ['cut'], sinceApproval: true, files: [{ file: 'src/a.ts', added: 0, removed: 3, line: 1 }], untagged: [], deleted: [], planned: [] }] }]);
    expect([...lines]).toEqual([]);
  });

  it('reads a bug as a section of plan.md, and the pieces whose sections stand under it as what fixes it', () => {
    const md = ['# P', '', '## #free', '', 'A piece of no bug.', '',
      '## Bug: The total ignores the card', '', 'The buyer pays the whole amount: see #save.', '', '## #cut', '', 'Cuts.', '', '## #save', '', 'Saves.', '',
      '## Bug: Two rows share an id', '', 'One click opens both.', '', '## #row', '', 'Rows.', '',
      '## Across', '', 'Decides #cut and #row.', ''].join('\n');
    const [made] = assemble({ sites: [site('free', 'src/a.ts', 1), site('cut', 'src/a.ts', 2), site('save', 'src/a.ts', 3), site('row', 'src/a.ts', 4)], docs: docs(md, null) });
    const piece = (slug: string) => made.pieces.find((p) => p.slug === slug)!;
    // The title is the bug's, its prefix taken off; a piece stands under the last bug above its section.
    expect(made.doc!.sections.filter((s) => s.bug).map((s) => [s.title, s.anchor])).toEqual([['The total ignores the card', 'bug-the-total-ignores-the-card'], ['Two rows share an id', 'bug-two-rows-share-an-id']]);
    expect(['free', 'cut', 'save', 'row'].map((slug) => piece(slug).bug?.title ?? null)).toEqual([null, 'The total ignores the card', 'The total ignores the card', 'Two rows share an id']);
    // A bug is no decision across pieces: the piece it names in passing is not decided there.
    expect(piece('save').decidedIn).toEqual([]);
    expect(piece('cut').decidedIn.map((s) => s.title)).toEqual(['Across']);
    expect(findings(made).failures).toEqual([]);
    // It is approved as a unit of its own, under its whole title.
    expect(made.doc!.sections.map(plan.unitNameOf)).toEqual(['#free', 'Bug: The total ignores the card', '#cut', '#save', 'Bug: Two rows share an id', '#row', 'Across']);
  });

  it('fails a bug no piece stands under, one that says too much, and one with no title', () => {
    const long = Array.from({ length: 61 }, () => 'word').join(' ');
    const [made] = assemble({ sites: [site('cut', 'src/a.ts', 2)], docs: docs(`# P\n\n## Bug: Fixed by nothing\n\nNobody fixes it.\n\n## Bug: Said at length\n\n${long}\n\n## #cut\n\nCuts.\n`, null) });
    expect(findings(made).failures.map((f) => f.split(' — ')[0])).toEqual([
      'planned: specs/features/demo/plan.md:3 bug "Fixed by nothing" has no piece under it',
      'planned: specs/features/demo/plan.md:7 bug "Said at length" says what is wrong in 61 words, and the budget is 60',
    ]);
    expect(() => planDocOf(parseIntent('# P\n\n## Bug:\n\nNothing.\n', 'plan.md'), 'plan.md')).toThrow(/plan\.md:3 — "## Bug:": a bug's section is titled with what is wrong/);
  });

  it('matches a story to its tagged test by file and title, a parametrized case included', () => {
    const t = reproduction();
    expect(plan.isStoryOf(t, { file: 'tests/x.test.ts', test: 'demo#cut: cut is tested' })).toBe(true);
    expect(plan.isStoryOf(t, { file: 'tests/x.test.ts', test: 'demo#cut: cut is tested[card]' })).toBe(true);
    expect(plan.isStoryOf(t, { file: 'tests/y.test.ts', test: 'demo#cut: cut is tested' })).toBe(false);
  });
});

describe('a removal comment', () => {
  it('reads the tag with .remove as a site that removes what stands under it', () => {
    const [kept, gone] = scanPlannedComments('tests/x.test.ts', `// ${TAG} demo#cut the case below gains the cap\n// ${TAG}.remove demo#cut held by the narrative case "lists the latest 2"\n`);
    expect([kept.removes, kept.text]).toEqual([false, 'the case below gains the cap']);
    expect([gone.removes, gone.slug, gone.text]).toEqual([true, 'cut', 'held by the narrative case "lists the latest 2"']);
  });
});

describe('what a comment site stands on', () => {
  const on = (file: string, text: string) => scanPlannedComments(file, text).map((s) => s.on);

  it('is what the title reader says the first line under it opens, as the pages print it', () => {
    expect(on('tests/x.test.ts', `  // ${TAG}.remove demo#cut held by the reference case\n  it('a tap moves the figure, and it\\'s not saved', async () => {\n`)).toEqual(['it "a tap moves the figure, and it\'s not saved"']);
    // Two comments stacked on one test stand on that test, both of them.
    expect(on('tests/x.test.ts', `// ${TAG} demo#cut reads Y's range\n// ${TAG} demo#cut reads the fourth row\nit('the reference case', () => {\n`)).toEqual(['it "the reference case"', 'it "the reference case"']);
  });

  it('is nothing after a blank line, and over a line the reader says opens nothing', () => {
    expect(on('tests/x.test.ts', `// ${TAG} demo#cut a note\n\nit('far', () => {});\n`)).toEqual([null]);
    expect(on('tests/x.test.ts', `// ${TAG} demo#cut the select names the column\n  .select(COLUMNS)\n`)).toEqual([null]);
  });
});

describe('a new function nobody names', () => {
  const shell = { ...site('seam', 'src/due.ts', 59, [], 'added'), fn: 'latestPriors' };

  it('fails: no clause says where it will be called from, so no flow shows it', () => {
    const [plan] = assemble({ sites: [shell, site('cut', 'src/reader.ts', 151)], docs: docs(null, null) });
    expect(findings(plan).failures).toEqual(['planned: src/due.ts:59 the new `latestPriors` (#seam) is named by no other site — the clause of the place that will call it names it in backticks, and the page draws it there']);
  });

  it('passes once the clause of the place that will call it names it, as a symbol or as a call', () => {
    for (const sentence of ['calls `latestPriors` after the decision', 'hands the cap to `latestPriors(due, cap)`']) {
      const [plan] = assemble({ sites: [shell, { ...site('cut', 'src/reader.ts', 151), sentence }], docs: docs(null, null) });
      expect(findings(plan).failures).toEqual([]);
    }
  });
});

describe('the delivery', () => {
  const PIECES = '# P\n\n## #cut\n\nThe reader cuts.\n\n## #save\n\nSave sends it.\n';
  const lots = (items: string) => `${PIECES}\n## Delivery\n\n${items}\n`;
  const input = { sites: [site('cut', 'src/reader.ts', 1), site('save', 'src/card.tsx', 2)], todos: [todo('cut', 'tests/x.test.ts', 3)] };
  const cases = [{ feature: 'demo', journey: 'Study', screen: 'review-band', title: 'lists the latest', file: 'tests/e2e/journeys/study.journey.spec.ts', line: 9, column: 3 }];

  it('reads each lot: its slug, its difficulty, its pieces in order, its screens, its reason — a #slug in the reason is a mention', () => {
    const doc = planDocOf(parseIntent(lots('- **the-reader** (hard) #cut @review-band — The reader first.\n- **the-card** #save, on what #cut left.'), 'plan.md'), 'plan.md');
    expect(doc.lots.map(({ line: _line, ...lot }) => lot)).toEqual([
      { slug: 'the-reader', difficulty: 'hard', pieces: ['cut'], screens: ['review-band'], reason: 'The reader first.' },
      { slug: 'the-card', difficulty: 'standard', pieces: ['save'], screens: [], reason: 'on what #cut left.' },
    ]);
    // The section is the delivery's, not a decision across pieces.
    expect(doc.sections.map((s) => s.title)).toEqual(['#cut', '#save']);
  });

  it.each([
    ['Some prose.\n\n- **a** #cut — why', /holds a list and nothing else/],
    ['- #cut — why', /a lot opens with its bold kebab-case slug/],
    ['- **a** #cut', /names what it delivers, then says why/],
    ['- **a** the reader first', /names what it delivers, then says why/],
    ['- **a** #cut — why\n- **a** #save — why', /two lots are named "a"/],
  ])('refuses a section that is not a list of lots: %s', (items, error) => {
    expect(() => planDocOf(parseIntent(lots(items), 'plan.md'), 'plan.md')).toThrow(error);
  });

  it('holds every piece, and every screen with a case to write, to one lot', () => {
    const check = (items: string) => findings(assemble({ ...input, journeyCases: cases, docs: docs(lots(items), null) })[0]).failures;
    expect(check('- **a** #cut @review-band — why\n- **b** #save — why')).toEqual([]);
    expect(check('- **a** #cut — why\n- **b** #cut #ghost — why')).toEqual([
      'planned: specs/features/demo/plan.md:14 lot "b" names #ghost, which is no piece of demo',
      'planned: piece #save is in no lot of "## Delivery" (specs/features/demo/plan.md)',
      'planned: piece #cut is in 2 lots, and it is delivered once — "a", "b"',
      'planned: the journey cases of @review-band is in no lot of "## Delivery" (specs/features/demo/plan.md)',
    ]);
  });

  it('says what a lot still owes, and nothing once its pieces are written', () => {
    const [plan] = assemble({ ...input, journeyCases: cases, docs: docs(lots('- **a** #cut @review-band — why\n- **b** #save — why'), null) });
    expect(plan.doc!.lots.map((lot) => lotLeft(plan, lot))).toEqual([{ sites: 1, tests: 1, cases: 1 }, { sites: 1, tests: 0, cases: 0 }]);
    const [done] = assemble({ todos: [{ ...todo('cut', 'tests/x.test.ts', 3), written: true }], docs: docs(lots('- **a** #cut — why'), null) });
    expect(lotLeft(done, done.doc!.lots[0])).toEqual({ sites: 0, tests: 0, cases: 0 });
  });
});

describe('the approved plan', () => {
  const MD = '# P\n\n## #cut\n\nThe reader cuts.\n\nOn stamps, before the read.\n\n## The snapshot\n\nRegenerated with #cut.\n';
  const base = { sites: [site('cut', 'src/reader.ts', 151)], todos: [todo('cut', 'tests/x.test.ts', 3)], narratives: [{ title: 'The band', kind: 'product' as const, steps: ['decideDue — decides.'] }] };
  const crossedSite = { ...site('cut', 'src/reader.ts', 151), crossedBy: [crossed('The band', 4)] };
  const approvedAs = (input: Partial<PlanInput>, md: string): PlanBaseline => ({ feature: 'demo', base: 'abc12345', approvedOn: '2026-11-13', units: assemble({ ...input, docs: docs(md, null) })[0].snapshot.units });
  const BASELINE = approvedAs({ ...base, sites: [crossedSite] }, MD);
  const now = (input: Partial<PlanInput>, md = MD, baseline: PlanBaseline | null = BASELINE) => assemble({
    ...base, sites: [crossedSite], ...input,
    docs: (feature) => ({ ...docs(md, null)(feature), approved: baseline ? { file: 'specs/features/demo/plan.approved.json', baseline } : null }),
  })[0];
  const says = (md: string, why: string, what = '**The clause was reworded.** ') => md.replace('On stamps, before the read.\n', `On stamps, before the read.\n\nChanged: ${what}${why}\n`);

  it('is as approved while nothing moved — a site on another line is the same site', () => {
    expect(now({}).delta).toEqual([]);
    expect(now({ sites: [{ ...crossedSite, line: 190 }] }).delta).toEqual([]);
    expect(now({}, MD, null).delta).toBeNull();
  });

  it('fails a piece that gained a clause, a test or a reason, until its section says why', () => {
    const reworded = { sites: [{ ...crossedSite, sentence: 'cut calls `latestPriors`.' }] };
    const plan = now(reworded);
    expect(plan.delta).toMatchObject([{
      kind: 'piece', name: '#cut', state: 'changed', reason: 'needed',
      facets: [{ facet: 'sites', added: ['changed src/reader.ts in fn — cut calls `latestPriors`.'], removed: ['changed src/reader.ts in fn — cut happens.'] }],
    }]);
    expect(findings(plan).failures).toEqual(['planned: #cut is not as approved (specs/features/demo/plan.approved.json: sites +1 −1) and its section of specs/features/demo/plan.md holds no "Changed:" — one paragraph saying why, which the reviewer reads before approving again']);
    const told = now(reworded, says(MD, 'no site named the new function.'));
    expect(told.delta!.map((d) => d.reason)).toEqual(['given']);
    expect(findings(told).failures).toEqual([]);
    // A planned test that is gone is a change of the plan; so is a narrative case nobody planned.
    expect(now({ todos: [] }).delta!.map((d) => [d.reason, d.facets[0].removed])).toEqual([['needed', ['unit tests/x.test.ts — cut is tested']]]);
    expect(now({ todos: [...base.todos, { ...todo('cut', 'tests/narratives/band.test.tsx', 9, null, 'narrative'), title: 'one more case' }] }).delta!.map((d) => [d.reason, d.facets[0].added])).toEqual([['needed', ['narrative tests/narratives/band.test.tsx — one more case']]]);
  });

  it('takes the unit tier and the delivery as the tasks stage\'s output, not as changes, until a delivery is approved', () => {
    const belt = { todos: [...base.todos, { ...todo('cut', 'tests/x.test.ts', 9), title: 'one more belt' }], statics: [comment('cut', 'tests/x.test.ts', 4, true), comment('cut', 'tests/narratives/band.test.tsx', 4)] };
    const delivery = `${MD}\n## Delivery\n\n- **a** #cut — why\n`;
    // The approval holds no delivery: the lots, the unit title and the comment on a unit test are no line of the
    // delta. The comment on a narrative's test is one: it changes what a narrative tells.
    expect(now(belt, delivery).delta!.map((d) => [d.name, d.facets.map((f) => [f.facet, f.added])])).toEqual([['#cut', [['comments', ['changes tests/narratives/band.test.tsx — cut in a comment']]]]]);
    // Once a delivery is approved, a test nobody planned is a change like another.
    const approved = approvedAs({ ...base, sites: [crossedSite] }, delivery);
    expect(now(belt, delivery, approved).delta!.map((d) => [d.name, d.reason, d.facets.map((f) => [f.facet, f.added.length])])).toEqual([['#cut', 'needed', [['comments', 2], ['tests', 1]]]]);
  });

  it('asks nothing of a site that went — implemented or dropped — nor of a test written under its title', () => {
    const plan = now({ sites: [], todos: [{ ...base.todos[0], written: true }] });
    expect(plan.delta!.map((d) => [d.name, d.state, d.reason])).toEqual([['#cut', 'changed', 'none']]);
    expect(findings(plan).failures).toEqual([]);
  });

  it('still knows a piece of the approved plan once nothing of it is planned: its section and its lot name it', () => {
    const md = `${MD}\n## #save\n\nSave sends it.\n\n## Delivery\n\n- **a** #cut #save — why\n`;
    const save = site('save', 'src/card.tsx', 2);
    const plan = now({ sites: [save], todos: [] }, says(md, 'the test was folded into the reference case.'), approvedAs({ ...base, sites: [crossedSite, save] }, md));
    expect(plan.pieces.map((x) => x.slug)).toEqual(['save', 'cut']);
    expect(plan.delta!.map((d) => [d.name, d.reason])).toEqual([['#cut', 'given']]);
    expect(findings(plan).failures).toEqual([]);
  });

  it('holds a decision across pieces that reads differently, or is new, to a reason', () => {
    expect(now({}, MD.replace('Regenerated with #cut.', 'Regenerated twice, with #cut.')).delta!.map((d) => [d.kind, d.name, d.reason])).toEqual([['decision', 'The snapshot', 'needed']]);
    expect(now({}, `${MD}\n## Docs made stale\n\nThe README, with #cut.\n\nChanged: the tasks stage found the paragraph.\n`).delta!.map((d) => [d.state, d.reason])).toEqual([['new', 'given']]);
  });

  it('lists a story that moved, and a delivery that moved once one is approved, and asks no reason for them', () => {
    const steps = { narratives: [{ title: 'The band', kind: 'product' as const, steps: ['decideDue — decides.', 'latestPriors — cuts.'] }] };
    const delivery = `${MD}\n## Delivery\n\n- **a** #cut — why\n`;
    expect(now(steps, delivery).delta!.map((d) => [d.kind, d.state, d.reason, d.facets[0].added])).toEqual([['story', 'changed', 'none', ['latestPriors — cuts.']]]);
    expect(now({}, delivery.replace('— why', '— why, and first'), approvedAs({ ...base, sites: [crossedSite] }, delivery)).delta!.map((d) => [d.kind, d.state, d.reason])).toEqual([['delivery', 'changed', 'none']]);
    // The story is still compared once the site that crossed it is code.
    expect(now({ sites: [], narratives: [{ title: 'The band', kind: 'product', steps: [] }] }).delta!.map((d) => d.kind)).toEqual(['piece', 'story']);
  });

  it('lists a question a later stage raises, which asks for no "Changed:" beside it', () => {
    const plan = now({}, MD.replace('On stamps, before the read.\n', 'On stamps, before the read.\n\nTo confirm: **Is the cut made twice?** Once would settle a tie by id.\n'));
    expect(plan.delta).toMatchObject([{ kind: 'piece', name: '#cut', state: 'changed', reason: 'none', facets: [{ facet: 'question', added: ['Is the cut made twice? Once would settle a tie by id.'], removed: [] }] }]);
    expect(findings(plan).failures).toEqual([]);
  });

  it('refuses a "Changed:" that stands on no difference, and one in a plan never approved', () => {
    expect(findings(now({}, says(MD, 'nothing did.'))).failures).toEqual(['planned: specs/features/demo/plan.md:9 #cut says "Changed:" and is as approved (specs/features/demo/plan.approved.json) — the paragraph goes']);
    expect(findings(now({}, says(MD, 'nothing did.'), null)).failures).toEqual(['planned: specs/features/demo/plan.md:9 #cut says "Changed:" and the plan was never approved — there is nothing to have changed from']);
  });

  it('reads what moved off the bold opening, and fails a reason that says no what', () => {
    const reworded = { sites: [{ ...crossedSite, sentence: 'reworded.' }] };
    expect(now(reworded, says(MD, 'No site named it.', '**The clause names `latestPriors`.** ')).doc!.sections[0].changed).toEqual([
      { what: 'The clause names `latestPriors`', why: 'No site named it.', text: '**The clause names `latestPriors`.** No site named it.', claims: [], line: 9 },
    ]);
    expect(findings(now(reworded, says(MD, 'no site named it.', ''))).failures).toEqual([
      'planned: specs/features/demo/plan.md:9 #cut gives a reason and does not say what moved — "Changed: **what moved.** why", one edit a paragraph, so the reviewer knows which change the reason speaks of',
    ]);
  });

  it('gives each edit the lines it names, a rewording\'s other half with them, and fails on a line no edit names', () => {
    const moved = {
      sites: [{ ...crossedSite, sentence: 'cut calls `latestPriors`.' }],
      todos: [...base.todos, { ...todo('cut', 'tests/narratives/band.test.tsx', 9, null, 'narrative'), title: 'lists the latest two' }],
    };
    const two = (claims: string) => says(MD, `No site named it. → code latestPriors\n\nChanged: **One narrative case.** The cut shows on screen.${claims}`, '**The clause names the function.** ');
    const [d] = now(moved, two(' → test "lists the latest"')).delta!;
    expect(d.edits.map((e) => [e.change.what, e.lines.map((l) => `${l.sign} ${l.facet}`), e.unmatched])).toEqual([
      ['The clause names the function', ['− sites', '+ sites'], []],
      ['One narrative case', ['+ tests'], []],
    ]);
    expect(d.unclaimed).toEqual([]);
    expect(findings(now(moved, two(' → test "lists the latest"'))).failures).toEqual([]);
    // The second edit names nothing, then a line that is not there.
    expect(findings(now(moved, two(''))).failures).toEqual([
      'planned: #cut holds 2 "Changed:" and 1 line of its delta that none of them names — an edit ends \' → kind "fragment"; …\' naming its lines:\n      + test: narrative tests/narratives/band.test.tsx — lists the latest two',
    ]);
    expect(findings(now(moved, two(' → test "lists the latest"; code nowhere'))).failures).toEqual(['planned: specs/features/demo/plan.md:11 #cut claims code "nowhere", and no line of its delta is of that kind and holds that fragment']);
    // One edit: every line is its, and it names none.
    expect(now(moved, says(MD, 'two things at once.')).delta![0].edits[0].lines).toHaveLength(3);
    expect(() => now(moved, says(MD, 'why. → the clause'))).toThrow(/"the clause" is no claim/);
  });

  it('lists what the reviewer answers — each edit, each question — under a key that moves when the item is reworded', () => {
    const reworded = { sites: [{ ...crossedSite, sentence: 'reworded.' }] };
    const asked = says(MD, 'No site named it.').replace('## The snapshot', 'To confirm: **Is the cut made twice?** Once settles a tie by id.\n\n## The snapshot');
    const items = reviewItems(now(reworded, asked));
    expect(items.map((i) => [i.unit, i.kind, i.what, i.why])).toEqual([
      ['#cut', 'edit', 'The clause was reworded', 'No site named it.'],
      ['#cut', 'question', 'Is the cut made twice? Once settles a tie by id.', ''],
    ]);
    const again = reviewItems(now({ sites: [{ ...crossedSite, sentence: 'reworded again.' }] }, asked));
    expect(again[0].key).not.toBe(items[0].key);
    expect(again[1].key).toBe(items[1].key);
    expect(reviewItems(now({}))).toEqual([]);
  });

  it('gives a question to answer from the first draft on, a piece\'s and a waiver\'s, with no approval to have moved from', () => {
    const asked = `${MD.replace('## The snapshot', 'To confirm: **Is the cut made twice?** Once settles a tie by id.\n\n## The snapshot')}\n## Rules no test holds\n\n- **owned-once** To confirm: A test would restate the code.\n- **owned-by-none** True by the order of the code.\n`;
    const draft = reviewItems(now({}, asked, null));
    expect(draft.map((i) => [i.unit, i.kind, i.what])).toEqual([
      ['#cut', 'question', 'Is the cut made twice? Once settles a tie by id.'],
      ['no test for owned-once', 'question', 'A test would restate the code.'],
    ]);
    // The same question is the same item once the plan is approved: an answer given on the draft still stands.
    expect(reviewItems(now({}, asked)).map((i) => i.key)).toEqual(draft.map((i) => i.key));
    expect(reviewItems(now({}, MD, null))).toEqual([]);
  });

  describe('a piece planned elsewhere', () => {
    const ELSEWHERE = `${MD}\n## Planned elsewhere\n\n- **the-library** #scale-calls — A call scales with every device; #cut reads it.\n`;
    const there = (statement: string | null, approvedOn: string | null = null) => ({ statement, approvedOn, source: '/work/the-library/specs/features/demo/plan.md', line: 12 });
    const pointing = (md: string, pointed: (repository: string, slug: string) => plan.PointerTarget | null, baseline: PlanBaseline | null = BASELINE) => assemble({
      ...base, sites: [crossedSite],
      docs: (feature) => ({ ...docs(md, null)(feature), approved: baseline ? { file: 'specs/features/demo/plan.approved.json', baseline } : null, pointed }),
    })[0];

    it('is read off its section, with what its repository says of it, and is no piece of this plan', () => {
      const asked: string[] = [];
      const p = pointing(ELSEWHERE, (repository, slug) => { asked.push(`${repository} ${slug}`); return there('A call scales with every device.', '2026-11-20'); });
      expect(p.pointers).toEqual([{ repository: 'the-library', slug: 'scale-calls', reason: 'A call scales with every device; #cut reads it.', line: 15, target: there('A call scales with every device.', '2026-11-20') }]);
      expect(asked).toEqual(['the-library scale-calls']);
      expect(p.pieces.map((x) => x.slug)).toEqual(['cut']);
      expect(findings(p).failures).toEqual([]);
    });

    it('is held by the approval: one added since is listed, and carries its own reason', () => {
      const p = pointing(ELSEWHERE, () => there('A call scales with every device.'));
      expect(p.delta!.map((d) => [d.kind, d.name, d.state, d.reason, d.facets[0].added])).toEqual([
        ['elsewhere', 'Planned elsewhere', 'new', 'none', ['the-library #scale-calls — A call scales with every device; #cut reads it.']],
      ]);
      expect(pointing(ELSEWHERE, () => null, approvedAs({ ...base, sites: [crossedSite] }, ELSEWHERE)).delta).toEqual([]);
    });

    it('fails when that plan holds no such piece, and only says so when no checkout is known', () => {
      expect(findings(pointing(ELSEWHERE, () => there(null))).failures).toEqual([
        'planned: specs/features/demo/plan.md:15 points at the-library\'s demo#scale-calls, and the plan of that repository holds no such piece (/work/the-library/specs/features/demo/plan.md)',
      ]);
      const unchecked = findings(pointing(ELSEWHERE, () => null));
      expect(unchecked.failures).toEqual([]);
      expect(unchecked.info).toContain('planned: specs/features/demo/plan.md:15 points at the-library\'s demo#scale-calls, which is not checked — no checkout of the-library is named under "repositories" of the configuration, or none is there');
    });

    it('may be named by a section and by no lot, and is not planned here too', () => {
      const named = ELSEWHERE.replace('Regenerated with #cut.', 'Regenerated with #cut, after #scale-calls.');
      expect(pointing(named, () => there('It scales.')).unknownRefs).toEqual([]);
      const lot = `${ELSEWHERE}\n## Delivery\n\n- **a** #cut #scale-calls — why\n`;
      expect(pointing(lot, () => there('It scales.')).unknownLotPieces.map((x) => x.slug)).toEqual(['scale-calls']);
      const twice = ELSEWHERE.replace('#scale-calls —', '#cut —');
      expect(findings(pointing(twice, () => there('It scales.'))).failures).toEqual([
        'planned: specs/features/demo/plan.md:15 points at the-library\'s demo#cut, and #cut is a piece of this plan too — a piece is planned here or there, under two tags when both repositories change',
      ]);
    });

    it('refuses a section that is not a list of pointers, and a reason over its budget', () => {
      const section = (items: string) => () => planDocOf(parseIntent(`# P\n\n## Planned elsewhere\n\n${items}\n`, 'plan.md'), 'plan.md');
      expect(section('Some prose.')).toThrow(/plan\.md:5 — "## Planned elsewhere" holds a list and nothing else/);
      expect(section('- #scale-calls — no repository')).toThrow(/names its repository in bold, then its tag, then says what this plan relies on/);
      expect(section('- **the-library** scales the calls')).toThrow(/names its repository in bold, then its tag/);
      expect(section('- **the-library** #scale-calls')).toThrow(/names its repository in bold, then its tag/);
      expect(section('- **the-library** #scale-calls — one\n- **another** #scale-calls — two')).toThrow(/plan\.md:6 — two pieces planned elsewhere are tagged #scale-calls/);
      const long = ELSEWHERE.replace('A call scales with every device; #cut reads it.', 'word '.repeat(BUDGET.pointer + 1).trim());
      expect(findings(pointing(long, () => there('It scales.'))).failures).toEqual([
        `planned: specs/features/demo/plan.md:15 #scale-calls says what the plan relies on in ${BUDGET.pointer + 1} words, and the budget is ${BUDGET.pointer} — what is relied on, and which pieces stand on it: the piece is stated where it is planned`,
      ]);
    });
  });

  it('takes a line one piece lost and another gained, word for word, as a move: no reason, no line of either delta', () => {
    const md = `${MD}\n## #save\n\nSave sends it.\n`;
    const save = site('save', 'src/card.tsx', 2);
    const test = (slug: string) => ({ ...todo(slug, 'tests/narratives/band.test.tsx', 9, null, 'narrative'), title: 'lists the latest two' });
    const approved = approvedAs({ sites: [crossedSite, save], todos: [test('cut')], narratives: base.narratives }, md);
    const plan = now({ sites: [crossedSite, save], todos: [test('save')] }, md, approved);
    expect(plan.moves).toEqual([{ facet: 'tests', text: 'narrative tests/narratives/band.test.tsx — lists the latest two', from: '#cut', to: '#save' }]);
    expect(plan.delta).toEqual([]);
    expect(findings(plan).failures).toEqual([]);
    // Reworded on the way, it is a loss here and a gain there, each with its reason.
    const reworded = now({ sites: [crossedSite, save], todos: [{ ...test('save'), title: 'lists the latest three' }] }, md, approved);
    expect(reworded.moves).toEqual([]);
    expect(reworded.delta!.map((d) => [d.name, d.reason])).toEqual([['#cut', 'needed'], ['#save', 'needed']]);
  });

  it('keeps a "Changed:" out of the piece\'s reason and out of what is approved', () => {
    const plan = now({ sites: [{ ...crossedSite, sentence: 'reworded.' }] }, says(MD, 'reworded for the page.'));
    expect(plan.pieces[0].doc!.why).toEqual([{ kind: 'p', text: 'On stamps, before the read.', line: 7 }]);
    expect(plan.snapshot.units[0].facets.reason).toEqual(['On stamps, before the read.']);
  });
});

describe('a plan being implemented', () => {
  const MD = '# P\n\n## #cut\n\nThe reader cuts.\n\n## #save\n\nSave sends it.\n\n## Delivery\n\n- **a** #cut — first\n- **b** #save — then\n';
  const cut = site('cut', 'src/reader.ts', 151);
  const save = site('save', 'src/card.tsx', 2);
  const goes = comment('cut', 'tests/x.test.ts', 4, true);
  const planned = { sites: [cut, save], statics: [goes], todos: [todo('cut', 'tests/x.test.ts', 9)] };
  const BASELINE: PlanBaseline = { feature: 'demo', base: 'abc12345', approvedOn: '2026-11-13', units: assemble({ ...planned, docs: docs(MD, null) })[0].snapshot.units };
  const commit = (sha: string, pieces: string[], over: Partial<PieceCommit> = {}): PieceCommit => ({ sha, subject: `${pieces.join(' ')} lands`, pieces, sinceApproval: true, files: [], untagged: [], deleted: [], planned: [], ...over });
  const now = (input: Partial<PlanInput>, commits: PieceCommit[] = [], md = MD) => assemble({
    ...planned, ...input,
    docs: (feature) => ({ ...docs(md, null)(feature), approved: { file: 'specs/features/demo/plan.approved.json', baseline: BASELINE }, commits: { list: commits, baseKnown: true } }),
  })[0];
  const written = [{ ...todo('cut', 'tests/x.test.ts', 9), written: true }];
  const built = { sites: [save], statics: [], todos: written };

  it('keeps a place that became code as a built line of its piece: the plan is as approved, and the lot is delivered', () => {
    const plan = now(built, [commit('1111111122', ['cut'])]);
    expect(plan.pieces.find((x) => x.slug === 'cut')!.built).toEqual({ sites: ['changed src/reader.ts in fn — cut happens.'], comments: ['removes tests/x.test.ts — cut in a comment'] });
    expect(plan.delta).toEqual([]);
    expect(plan.doc!.lots.map((lot) => lotLeft(plan, lot))).toEqual([{ sites: 0, tests: 0, cases: 0 }, { sites: 1, tests: 0, cases: 0 }]);
    expect(plan.pieces.find((x) => x.slug === 'cut')!.commits.map((c) => c.sha)).toEqual(['1111111122']);
    expect(findings(plan).failures).toEqual([]);
    // Approved again, the built lines are still the plan's.
    expect(plan.snapshot.units.find((u) => u.name === '#cut')!.facets.sites).toEqual(['changed src/reader.ts in fn — cut happens.']);
  });

  it('tells a reworded place from a built one, and a line another piece took from one that became code', () => {
    const reworded = now({ sites: [{ ...cut, sentence: 'cut reads less.' }, save] });
    expect(reworded.pieces.find((x) => x.slug === 'cut')!.built.sites).toEqual([]);
    expect(reworded.delta!.map((d) => [d.name, d.facets.map((f) => [f.facet, f.added.length, f.removed.length])])).toEqual([['#cut', [['sites', 1, 1]]]]);
    const moved = now({ statics: [{ ...goes, slug: 'save' }] });
    expect(moved.pieces.find((x) => x.slug === 'cut')!.built.comments).toEqual([]);
    expect(moved.moves).toEqual([{ facet: 'comments', text: 'removes tests/x.test.ts — cut in a comment', from: '#cut', to: '#save' }]);
  });

  it('fails a delivered lot whose piece no commit names, and a commit that names no piece of the plan', () => {
    expect(findings(now(built)).failures).toEqual(['planned: lot "a" is delivered and no commit names #cut — the message of a piece\'s commit ends with the line "Piece: demo#<piece>"']);
    expect(findings(now(built, [commit('1111111122', ['cut', 'ghost'])])).failures).toEqual(['planned: the commit 11111111 names #ghost, which is no piece of demo — "Piece: demo#<piece>" names a piece of the plan']);
  });

  it('fails a test a commit added under no planned title: it is tagged and explained, or it goes', () => {
    const plan = now(built, [commit('1111111122', ['cut'], { untagged: [{ file: 'tests/x.test.ts', title: 'one more belt' }] })]);
    expect(findings(plan).failures).toEqual(['planned: tests/x.test.ts — "one more belt" was added by 11111111 (#cut) under no planned title — a test beyond the plan is titled "demo#<piece>: …" and its piece says why in a "Changed:", or it goes']);
    // Tagged, it is a line of the piece's delta, and asks for its reason there.
    const tagged = now({ ...built, todos: [...written, { ...todo('cut', 'tests/x.test.ts', 12), title: 'one more belt', written: true }] }, [commit('1111111122', ['cut'])]);
    expect(tagged.delta!.map((d) => [d.name, d.reason, d.facets[0].added])).toEqual([['#cut', 'needed', ['unit tests/x.test.ts — one more belt']]]);
  });

  it('makes a line of the piece\'s delta of a test deleted with nothing planned on it and of a file no place names', () => {
    const beyond = commit('1111111122', ['cut'], {
      files: [{ file: 'src/reader.ts', added: 4, removed: 1, line: 151 }, { file: 'src/other.ts', added: 2, removed: 0, line: 7 }, { file: 'tests/y.test.ts', added: 1, removed: 1, line: 3 }],
      deleted: [{ file: 'tests/x.test.ts', title: 'the old cut' }],
    });
    const plan = now(built, [beyond]);
    expect(plan.delta).toMatchObject([{ name: '#cut', reason: 'needed', facets: [{ facet: 'unplanned', added: ['test tests/x.test.ts — deleted, and the plan removed no such test: the old cut', 'file src/other.ts — changed, and no place of the plan names it'], removed: [] }] }]);
    expect(findings(plan).failures).toHaveLength(1);
    const two = MD.replace('The reader cuts.\n', 'The reader cuts.\n\nChanged: **The old cut test goes.** The reference case holds it. → test "the old cut"\n\nChanged: **`other` gains the field.** Its literal is typed. → code src/other.ts\n');
    const told = now(built, [beyond], two);
    expect(told.delta![0].edits.map((e) => e.lines.map((l) => l.text.split(' — ')[0]))).toEqual([['test tests/x.test.ts'], ['file src/other.ts']]);
    expect(findings(told).failures).toEqual([]);
    expect(reviewItems(told).map((i) => i.what)).toEqual(['The old cut test goes', '`other` gains the field']);
    // A commit the approval already covers is not read.
    expect(now(built, [{ ...beyond, sinceApproval: false }]).delta).toEqual([]);
  });

  it('tells a place taken off and not built: its file gained no line from the piece\'s commits', () => {
    const touched = (added: number) => commit('1111111122', ['cut'], { files: [{ file: 'src/reader.ts', added, removed: 1, line: 151 }, { file: 'tests/x.test.ts', added: 0, removed: 3, line: 4 }] });
    const dropped = now(built, [touched(0)]);
    // The removal of a test adds nothing by design, and is no such line.
    expect(dropped.delta).toMatchObject([{ name: '#cut', reason: 'needed', facets: [{ facet: 'unplanned', added: ['place src/reader.ts — planned there, and the piece\'s commits added no line to the file: cut happens.'] }] }]);
    expect(now(built, [touched(6)]).delta).toEqual([]);
    // A later commit of the piece that writes there settles it.
    expect(now(built, [touched(0), commit('2222222233', ['cut'], { files: [{ file: 'src/reader.ts', added: 2, removed: 0, line: 151 }] })]).delta).toEqual([]);
  });

  it('reads a note as what a piece was built with: listed when new, asking nothing, kept by the approval', () => {
    const noted = MD.replace('The reader cuts.\n', 'The reader cuts.\n\nNote: **The bounds read null when no number is offered.** #save shows that as one position.\n');
    const plan = now(built, [commit('1111111122', ['cut'])], noted);
    const cutPiece = plan.pieces.find((x) => x.slug === 'cut')!;
    expect(cutPiece.doc!.notes).toMatchObject([{ what: 'The bounds read null when no number is offered', detail: '#save shows that as one position.' }]);
    expect(cutPiece.doc!.why).toEqual([]);
    expect(plan.delta).toMatchObject([{ name: '#cut', reason: 'none', facets: [{ facet: 'notes', added: ['**The bounds read null when no number is offered.** #save shows that as one position.'], removed: [] }] }]);
    expect(reviewItems(plan)).toEqual([]);
    expect(findings(plan).failures).toEqual([]);
    expect(plan.snapshot.units.find((u) => u.name === '#cut')!.facets.notes).toHaveLength(1);
    // Beside an edit, a note is none of the edit's lines.
    const both = now({ ...built, todos: [...written, { ...todo('cut', 'tests/x.test.ts', 12), title: 'one more belt', written: true }] }, [commit('1111111122', ['cut'])], noted.replace('Note: ', 'Changed: **One more test.** No title held the belt.\n\nNote: '));
    expect(both.delta![0].edits.map((e) => e.lines.map((l) => l.facet))).toEqual([['tests']]);
    expect(findings(both).failures).toEqual([]);
    // A note says its point in bold.
    expect(findings(now(built, [commit('1111111122', ['cut'])], MD.replace('The reader cuts.\n', 'The reader cuts.\n\nNote: the bounds read null.\n'))).failures).toEqual([expect.stringContaining('holds a note with no point')]);
  });

  it('keeps a journey case that was written as a case of the plan', () => {
    const theCase = { feature: 'demo', journey: 'Change the rule', screen: 'review-rule', title: 'the row reads 2', file: 'tests/e2e/journeys/a.journey.spec.ts', line: 9, column: 5 };
    const md = MD.replace('#cut — first', '#cut @review-rule — first');
    const approved: PlanBaseline = { ...BASELINE, units: assemble({ ...planned, journeyCases: [theCase], docs: docs(md, null) })[0].snapshot.units };
    const plan = assemble({ ...built, docs: (feature) => ({ ...docs(md, null)(feature), approved: { file: 'x', baseline: approved }, commits: { list: [commit('1111111122', ['cut'])], baseKnown: true } }) })[0];
    expect(plan.builtCases).toEqual(['Change the rule · review-rule — the row reads 2']);
    expect(plan.delta).toEqual([]);
  });
});

describe('the tests a commit added and deleted', () => {
  const file = 'tests/x.test.ts';
  const wrap = (...lines: string[]) => `describe('x', () => {\n${lines.join('\n')}\n});\n`;

  it('counts a deletion and a change the plan said, and nothing else of them', () => {
    const before = wrap(`// ${TAG}.remove demo#cut held by the reference case`, `it('old cut', () => {});`, `// ${TAG} demo#cut retitled to the general case`, `it('reads the default before 069', () => {});`, `it('stays', () => {});`);
    const after = wrap(`it('a figure missing reads its default', () => {});`, `it('stays', () => {});`);
    expect(testChanges('demo', file, before, after)).toMatchObject({
      planned: [{ title: 'old cut', removes: true, text: 'held by the reference case' }, { title: 'reads the default before 069', removes: false, text: 'retitled to the general case' }],
      deleted: [], untagged: [],
    });
  });

  it('reports a test deleted with nothing planned on it and a test added under no tag', () => {
    const before = wrap(`it('stays', () => {});`, `it('goes quietly', () => {});`, `it.todo('demo#cut: lists two');`);
    const after = wrap(`it('stays', () => {});`, `it('demo#cut: lists two', () => {});`, `it('one more belt', () => {});`);
    expect(testChanges('demo', file, before, after)).toMatchObject({ planned: [], deleted: ['goes quietly'], untagged: ['one more belt'] });
  });

  it('takes an existing test extended into a planned title as no deletion', () => {
    const before = wrap(`it('saves three figures', () => {});`, `// ${TAG} demo#cut the test above, extended: no case is added`, `it.todo('demo#cut: saves four figures');`);
    const after = wrap(`it('demo#cut: saves four figures', () => {});`);
    expect(testChanges('demo', file, before, after)).toMatchObject({ planned: [], deleted: [], untagged: [] });
  });
});

describe('overSentenceBudget', () => {
  const long = (n: number) => Array.from({ length: n }, () => 'word').join(' ');

  it('passes a sentence at the budget, its bold marks not counted as words', () => {
    expect(overSentenceBudget(`**${long(3)}** ${long(SENTENCE_BUDGET.words - 3)}`)).toEqual([]);
    expect(overSentenceBudget(long(5))).toEqual([]);
  });

  it('names each budget a sentence is over: one word too many, a second bold', () => {
    expect(overSentenceBudget(long(SENTENCE_BUDGET.words + 1)).map((f) => f.split(' — ')[0])).toEqual([
      `tells its step in ${SENTENCE_BUDGET.words + 1} words, and the budget is ${SENTENCE_BUDGET.words}`,
    ]);
    expect(overSentenceBudget('**one** rule and **another**').map((f) => f.split(' — ')[0])).toEqual([
      `holds 2 bolds, and a sentence has ${SENTENCE_BUDGET.bolds} at most`,
    ]);
  });
});
