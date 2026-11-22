/**
 * A title reader for the tools' own tests (`TitleReader`, `../stack.ts`): the smallest syntax their fixtures
 * are written in — one test a line, `it('title', …)`, `test('title', …)` or `it.todo('title')`, in single
 * quotes. A project's stack has its own reader and its own tests of it; what is fenced here is what the tools
 * do with a reader's answer.
 */
import type { Stand, TestTitle, TitleReader } from '../stack';

const TEST = /^\s*(it|test)(\.todo)?\(\s*'((?:\\.|[^'\\])*)'/;

export const lineTitles: TitleReader = {
  read(_file, text) {
    const tests: TestTitle[] = [];
    const stands: Stand[] = [];
    text.split('\n').forEach((line, i) => {
      const m = TEST.exec(line);
      if (!m) return;
      const title = m[3].replace(/\\(.)/g, '$1');
      tests.push({ title, line: i + 1, column: line.indexOf(m[1]) + 1, planned: m[2] !== undefined });
      stands.push({ line: i + 1, label: `${m[1]} "${title}"`, test: title });
    });
    return { tests, stands, journeyCases: [] };
  },
};
