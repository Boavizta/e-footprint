import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';
import { JsonSource, checkSourceIndex } from '../json-source';
import { deriveNarratives, renderIndexPage, renderMechanismPage, renderNarrativePage } from '../render';
import { SourceIndex } from '../source-index';
import type { NarrativeKind, SourceIndexDocument, Story } from '../stack';

const TOOLS = dirname(dirname(fileURLToPath(import.meta.url)));
const dirs: string[] = [];
afterEach(() => { for (const dir of dirs.splice(0)) rmSync(dir, { recursive: true, force: true }); });

function example(kind: NarrativeKind, docScope: boolean) {
  const doc = JSON.parse(readFileSync(join(TOOLS, 'tests/fixtures/shop/source-index.json'), 'utf8')) as SourceIndexDocument;
  if (docScope) doc.narratives[0].scope = 'doc';
  const source = new JsonSource(checkSourceIndex(doc, 'fixture'), (file) => !file.startsWith('tests/'));
  const index = new SourceIndex(source);
  const step = source.sites('shop/checkout.py').find((s) => s.line === 23)!;
  const story: Story = { file: doc.narratives[0].file, test: doc.narratives[0].firstTest!,
    narrative: { title: doc.narratives[0].title, kind }, canonical: true, order: 1, state: 'passed', durationMs: 1,
    hits: [{ kind: 'step', sentence: step.sentence!, site: step, stack: [], watch: null, atMs: 1 }] };
  return { index, stories: [story], narratives: deriveNarratives([story], index) };
}

describe('documentation narrative scope', () => {
  it.each(['product', 'mechanism'] as const)('labels a %s narrative without changing its steps or ownership', (kind) => {
    const plain = example(kind, false);
    const scoped = example(kind, true);
    const [narrative] = scoped.narratives;
    expect(narrative.scope).toBe('doc');
    expect(narrative.kind).toBe(kind);
    expect(narrative.steps).toEqual(plain.narratives[0].steps);
    expect(narrative.siteIds).toEqual(plain.narratives[0].siteIds);
    const render = kind === 'product' ? renderNarrativePage : renderMechanismPage;
    const html = render(narrative, scoped.stories, scoped.narratives, scoped.index, { entries: [], byKey: new Map() });
    expect(html).toContain('data-narrative-scope="doc">doc</span>');
    const plainHtml = render(plain.narratives[0], plain.stories, plain.narratives, plain.index, { entries: [], byKey: new Map() });
    expect(plainHtml).not.toContain('data-narrative-scope');
    const index = renderIndexPage([{ kind: 'Narratives', pages: [{ href: 'scenario.html', title: narrative.title, scope: narrative.scope }] }]);
    expect(index).toContain('data-narrative-scope="doc">doc</span>');
  });

  it('lists only documentation flows when scope is requested and retains the label in individual map answers', () => {
    const root = mkdtempSync(join(tmpdir(), 'comprehension-scope-'));
    dirs.push(root);
    for (const file of ['map.mjs', 'project.mjs', 'map-log.mjs']) copyFileSync(join(TOOLS, file), join(root, file));
    writeFileSync(join(root, 'comprehension.config.json'), JSON.stringify({ cache: 'cache', docs: 'docs',
      commands: { journeys: [], tool: [], tests: [] }, tests: { narrative: [] } }));
    mkdirSync(join(root, 'cache/map'), { recursive: true });
    const base = { kind: 'product', summary: 'A scenario is converted.', file: 'tests/test_scenario.py', line: 1,
      canonical: 'test_converts', steps: [], branches: [], ridesOn: [], exercisedBy: [], variants: [], editedSince: [] };
    writeFileSync(join(root, 'cache/map/narratives.json'), JSON.stringify({ inputs: {}, narratives: [
      { ...base, slug: 'scenario', title: 'A scenario is converted', scope: 'doc' },
      { ...base, slug: 'basket', title: 'A basket is paid' },
    ] }));
    const run = (...args: string[]) => spawnSync(process.execPath, ['map.mjs', ...args], { cwd: root, encoding: 'utf8' });
    const all = run('narrative');
    expect(all.status, all.stderr).toBe(0);
    expect(all.stdout).toContain('basket');
    expect(all.stdout).toContain('scenario [doc]');
    const filtered = run('narrative', '--scope', 'doc');
    expect(filtered.status, filtered.stderr).toBe(0);
    expect(filtered.stdout).toContain('scenario [doc]');
    expect(filtered.stdout).not.toContain('basket');
    const detail = run('narrative', 'scenario');
    expect(detail.status, detail.stderr).toBe(0);
    expect(detail.stdout).toContain('[product, doc]');
    expect(run('narrative', '--scope', 'contributor').status).toBe(1);
  });
});
