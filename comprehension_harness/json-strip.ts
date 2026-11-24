/**
 * json-strip.ts — `Stack.strip` (`stack.ts`) for a stack that does not run in Node: its command reads
 * `{ file, text, feature }` on its input and prints `{ text, taken }`, the file as the archive of the feature
 * leaves it and what was taken off. One process a file: a strip is run once a feature, on the files that name it.
 *
 * A command that fails is the stack's refusal (a `built` call that cannot go alone), said as the command said
 * it. An answer that is not of that shape stops the tool, naming the command.
 */
import { execFileSync } from 'node:child_process';
import type { Stripped } from './stack';

const KINDS: ReadonlyArray<Stripped['taken'][number]['kind']> = ['built', 'title', 'screen'];

export function commandStrip(command: readonly string[], cwd: string): (file: string, text: string, feature: string) => Stripped {
  const [program, ...args] = command;
  const named = command.join(' ');
  return (file, text, feature) => {
    let printed: string;
    try {
      printed = execFileSync(program, args, { cwd, input: JSON.stringify({ file, text, feature }), encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe'] });
    } catch (error) {
      const said = String((error as { stderr?: unknown }).stderr ?? '').trim();
      throw new Error(said || `comprehension-strip: \`${named}\` failed on ${file} — ${(error as Error).message}`);
    }
    let answer: unknown;
    try { answer = JSON.parse(printed); } catch (error) { throw new Error(`comprehension-strip: \`${named}\` did not print JSON for ${file} — ${(error as Error).message}`); }
    const a = answer as Partial<Stripped> | null;
    const isTaken = (t: unknown) => t !== null && typeof t === 'object' && typeof (t as { line?: unknown }).line === 'number'
      && KINDS.includes((t as { kind: Stripped['taken'][number]['kind'] }).kind) && typeof (t as { was?: unknown }).was === 'string';
    if (a === null || typeof a !== 'object' || typeof a.text !== 'string' || !Array.isArray(a.taken) || !a.taken.every(isTaken)) {
      throw new Error(`comprehension-strip: \`${named}\` — the answer for ${file} is not { text, taken: [{ line, kind, was }] }, kind being ${KINDS.join(', ')}`);
    }
    return { text: a.text, taken: a.taken };
  };
}
