/**
 * json-titles.ts — `TitleReader` (`stack.ts`) for a stack that does not run in Node: its command reads
 * `[{ file, text }]` on its input and prints `[{ file, tests, stands, journeyCases }]` in the same order, one
 * process for the whole batch.
 *
 * A render says at once which files it will ask for (`prime`), so it costs one process; a file asked for alone
 * (the lot check reads a test file on both sides of a commit) costs one more. An answer is kept by the file's
 * text. An answer that is not of that shape stops the tool, naming the command.
 */
import { execFileSync } from 'node:child_process';
import type { TestFile, TitleReader } from './stack';

const isList = (x: unknown): x is unknown[] => Array.isArray(x);

export function commandTitles(command: readonly string[], cwd: string): TitleReader {
  const known = new Map<string, TestFile>();
  const key = (file: string, text: string) => `${file}\n${text}`;
  const named = command.join(' ');

  function ask(files: ReadonlyArray<{ file: string; text: string }>): void {
    const [program, ...args] = command;
    const printed = execFileSync(program, args, { cwd, input: JSON.stringify(files), encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
    let answers: unknown;
    try { answers = JSON.parse(printed); } catch (error) { throw new Error(`comprehension-titles: \`${named}\` did not print JSON — ${(error as Error).message}`); }
    if (!isList(answers) || answers.length !== files.length) throw new Error(`comprehension-titles: \`${named}\` was asked for ${files.length} file${files.length === 1 ? '' : 's'} and did not answer a list of as many`);
    answers.forEach((answer, i) => {
      const a = answer as Partial<TestFile> & { file?: unknown } | null;
      if (a === null || typeof a !== 'object' || a.file !== files[i].file || !isList(a.tests) || !isList(a.stands) || !isList(a.journeyCases)) {
        throw new Error(`comprehension-titles: \`${named}\` — answer ${i + 1} is not { file: "${files[i].file}", tests, stands, journeyCases }`);
      }
      known.set(key(files[i].file, files[i].text), { tests: a.tests, stands: a.stands, journeyCases: a.journeyCases });
    });
  }

  return {
    prime(files) {
      const unknown = files.filter(({ file, text }) => !known.has(key(file, text)));
      if (unknown.length > 0) ask(unknown);
    },
    read(file, text) {
      if (!known.has(key(file, text))) ask([{ file, text }]);
      return known.get(key(file, text))!;
    },
  };
}
