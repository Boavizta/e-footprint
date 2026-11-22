/**
 * project-stack.ts — the stack of this project, as the tools reach it: its source reader and its title
 * reader (`stack.ts` says what each answers), and the hook that draws a proposed migration's diff.
 *
 * `comprehension.config.json` names each as a module, a path from the root. A module is loaded where it is
 * first needed, and a module that does not export what it should stops the tool, naming it.
 */
import { readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CONFIG_FILE, ROOT, config, layout } from './config';
import { openJsonSource } from './json-source';
import { commandTitles } from './json-titles';
import type { PlanDiff, SourceReader, Stack, TitleReader } from './stack';

const load = createRequire(import.meta.url);

function loadStack(): Stack {
  // A stack that does not run in Node: its two commands print what the readers of this folder answer from.
  if (typeof config.stack !== 'string') {
    const { sourceIndex, titles } = config.stack;
    return { openSource: () => openJsonSource(sourceIndex, ROOT, (file) => !layout.isTest(file)), titles: commandTitles(titles, ROOT) };
  }
  const module = load(join(ROOT, config.stack)) as { stack?: Partial<Stack> };
  const stack = module.stack;
  if (!stack || typeof stack.openSource !== 'function' || typeof stack.titles?.read !== 'function') {
    throw new Error(`config: ${config.stack} (the "stack" of ${CONFIG_FILE}) must export \`stack\`, with \`openSource()\` and \`titles.read(file, text)\``);
  }
  return stack as Stack;
}

let stack: Stack | null = null;

/** A reader of the source as it stands. */
export const openSource = (): SourceReader => (stack ??= loadStack()).openSource();

export const titles: TitleReader = {
  read: (file, text) => (stack ??= loadStack()).titles.read(file, text),
  prime: (files) => (stack ??= loadStack()).titles.prime?.(files),
};

/** The project's hook for a proposed migration's diff; null when the configuration names none. */
export function loadPlanDiff(): PlanDiff | null {
  if (config.planDiff === null) return null;
  const hook = load(join(ROOT, config.planDiff)) as Partial<PlanDiff>;
  if (typeof hook.draw !== 'function' || typeof hook.isUnreachable !== 'function' || typeof hook.remedy !== 'string') {
    throw new Error(`config: ${config.planDiff} (the "planDiff" of ${CONFIG_FILE}) must export \`draw(sql, page)\`, \`isUnreachable(error)\` and \`remedy\``);
  }
  return hook as PlanDiff;
}

/** What a page or a snapshot is as old as, beside what it was read from: the tools' own files, the
 *  configuration and the files beside the stack's module, as paths from the root. */
export function toolSources(): string[] {
  const code = (dir: string) => readdirSync(dir).filter((f) => /\.(?:ts|mjs)$/.test(f)).sort().map((f) => relative(ROOT, join(dir, f)));
  const stackFiles = typeof config.stack === 'string' ? code(dirname(join(ROOT, config.stack))) : [];
  return [...code(dirname(fileURLToPath(import.meta.url))), CONFIG_FILE, ...stackFiles];
}
