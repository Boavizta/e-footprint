/**
 * json-titles — the title reader of a stack that does not run in Node (`../json-titles.ts`): a command fed
 * the files as JSON, answering in the same order.
 *
 * What is worth fencing: that a render costs one process whatever the number of files, that a text already
 * answered costs none, and that an answer of another shape is refused.
 */
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { commandTitles } from '../json-titles';

describe('commandTitles', () => {
  let dir = '';
  beforeAll(() => { dir = mkdtempSync(join(tmpdir(), 'comprehension-titles-')); });
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  /** A stack's command, here in Node: a test per line of the text, and one line written to `runs` per process. */
  const command = (answer: string) => ['node', '-e', `
    const fs = require('node:fs');
    fs.appendFileSync('runs', 'run\\n');
    const files = JSON.parse(fs.readFileSync(0, 'utf8'));
    process.stdout.write(JSON.stringify(${answer}));`];
  const perLine = 'files.map(({ file, text }) => ({ file, tests: text.split("\\n").map((title, i) => ({ title, line: i + 1, column: 1, planned: false })), stands: [], journeyCases: [] }))';
  const runs = () => readFileSync(join(dir, 'runs'), 'utf8').split('\n').filter(Boolean).length;

  it('answers a batch in one process, keeps each answer by the file\'s text, and asks alone for a text it was not told of', () => {
    const titles = commandTitles(command(perLine), dir);
    titles.prime!([{ file: 'a.py', text: 'one\ntwo' }, { file: 'b.py', text: 'three' }]);
    expect(runs()).toBe(1);
    expect(titles.read('a.py', 'one\ntwo').tests.map((t) => [t.title, t.line])).toEqual([['one', 1], ['two', 2]]);
    expect(titles.read('b.py', 'three').tests.map((t) => t.title)).toEqual(['three']);
    titles.prime!([{ file: 'a.py', text: 'one\ntwo' }]);
    expect(runs()).toBe(1);
    // The same file at another commit is another text.
    expect(titles.read('a.py', 'one').tests.map((t) => t.title)).toEqual(['one']);
    expect(runs()).toBe(2);
  });

  it('refuses an answer that is not a list of as many files, or not of the shape', () => {
    expect(() => commandTitles(command('[]'), dir).read('a.py', 'x')).toThrow(/was asked for 1 file and did not answer a list of as many/);
    expect(() => commandTitles(command('files.map(({ file }) => ({ file, tests: [] }))'), dir).read('a.py', 'x')).toThrow(/answer 1 is not \{ file: "a\.py", tests, stands, journeyCases \}/);
    expect(() => commandTitles(['node', '-e', 'process.stdout.write("no")'], dir).read('a.py', 'x')).toThrow(/did not print JSON/);
  });
});
