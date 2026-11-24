/**
 * json-strip — the strip of a stack that does not run in Node (`../json-strip.ts`): a command fed one file as
 * JSON, answering what the archive of a feature leaves of it.
 *
 * What is worth fencing: that the command is handed the file, its text and the feature, that its refusal is
 * said as it said it, and that an answer of another shape is refused.
 */
import { describe, expect, it } from 'vitest';
import { commandStrip } from '../json-strip';

/** A stack's command, here in Node: what it prints is computed from what it was asked. */
const command = (answer: string) => ['node', '-e', `
  const asked = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
  ${answer}`];
const print = (answer: string) => command(`process.stdout.write(JSON.stringify(${answer}));`);

describe('commandStrip', () => {
  it('hands the command the file, its text and the feature, and answers what it printed', () => {
    const strip = commandStrip(print("{ text: asked.text.replace(`built('${asked.feature}#cut:the-cut')\\n`, ''), taken: [{ line: 2, kind: 'built', was: asked.file }] }"), process.cwd());
    expect(strip('app/a.py', "x = 1\nbuilt('demo#cut:the-cut')\ny = 2\n", 'demo')).toEqual({ text: 'x = 1\ny = 2\n', taken: [{ line: 2, kind: 'built', was: 'app/a.py' }] });
  });

  it('says a refusal as the command said it', () => {
    const strip = commandStrip(command("process.stderr.write(`comprehension-strip: ${asked.file}:2 — built(…) is no statement of a block\\n`); process.exit(1);"), process.cwd());
    expect(() => strip('app/a.py', 'x', 'demo')).toThrow(/^comprehension-strip: app\/a\.py:2 — built\(…\) is no statement of a block$/);
  });

  it('refuses an answer that is not JSON, or not of the shape', () => {
    expect(() => commandStrip(['node', '-e', 'process.stdout.write("no")'], process.cwd())('a.py', 'x', 'demo')).toThrow(/did not print JSON for a\.py/);
    expect(() => commandStrip(print('{ text: asked.text }'), process.cwd())('a.py', 'x', 'demo')).toThrow(/the answer for a\.py is not \{ text, taken/);
    expect(() => commandStrip(print("{ text: '', taken: [{ line: 1, kind: 'import', was: 'x' }] }"), process.cwd())('a.py', 'x', 'demo')).toThrow(/the answer for a\.py is not \{ text, taken/);
  });
});
