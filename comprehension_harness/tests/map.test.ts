import { spawnSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';

const TOOLS = dirname(dirname(fileURLToPath(import.meta.url)));
const dirs: string[] = [];
afterEach(() => { for (const dir of dirs.splice(0)) rmSync(dir, { recursive: true, force: true }); });

function repository(journeys: string[] = []) {
  const root = mkdtempSync(join(tmpdir(), 'comprehension-map-'));
  dirs.push(root);
  const put = (file: string, text: string) => {
    mkdirSync(dirname(join(root, file)), { recursive: true });
    writeFileSync(join(root, file), text);
  };
  for (const file of ['map.mjs', 'project.mjs', 'map-log.mjs']) copyFileSync(join(TOOLS, file), join(root, file));
  put('comprehension.config.json', JSON.stringify({
    cache: 'cache', docs: 'docs',
    commands: { journeys, tool: [process.execPath, '-e', 'require("node:fs").writeFileSync("unexpected-run", "tool")'], tests: [] },
    tests: { journeys: '^tests/journeys/', narrative: [] },
  }));
  const intent = '# Example\n\n## The change\n\nBuild a model.\n';
  put('docs/features/example/spec.md', intent);
  const run = (feature = 'example') => spawnSync(process.execPath, ['map.mjs', 'spec', feature], { cwd: root, encoding: 'utf8' });
  return { root, put, intent, run };
}

describe('map spec and optional screen journeys', () => {
  it('reads the current spec without snapshots or tool runs when journeys are disabled', () => {
    const { root, put, intent, run } = repository();
    // Even a leftover journey snapshot must not substitute its older text for the spec.
    put('cache/map/spec-example.json', JSON.stringify({ intent: 'Old text' }));
    const result = run();
    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain(intent.trim());
    expect(result.stdout).not.toContain('Old text');
    expect(existsSync(join(root, 'unexpected-run'))).toBe(false);
    expect(existsSync(join(root, 'cache/map/narratives.json'))).toBe(false);
    const missing = run('missing');
    expect(missing.status).toBe(1);
    expect(missing.stderr).toContain('no spec docs/features/missing/spec.md');
  });

  it('retains planned screens and cases from snapshots when journeys are configured', () => {
    const { root, put, intent, run } = repository(['run-journeys']);
    const builtAt = '2026-01-01T00:00:00.000Z';
    put('cache/map/narratives.json', JSON.stringify({ builtAt, inputs: {}, narratives: [] }));
    mkdirSync(join(root, 'cache/stories'), { recursive: true });
    const spec = {
      builtAt, inputs: {}, intent,
      journeys: [{ slug: 'checkout', name: 'Pay', file: 'tests/journeys/pay.ts', who: 'buyer', wants: 'pay', now: 'a basket',
        path: ['basket'], unreached: [], changed: [{ id: 'basket', why: 'Review',
          planned: { what: 'Show the total', mockup: 'total.html' }, todos: [{ title: 'Total includes tax', line: 12 }] }] }],
      rides: { narratives: [], orphans: [], silent: [], server: [] },
    };
    put('cache/map/spec-example.json', JSON.stringify(spec));
    const result = run();
    expect(result.status, result.stderr).toBe(0);
    expect(result.stdout).toContain('planned: Show the total');
    expect(result.stdout).toContain('Total includes tax');
    expect(result.stdout).toContain('mockup:  total.html');
    // Configured journeys must still demand fresh captures after their test changes.
    put('cache/map/spec-example.json', JSON.stringify({ ...spec, inputs: { 'tests/journeys/pay.ts': 0 } }));
    const stale = run();
    expect(stale.status).toBe(1);
    expect(stale.stderr).toContain('changed since its captures were taken — run-journeys');
  });
});
