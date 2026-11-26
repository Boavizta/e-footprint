import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { JsonSource, checkSourceIndex } from '../json-source';
import { parseIntent } from '../intent-md';
import { renderDeliveryPage, renderPlanPage } from '../render';
import { assemblePlans, type PlanSite } from '../plan';
import { SourceIndex } from '../source-index';
import type { SourceIndexDocument } from '../stack';
import { LAYOUT } from './layout';

const FILE = 'shop/checkout.py';
const SHOP = join(dirname(fileURLToPath(import.meta.url)), 'fixtures/shop');

function example(samePiece = false, refactoring = false) {
  const doc = JSON.parse(readFileSync(join(SHOP, 'source-index.json'), 'utf8')) as SourceIndexDocument;
  const target = { file: FILE, line: 27, column: 5 };
  doc.files[FILE].imports.push({ name: 'refund_later', at: target });
  doc.files['shop/pricing.py'].imports.push({ name: 'refund', at: { file: FILE, line: 22, column: 5 } });
  const index = new SourceIndex(new JsonSource(checkSourceIndex(doc, 'the example'), (f) => !f.startsWith('tests/')));
  const sites: PlanSite[] = index.plannedSites().map((site) => ({
    ...site, ...site.planned!, sentence: site.planned!.change === 'added' ? 'Return the amount.' : 'Use `refund` or `refund_later`, then `charge`.',
    signature: site.planned!.signature, crossedBy: [], reachedBy: [], seenBy: [], expect: null, distinct: [],
    slug: samePiece ? 'deduct-the-card' : site.planned!.slug,
  }));
  const [plan] = assemblePlans({
    sites, statics: [], todos: [], narratives: [], layout: LAYOUT,
    docs: () => ({ folderExists: true, spec: null, plan: { file: 'specs/features/gift-cards/plan.md', intent: parseIntent(`# Gift cards\n\n## #deduct-the-card\n\n${refactoring ? 'Kind: refactoring\n\n' : ''}Deduct the balance.\n\n## #refund-to-card\n\nReturn the amount.\n`, 'plan.md') } }),
  });
  plan.doc!.lots = [{ slug: 'renderers', difficulty: 'standard', pieces: plan.pieces.map((p) => p.slug), screens: [], reason: 'Shared reference rendering.', line: 12 }];
  return { index, plan };
}

const markers = (html: string) => [...html.matchAll(/<button[^>]*data-new-declaration="([^"]+)"[^>]*>/g)].map((m) => m[1]);

describe('references to declarations introduced by a plan', () => {
  it('labels refactoring on plan and delivery cards without presenting its marker as prose', () => {
    const { plan, index } = example(false, true);
    for (const html of [renderPlanPage(plan, [], [], index), renderDeliveryPage(plan, [], index)]) {
      const header = html.match(/<section[^>]*id="piece-deduct-the-card"[^>]*>\s*<header>([\s\S]*?)<\/header>/)![1];
      expect(header).toContain('<span class="badge">Refactoring</span>');
      expect(html).not.toContain('Kind: refactoring');
      const unmarked = html.match(/<section[^>]*id="piece-refund-to-card"[^>]*>\s*<header>([\s\S]*?)<\/header>/)![1];
      expect(unmarked).not.toContain('Refactoring');
    }
  });

  it.each([false, true])('marks references and aliases, with the declaration in the same piece: %s', (samePiece) => {
    const { plan, index } = example(samePiece);
    const html = renderPlanPage(plan, [], [], index);
    expect(markers(html)).toEqual([`${FILE}#refund`, `${FILE}#refund`]);
    expect(html).toContain(`data-declaration="${FILE}#refund"`);
    expect(html).toMatch(/href="vscode:[^"]*checkout.py:27:5"[^>]*>refund<\/a> <button/);
    expect(html).not.toMatch(/>charge<\/a> <button/);
    expect(html).not.toMatch(/>checkout.py:28<\/a> <button/);
  });

  it('uses the resolved declaration rather than matching the symbol name', () => {
    const { plan, index } = example();
    const site = plan.pieces.flatMap((p) => p.sites).find((s) => s.change === 'changed')!;
    site.file = 'shop/pricing.py';
    site.line = 8;
    site.sentence = 'Use `refund`.';
    expect(markers(renderPlanPage(plan, [], [], index))).toEqual([]);
  });

  it('keeps an introduced declaration marked once built, on plan and delivery pages', () => {
    const { plan, index } = example();
    const added = plan.pieces.find((p) => p.sites.some((s) => s.change === 'added'))!;
    added.sites = [];
    added.built.sites = [`added ${FILE} in refund — Return the amount.`];
    const caller = plan.pieces.find((p) => p !== added)!;
    caller.doc!.what = 'Use `refund` and `charge`.';
    for (const html of [renderPlanPage(plan, [], [], index), renderDeliveryPage(plan, [], index)]) {
      expect(markers(html).length).toBeGreaterThan(0);
      expect(html).toContain(`class="pline built" data-declaration="${FILE}#refund"`);
      expect(html).not.toMatch(/>charge<\/a> <button/);
    }
  });

  it('does not add inert markers when the delivery has no declaration row yet', () => {
    const { plan, index } = example();
    plan.pieces[0].doc!.what = 'Use `refund`.';
    expect(markers(renderDeliveryPage(plan, [], index))).toEqual([]);
  });
});

