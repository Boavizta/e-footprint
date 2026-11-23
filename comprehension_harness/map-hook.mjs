#!/usr/bin/env node
/**
 * map-hook — a Claude Code PreToolUse hook (`.claude/settings.json`, on Edit and Write): the first time
 * a session edits a source file that carries a narrative step, or sits next to one, the agent is told
 * which steps, and which test tells them. An agent that was never told `npm run map` exists still
 * learns that the file it is about to change is part of a told flow.
 *
 * It only reads the snapshot `comprehension_harness/map-build.ts` wrote (no rebuild, no test run: a hook answers in
 * milliseconds or not at all), says so when that snapshot is older than the file, and never fails the
 * edit: any error ends silently with exit 0. It speaks once per file per session.
 */
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative } from 'node:path';
import { logMapEvent } from './map-log.mjs';
import { readProject } from './project.mjs';

try {
  const { root: ROOT, config, mapDir } = readProject();
  const input = JSON.parse(readFileSync(0, 'utf8'));
  const path = input.tool_input?.file_path;
  if (typeof path !== 'string') process.exit(0);
  const file = relative(ROOT, path);
  if (!config.source.product.some((folder) => file.startsWith(folder))) process.exit(0);
  const snapshot = join(mapDir, 'narratives.json');
  if (!existsSync(snapshot)) process.exit(0);

  // Once per file per session.
  const seenFile = join(tmpdir(), 'comprehension-map-hook', `${String(input.session_id ?? 'session').replace(/[^A-Za-z0-9_-]/g, '')}.json`);
  const seen = existsSync(seenFile) ? JSON.parse(readFileSync(seenFile, 'utf8')) : [];
  const who = { session_id: input.session_id ?? null, agent_id: input.agent_id ?? null, agent_type: input.agent_type ?? null, tool: input.tool_name ?? null };
  if (seen.includes(file)) { logMapEvent({ kind: 'hook', file, spoke: false, why: 'already told this session', ...who }); process.exit(0); }

  const map = JSON.parse(readFileSync(snapshot, 'utf8'));
  const lines = [];
  const tests = new Set();
  for (const n of map.narratives) {
    const steps = n.steps.filter((s) => s.file === file);
    const branches = n.branches.filter((b) => b.file === file);
    if (steps.length) lines.push(`- ${steps.length === 1 ? 'step' : 'steps'} ${steps.map((s) => `${s.n} (${s.fn}:${s.line})`).join(', ')} of "${n.title}"`);
    if (branches.length) lines.push(`- ${branches.length === 1 ? 'a branch' : `${branches.length} branches`} of "${n.title}" (${branches.map((b) => `${b.fn}:${b.line}`).join(', ')})`);
    if (steps.length || branches.length) tests.add(n.file);
  }
  const near = new Set();
  // Next to a PRODUCT narrative only: a mechanism can have sixty callers, and telling each of them so is noise.
  for (const n of map.narratives) if (n.kind === 'product') for (const s of n.steps) for (const x of [...s.callers, ...s.callees]) {
    if (!x.narrated && x.file === file) near.add(x.fn);
  }
  if (lines.length === 0 && near.size === 0) process.exit(0);

  mkdirSync(dirname(seenFile), { recursive: true });
  writeFileSync(seenFile, JSON.stringify([...seen, file]));

  const stale = statSync(path).mtimeMs > (map.inputs[file] ?? Infinity);
  const text = [
    lines.length ? `${file} is part of a narrative — what the code does for one action, told step by step by \`narrate\` calls in the code, in the order one test crosses it:` : `${file} holds no \`narrate\` call and sits next to narrated code:`,
    ...lines,
    ...(near.size ? [`${lines.length ? '- also next to narrated code, un-narrated: ' : '- '}${[...near].slice(0, 8).join(', ')}${near.size > 8 ? `, and ${near.size - 8} more` : ''}`] : []),
    ...(tests.size ? [`The tests that tell it: ${[...tests].join(', ')}. A \`narrate\` sentence states what the code at that line does: change the code and the sentence together.`] : []),
    `Details: npm run map -- where ${file}${stale ? '   (this note is from a snapshot older than the file; that command refreshes it)' : ''}`,
  ].join('\n');
  logMapEvent({ kind: 'hook', file, spoke: true, chars: text.length, steps: lines.length, stale, ...who });
  process.stdout.write(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', additionalContext: text } }));
} catch {
  process.exit(0);
}
