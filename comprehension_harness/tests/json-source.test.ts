/**
 * json-source — the source index read from a document (`../json-source.ts`), on an index written by hand for a
 * project of three Python files (`fixtures/shop/`).
 *
 * What is worth fencing: that the example is true to its source, since a stack's own index is written to
 * conform to it; that a site read from a document gets the same identity as one read by a compiler; that a
 * name is found in the order the contract gives, and the reason said when it is not; and that a document of
 * another shape is refused, never read in part.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { JsonSource, checkSourceIndex, openJsonSource } from '../json-source';
import { SourceIndex } from '../source-index';
import type { RawSite, SourceIndexDocument, Story } from '../stack';

const SHOP = join(dirname(fileURLToPath(import.meta.url)), 'fixtures/shop');
const INDEX = join(SHOP, 'source-index.json');
const document = () => JSON.parse(readFileSync(INDEX, 'utf8')) as SourceIndexDocument;
const isSource = (file: string) => !file.startsWith('tests/');
const reader = () => new JsonSource(checkSourceIndex(document(), 'the example'), isSource);
const CHECKOUT = 'shop/checkout.py';
const PRICING = 'shop/pricing.py';
const siteAt = (file: string, line: number): RawSite => reader().sites(file).find((s) => s.line === line)!;
const at = (file: string, line: number, column: number) => ({ file, line, column });

describe('the example index', () => {
  it('says where each thing is in the example source, line and column', () => {
    const wrong: string[] = [];
    for (const [file, tables] of Object.entries(document().files)) {
      const lines = readFileSync(join(SHOP, file), 'utf8').split('\n');
      const starts = (x: { line: number; column: number }, word: string, what: string) => {
        if (!(lines[x.line - 1] ?? '').slice(x.column - 1).startsWith(word)) wrong.push(`${file}:${x.line}:${x.column} is not ${what} "${word}"`);
      };
      for (const s of tables.sites) starts(s, `${s.kind === 'step' ? 'narrate' : s.kind}(`, 'the call');
      for (const f of tables.functions) starts(f, f.fn.split('.').pop()!, 'the function');
      for (const d of [...tables.declarations, ...tables.locals]) starts(d, d.name, 'the declaration of');
      for (const u of tables.uses) starts(u, u.name, 'a use of');
      for (const x of [...tables.imports, ...tables.uses]) {
        const declared = readFileSync(join(SHOP, x.at.file), 'utf8').split('\n')[x.at.line - 1] ?? '';
        if (!declared.slice(x.at.column - 1).startsWith(x.name)) wrong.push(`${file}: "${x.name}" is not declared at ${x.at.file}:${x.at.line}:${x.at.column}`);
      }
    }
    expect(wrong).toEqual([]);
  });
});

describe('sites read from a document', () => {
  it('get the identity every stack\'s sites get: the function and an ordinal, or the piece for a planned call', () => {
    const index = new SourceIndex(reader());
    expect([...index.sites(CHECKOUT).values()].map((s) => [s.line, s.kind, s.id])).toEqual([
      [18, 'planned', 'planned:gift-cards#deduct-the-card@shop/checkout.py:18'],
      [28, 'planned', 'planned:gift-cards#refund-to-card@shop/checkout.py:28'],
      [11, 'step', 'shop/checkout.py#Basket.total#1'],
      [16, 'event', 'shop/checkout.py#pay#1'],
      [23, 'step', 'shop/checkout.py#charge#1'],
    ]);
    expect(index.plannedSites().map((s) => [s.planned!.slug, s.planned!.change, s.planned!.signature, s.planned!.sentence])).toEqual([
      ['deduct-the-card', 'changed', null, 'The amount due **loses the card\'s balance**.'],
      ['refund-to-card', 'added', 'def refund(amount):', 'A refund goes back to the card first.'],
    ]);
    expect(index.sitesUnder(['shop/']).map((s) => s.id)).toEqual(['shop/checkout.py#Basket.total#1', 'shop/checkout.py#charge#1', 'shop/pricing.py#with_tax#1']);
  });

  it('find again, by its sentence, a site a run recorded two lines lower', () => {
    const index = new SourceIndex(reader());
    const story = { hits: [{ kind: 'step', sentence: 'The amount **is charged**.', site: { file: CHECKOUT, line: 25, column: 5, fn: 'charge' } }] } as unknown as Story;
    expect(index.realign([story])).toBe(1);
    expect(index.identity(story.hits[0].site).id).toBe('shop/checkout.py#charge#1');
  });

  it('are the product\'s when their file is no test file, and a file the document does not hold is refused', () => {
    expect(reader().sourceFiles()).toEqual([PRICING, CHECKOUT]);
    expect(reader().siteFiles()).toEqual([PRICING, CHECKOUT]);
    expect(reader().sourceFile('pricing.py')).toBe(PRICING);
    expect(reader().sourceFile('shop/checkout.py')).toBe(CHECKOUT);
    expect(reader().sourceFile('test_checkout.py')).toBeNull();
    expect(() => reader().sites('shop/missing.py')).toThrow(/shop\/missing\.py is not in the source index/);
  });
});

describe('a narrative\'s declaration', () => {
  it('is the document\'s: its line, its summary, its first test', () => {
    expect(reader().narrativeTestFiles()).toEqual(['tests/test_checkout.py']);
    expect(reader().declaration('tests/test_checkout.py', 'The customer pays a basket')).toEqual({ line: 5, summary: 'The total is the lines\' sum with the tax, and that is what is charged.', firstTest: 'test_charges_the_total_with_tax' });
    expect(() => reader().declaration('tests/test_checkout.py', 'Another')).toThrow(/declares no narrative titled "Another"/);
  });
});

describe('a name of a sentence', () => {
  const total = () => siteAt(CHECKOUT, 11);

  it('is found in order: an import of the file, a local of the functions around the call, the file, the source', () => {
    expect(reader().resolve(total(), 'with_tax')).toEqual({ linked: true, rule: 1, at: at(PRICING, 6, 5) });
    expect(reader().resolve(total(), 'subtotal')).toEqual({ linked: true, rule: '1b', at: at(CHECKOUT, 10, 9) });
    expect(reader().resolve(total(), 'charge')).toEqual({ linked: true, rule: 2, at: at(CHECKOUT, 22, 5) });
    expect(reader().resolve(siteAt(PRICING, 8), 'rate')).toEqual({ linked: true, rule: '1b', at: at(PRICING, 7, 5) });
    expect(reader().resolve(siteAt(PRICING, 8), 'refund')).toEqual({ linked: true, rule: 3, at: at(CHECKOUT, 27, 5) });
  });

  it('stays plain with the reason: a local of another function, a name declared nowhere, no identifier', () => {
    expect(reader().resolve(total(), 'basket')).toEqual({ linked: false, reason: 'a local of pay, not of Basket.total (shop/checkout.py:15)' });
    expect(reader().resolve(total(), 'nowhere')).toEqual({ linked: false, reason: 'no declaration of that name in the source' });
    expect(reader().resolve(total(), 'basket.total')).toEqual({ linked: false, reason: 'not an identifier' });
  });

  it('is found with no site in the files named beside it, else unique across the source, else near a place', () => {
    expect(reader().resolveUnscoped('charge', [CHECKOUT])).toEqual(at(CHECKOUT, 22, 5));
    expect(reader().resolveUnscoped('with_tax', [CHECKOUT])).toEqual(at(PRICING, 6, 5));
    expect(reader().resolveUnscoped('amount', [CHECKOUT])).toBeNull();
    expect(reader().resolveNear('amount', [{ file: CHECKOUT, line: 23 }])).toEqual(at(CHECKOUT, 22, 12));
    expect(reader().resolveNear('amount', [{ file: CHECKOUT, line: 18 }])).toEqual(at(CHECKOUT, 17, 5));
  });
});

describe('where a function uses a symbol', () => {
  it('is the first reference in it the document places at that declaration', () => {
    expect(reader().useSite(siteAt(CHECKOUT, 11), 'with_tax', at(PRICING, 6, 5))).toEqual(at(CHECKOUT, 12, 28));
    expect(reader().useIn(CHECKOUT, 'pay', 'charge', at(CHECKOUT, 22, 5))).toEqual(at(CHECKOUT, 19, 12));
    expect(reader().useIn(CHECKOUT, 'pay', 'with_tax', at(PRICING, 6, 5))).toBeNull();
    expect(reader().useIn(CHECKOUT, 'no_such_function', 'charge', at(CHECKOUT, 22, 5))).toBeNull();
  });
});

describe('the code around a site', () => {
  it('is its function, who refers to it — and who refers to those that hold no narrate — and what it calls', () => {
    expect(reader().around(siteAt(CHECKOUT, 23))).toEqual({
      range: [22, 24],
      callers: [
        { file: CHECKOUT, line: 15, fn: 'pay', narrated: false },
        { file: CHECKOUT, line: 32, fn: 'pay_all', narrated: false, how: 'via pay' },
      ],
      callees: [],
    });
    expect(reader().around(siteAt(CHECKOUT, 11))).toEqual({
      range: [9, 12],
      // `basket.total()` is a call on a value of unknown type: a parser with names alone cannot place it.
      callers: [],
      callees: [
        { file: PRICING, line: 6, fn: 'with_tax', narrated: true },
        { file: PRICING, line: 12, fn: 'round_price', narrated: false },
      ],
    });
    // The walk stops at narrated code: who calls `Basket.total` is told on that step, not on this one.
    expect(reader().around(siteAt(PRICING, 8))!.callers).toEqual([{ file: CHECKOUT, line: 9, fn: 'Basket.total', narrated: true }]);
  });
});

describe('a document of another shape', () => {
  it('is refused, naming the file and the table', () => {
    const noUses = document();
    delete (noUses.files[PRICING] as Partial<SourceIndexDocument['files'][string]>).uses;
    expect(() => checkSourceIndex(noUses, 'x.json')).toThrow(/x\.json — "uses" of shop\/pricing\.py is not a list/);
    const noSentence = document();
    noSentence.files[CHECKOUT].sites[2].sentence = null;
    expect(() => checkSourceIndex(noSentence, 'x.json')).toThrow(/the planned call at shop\/checkout\.py:18 needs a literal sentence/);
    expect(() => checkSourceIndex({ files: {} }, 'x.json')).toThrow(/"narratives" is not a list/);
  });
});

describe('a stack\'s command', () => {
  const print = (file: string) => ['node', '-e', `process.stdout.write(require('node:fs').readFileSync(${JSON.stringify(file)}, 'utf8'))`];

  it('prints the document, and is run again for the source as it is now', () => {
    const source = openJsonSource(print(INDEX), SHOP, isSource);
    expect(source.sites(PRICING).map((s) => s.fn)).toEqual(['with_tax']);
    expect(source.fresh().sites(PRICING).map((s) => s.fn)).toEqual(['with_tax']);
  });

  it('is refused when what it prints is not JSON', () => {
    expect(() => openJsonSource(print(join(SHOP, PRICING)), SHOP, isSource)).toThrow(/printed is not JSON/);
  });
});
