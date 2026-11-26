import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { JsonSource, checkSourceIndex } from '../json-source';
import { SourceIndex } from '../source-index';
import { deriveNarratives, derivePlans, narrativePlanIssues, renderNarrativePage, renderPlanPage } from '../render';
import type { SourceIndexDocument, Story } from '../stack';

const SHOP = join(dirname(fileURLToPath(import.meta.url)), 'fixtures/shop');
const FILE = 'shop/checkout.py';
const TEST = 'tests/test_checkout.py';

function example() {
  const doc = JSON.parse(readFileSync(join(SHOP, 'source-index.json'), 'utf8')) as SourceIndexDocument;
  doc.narratives = [{ file: TEST, title: 'The customer receives a refund', summary: 'The card receives the refunded amount.',
    line: 5, firstTest: 'gift-cards#refund-to-card: A refund goes to the card',
    intended: { test: 'gift-cards#refund-to-card: A refund goes to the card', steps: ['refund:read', 'refund:write'], planned: true } }];
  doc.files[FILE].sites.push(
    { kind: 'step', fn: 'refund', line: 27, column: 5, sentence: 'The amount is **read**.', narration: { id: 'refund:read', planned: true, changes: [] } },
    { kind: 'step', fn: 'refund', line: 29, column: 5, sentence: 'The card **receives the refund**.', narration: { id: 'refund:write', planned: true, changes: ['gift-cards#refund-to-card:refund'] } },
  );
  const build = () => {
    const index = new SourceIndex(new JsonSource(checkSourceIndex(doc, 'the example'), (f) => !f.startsWith('tests/')));
    return { index, narratives: deriveNarratives([], index) };
  };
  return { doc, build, ...build() };
}

