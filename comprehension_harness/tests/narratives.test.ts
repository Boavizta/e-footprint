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

function example(hasWatch = true) {
  const doc = JSON.parse(readFileSync(join(SHOP, 'source-index.json'), 'utf8')) as SourceIndexDocument;
  doc.files[FILE].sites.find((s) => s.fn === 'charge')!.hasWatch = hasWatch;
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
  it('links missing and additional steps to their calls with the narration as a plain-text tooltip', () => {
    const { index, stories: allStories } = example();
    const stories = allStories.filter((s) => s.file === 'tests/test_checkout.py');
    const variant = stories.find((s) => s.test === 'test_builds_then_pays')!;
    variant.hits = variant.hits.filter((h) => h.site.fn !== 'charge');
    variant.hits.find((h) => h.site.fn === 'Basket.total')!.sentence = 'The "basket" **adds <its> & lines** before `with_tax`.';
    const narratives = deriveNarratives(stories, index);
    const html = renderNarrativePage(narratives[0], stories, narratives, index, { entries: [], byKey: new Map() });
    const summary = html.match(/<summary>Builds then pays[^]*?<\/summary>/)![0];
    expect(summary).toContain('Not reached: <a class="src" title="The amount is charged."');
    expect(summary).toContain('shop/checkout.py:23:5"');
    expect(summary).toContain('shop/checkout.py#L23:5"');
    expect(summary).toContain('>charge</a>');
    expect(summary).toContain('Additional step reached: <a class="src" title="The &quot;basket&quot; adds &lt;its&gt; &amp; lines before with_tax."');
    expect(summary).toContain('shop/checkout.py:11:9"');
    expect(summary).toContain('shop/checkout.py#L11:9"');
    expect(summary).toContain('>Basket.total</a>');
    expect(summary).not.toContain('beyond the canonical');
  });

  it('gives a step without a declared watch the full text width and keeps its source link', () => {
    const { index, stories } = example(false);
    const narratives = deriveNarratives(stories, index);
    const html = renderNarrativePage(narratives.find((n) => n.title === TITLE)!, stories, narratives, index, { entries: [], byKey: new Map() });
    const rows = html.match(/<div class="step[^]*?\n  <\/div>/g)!;
    expect(rows.length).toBeGreaterThan(1);
    for (const row of rows) {
      expect(row).toContain('without-watch');
      expect(row).toContain('shop/checkout.py:23');
      expect(row).not.toContain('class="watch"');
      expect(row).not.toContain('Stop at');
      expect(row).not.toContain('no watch');
      expect(row).not.toContain(' ms');
    }
  });

  it.each([null, {}, [], { amount: 0 }].map((watch) => ({ watch })))('keeps the watch panel when a declared watch returns $watch', ({ watch }) => {
    const { index, stories } = example();
    for (const story of stories) for (const hit of story.hits) hit.watch = watch;
    const narratives = deriveNarratives(stories, index);
    const html = renderNarrativePage(narratives.find((n) => n.title === TITLE)!, stories, narratives, index, { entries: [], byKey: new Map() });
    const rows = html.match(/<div class="step[^]*?\n  <\/div>/g)!;
    for (const row of rows) {
      expect(row).not.toContain('without-watch');
      expect(row).toContain('class="watch"');
      expect(row).toContain('Stop at');
    }
  });

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