describe('highlighting an introduced declaration', () => {
  afterEach(() => vi.useRealTimers());

  function interaction(bounds: Array<[number, number]>) {
    vi.useFakeTimers();
    const { plan, index } = example();
    const html = renderPlanPage(plan, [], [], index);
    const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].find((m) => m[1].includes('data-new-declaration'))![1];
    const rows = bounds.map(([top, bottom]) => ({
      dataset: { declaration: `${FILE}#refund` },
      getBoundingClientRect: () => ({ top, bottom, height: bottom - top }),
      classList: { add: vi.fn(), remove: vi.fn() },
      scrollIntoView: vi.fn(),
    }));
    let click: (event: unknown) => void;
    runInNewContext(script, {
      document: { addEventListener: (_: string, handler: typeof click) => { click = handler; }, querySelectorAll: () => rows },
      window: { innerHeight: 800, matchMedia: () => ({ matches: false }) },
      setTimeout, clearTimeout,
    });
    const press = () => click({ target: { closest: () => ({ dataset: { newDeclaration: `${FILE}#refund` } }) } });
    return { rows, press };
  }

  it('highlights a visible row without scrolling and clears the highlight after two seconds', () => {
    const { rows: [row], press } = interaction([[100, 150]]);
    press();
    expect(row.classList.add).toHaveBeenCalledWith('declaration-highlight');
    expect(row.scrollIntoView).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1999);
    expect(row.classList.remove).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(row.classList.remove).toHaveBeenCalledWith('declaration-highlight');
  });

  it.each([[-100, -50], [780, 830], [900, 950]])('scrolls an offscreen or clipped row into view: %s to %s', (top, bottom) => {
    const { rows: [row], press } = interaction([[top, bottom]]);
    press();
    expect(row.scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    expect(row.classList.add).toHaveBeenCalledWith('declaration-highlight');
  });

  it('highlights a visible declaration when both its flow and piece card draw a row', () => {
    const { rows, press } = interaction([[-100, -50], [100, 150]]);
    press();
    expect(rows[0].classList.add).not.toHaveBeenCalled();
    expect(rows[1].classList.add).toHaveBeenCalledWith('declaration-highlight');
    expect(rows.every((row) => row.scrollIntoView.mock.calls.length === 0)).toBe(true);
  });

  it('restarts the highlight duration when pressed again', () => {
    const { rows: [row], press } = interaction([[100, 150]]);
    press();
    vi.advanceTimersByTime(1500);
    press();
    row.classList.remove.mockClear();
    vi.advanceTimersByTime(500);
    expect(row.classList.remove).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1500);
    expect(row.classList.remove).toHaveBeenCalledOnce();
  });
});