describe('intended narrative sequences', () => {
  it('shows documentation scope on intended narrative and plan pages before any run exists', () => {
    const { doc, build } = example();
    doc.narratives[0].scope = 'doc';
    const { index, narratives } = build();
    const [n] = narratives;
    expect(n.scope).toBe('doc');
    expect(n.canonical).toBeNull();
    const html = renderNarrativePage(n, [], narratives, index, { entries: [], byKey: new Map() });
    expect(html).toContain('data-narrative-scope="doc">doc</span>');
    expect(html).toContain('intended order, not an observed run');
    const [plan] = derivePlans([], narratives, index, { statics: [], todos: [], journeyCases: [] });
    expect(renderPlanPage(plan, [], narratives, index)).toContain('data-narrative-scope="doc">doc</span>');
  });

  it('derives a source-only narrative without inventing observed steps, crossings or ownership', () => {
    const { index, narratives } = example();
    expect(narratives).toHaveLength(1);
    const [n] = narratives;
    expect(n.canonical).toBeNull();
    expect(n.steps).toEqual([]);
    expect([...n.siteIds]).toEqual([]);
    expect(n.intended!.sites.map((s) => s.id)).toEqual(['refund:read', 'refund:write']);
    expect(narrativePlanIssues(narratives, index)).toEqual([]);
    const html = renderNarrativePage(n, [], narratives, index, { entries: [], byKey: new Map() });
    expect(html).toContain('intended order, not an observed run');
    expect(html).toContain('source declarations (intended, not observed)');
    expect(html).toContain('../plans/gift-cards.html#change-gift-cards%23refund-to-card%3Arefund');
    expect(html.indexOf('The amount is <b>read</b>')).toBeLessThan(html.indexOf('The card <b>receives the refund</b>'));
    expect(html).not.toContain('no story yet for its canonical');
  });

  it('draws planned sequences on the feature plan and holds their order in its approval snapshot', () => {
    const { index, narratives } = example();
    const [plan] = derivePlans([], narratives, index, { statics: [], todos: [], journeyCases: [] });
    const html = renderPlanPage(plan, [], narratives, index);
    expect(html).toContain('Planned narrative sequences');
    expect(html).toContain('href="#change-gift-cards%23refund-to-card%3Arefund" title="Linked change place"');
    expect(html).toContain('id="change-gift-cards#refund-to-card:refund"');
    expect(plan.snapshot.units.find((u) => u.name === 'Intended narrative — The customer receives a refund')!.facets.steps).toEqual([
      'refund:read — The amount is **read**.', 'refund:write — The card **receives the refund**.',
    ]);
    expect(plan.pieces.flatMap((p) => p.sites).every((s) => s.crossedBy.length === 0)).toBe(true);
  });

  it.each([
    ['missing declaration', (doc: SourceIndexDocument) => { doc.narratives[0].intended!.steps.push('refund:missing'); }, 'no declaration for intended step refund:missing'],
    ['broken change link', (doc: SourceIndexDocument) => { doc.files[FILE].sites.at(-1)!.narration!.changes = ['gift-cards#refund-to-card:missing']; }, 'links to unknown change place'],
    ['orphan step', (doc: SourceIndexDocument) => { doc.narratives[0].intended!.steps.pop(); }, 'named by no reference sequence'],
    ['duplicate step id', (doc: SourceIndexDocument) => { doc.files[FILE].sites.at(-1)!.narration!.id = 'refund:read'; }, 'duplicate narrative step refund:read'],
  ] as const)('rejects a %s', (_, edit, message) => {
    const { doc, build } = example();
    edit(doc);
    const { narratives, index } = build();
    expect(narrativePlanIssues(narratives, index).join('\n')).toContain(message);
  });

  it('validates promoted steps against the reference run and keeps their stable identities', () => {
    const { doc, build } = example();
    doc.narratives[0].intended!.planned = false;
    for (const site of doc.files[FILE].sites) if (site.narration) site.narration = { ...site.narration, planned: false, changes: [] };
    const { index } = build();
    const sites = index.namedSteps();
    const story: Story = { file: TEST, test: doc.narratives[0].intended!.test, narrative: { title: doc.narratives[0].title, kind: 'product' },
      canonical: true, order: 1, state: 'passed', durationMs: 1,
      hits: sites.map((site) => ({ kind: 'step', step: site.id, sentence: site.sentence!, site, watch: null, stack: [], atMs: 1 })) };
    const narratives = deriveNarratives([story], index);
    expect(narratives[0].steps.map((s) => s.id)).toEqual(['refund:read', 'refund:write']);
    expect(narrativePlanIssues(narratives, index)).toEqual([]);
    delete story.hits[0].step;
    expect(narrativePlanIssues(deriveNarratives([story], index), index).join('\n')).toContain('reference sequence differs');
    story.hits[0].step = 'refund:read';
    story.hits.reverse();
    expect(narrativePlanIssues(deriveNarratives([story], index), index).join('\n')).toContain('reference sequence differs');
    story.hits = [];
    expect(narrativePlanIssues(deriveNarratives([story], index), index).join('\n')).toContain('no run');
  });

  it('does not shift the identity of existing observed steps when planning a step in their function', () => {
    const { doc, build } = example();
    doc.files[FILE].sites.push({ kind: 'step', fn: 'charge', line: 21, column: 5, sentence: 'The charge is checked.',
      narration: { id: 'charge:check', planned: true, changes: [] } });
    const { index } = build();
    expect(index.sites(FILE).get(23)!.id).toBe(`${FILE}#charge#1`);
    expect(index.sites(FILE).get(21)!.ordinal).toBe(0);
  });

  it('rejects malformed sequence and step metadata from a stack', () => {
    const { doc } = example();
    doc.narratives[0].intended!.steps.push('refund:read');
    expect(() => checkSourceIndex(doc, 'the example')).toThrow('invalid intended reference sequence');
    doc.narratives[0].intended!.steps.pop();
    doc.files[FILE].sites.at(-1)!.narration!.changes = null as never;
    expect(() => checkSourceIndex(doc, 'the example')).toThrow('invalid narrative step');
  });
});
