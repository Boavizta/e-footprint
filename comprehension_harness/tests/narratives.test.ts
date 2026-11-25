import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { JsonSource, checkSourceIndex } from '../json-source';
import { deriveNarratives, derivePlans, renderNarrativePage } from '../render';
import { SourceIndex } from '../source-index';
import type { SourceIndexDocument, Story, StoryHit } from '../stack';

const SHOP = join(dirname(fileURLToPath(import.meta.url)), 'fixtures/shop');
const FILE = 'shop/checkout.py';
const TITLE = 'The customer pays a basket';

function example() {
  const doc = JSON.parse(readFileSync(join(SHOP, 'source-index.json'), 'utf8')) as SourceIndexDocument;
  doc.narratives.push({ file: 'tests/test_basket.py', title: 'A basket is assembled', line: 1, summary: '', firstTest: 'test_builds' });
  const source = new JsonSource(checkSourceIndex(doc, 'the example'), (f) => !f.startsWith('tests/'));
  const index = new SourceIndex(source);
  const hit = (line: number, phase: StoryHit['phase'], file = FILE): StoryHit => {
    const site = source.sites(file).find((s) => s.line === line)!;
    return { kind: site.kind, sentence: site.sentence!, site, phase, atMs: 1, stack: [], watch: null };
  };
  const story = (test: string, hits: StoryHit[]): Story => ({ file: 'tests/test_checkout.py', test, hits,
    narrative: { title: TITLE, kind: 'product' }, canonical: false, order: 1, state: 'passed', durationMs: 2 });
  const mechanism: Story = { ...story('test_builds', [hit(23, 'setup'), hit(11, undefined), hit(8, 'teardown', 'shop/pricing.py')]), file: 'tests/test_basket.py',
    narrative: { title: 'A basket is assembled', kind: 'mechanism' } };
  const canonical = story('test_charges_the_total_with_tax', [
    hit(16, 'setup'), hit(11, 'setup'), hit(18, 'setup'), hit(28, 'setup'),
    hit(16, 'call'), hit(18, 'call'), hit(23, 'call'),
    hit(16, 'teardown'), hit(8, 'teardown', 'shop/pricing.py'),
  ]);
  canonical.capped = [{ file: FILE, line: 11, phase: 'setup', kept: 50, omitted: 10 }];
  const variant = story('test_builds_then_pays', [hit(8, 'setup', 'shop/pricing.py'), hit(16, 'call'), hit(11, 'call'), hit(23, 'call')]);
  return { index, stories: [mechanism, canonical, variant], canonical };
}

describe('narratives scoped to the test body', () => {
  it('excludes fixture steps, ownership and caps while keeping explicit construction and the original trace', () => {
    const { index, stories, canonical } = example();
    const narratives = deriveNarratives(stories, index);
    const narrative = narratives.find((n) => n.title === TITLE)!;
    expect(narrative.canonical!.hits.map((h) => h.site.fn)).toEqual(['pay', 'pay', 'charge']);
    expect(narrative.canonical!.capped).toEqual([]);
    expect(narrative.steps.map((s) => s.site.fn)).toEqual(['charge']);
    expect(narrative.siteIds.size).toBe(1);
    expect(narrative.variants[0].hits.map((h) => h.site.fn)).toEqual(['pay', 'Basket.total', 'charge']);
    expect(canonical.hits).toHaveLength(9);
    expect(canonical.capped).toHaveLength(1);

    const html = renderNarrativePage(narrative, stories, narratives, index, { entries: [], byKey: new Map() });
    const main = html.split('<section class="narr"')[1].split('</section>')[0];
    expect(main).toContain('1 event');
    expect(main).toContain('1 narrative step hit across 1 distinct step');
    expect(main).not.toContain('data-rides-on');
    expect(html).toContain('data-rides-on="a-basket-is-assembled"');
    expect(html).not.toContain('The price');
  });

  it('keeps setup as plan evidence and locates test-body planned hits in the filtered narrative', () => {
    const { index, stories, canonical } = example();
    stories.push({ ...canonical, narrative: null });
    const plans = derivePlans(stories, deriveNarratives(stories, index), index, { statics: [], todos: [], journeyCases: [] });
    const sites = plans.flatMap((p) => p.pieces.flatMap((piece) => piece.sites));
    const setup = sites.find((s) => s.line === 28)!;
    const body = sites.find((s) => s.line === 18)!;
    expect(setup.reachedBy.flatMap((r) => r.titles)).toContain('test_charges_the_total_with_tax');
    expect(setup.crossedBy).toEqual([]);
    expect(body.crossedBy).toEqual([{ narrative: TITLE, at: 1, step: null }]);
  });
});
