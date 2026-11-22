/**
 * map-log — one line per `npm run map` call and per note of the edit hook, so their use can be analysed:
 * which verbs agents ask, how often an answer needed a refresh, which files the hook spoke for.
 *
 * Appended to `ai-usage/.state/map-events-YYYY-MM.jsonl` (gitignored, this machine only). Each line
 * carries the Claude Code session id, which is the `session_id` of the usage ledger's runs
 * (`ai-usage/data/<machine>/runs-*.jsonl`): join on it for the skill, stage, feature and tokens of the
 * session that asked. A sub-agent shares its parent's session id; its own run is the one whose
 * start and end surround `ts`. Never throws: a log that cannot be written is not a reason to fail an answer.
 */
import { appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { findRoot } from './project.mjs';

export function logMapEvent(event) {
  try {
    const STATE = join(findRoot(), 'ai-usage', '.state');
    const ts = new Date().toISOString();
    mkdirSync(STATE, { recursive: true });
    appendFileSync(join(STATE, `map-events-${ts.slice(0, 7)}.jsonl`), `${JSON.stringify({ ts, session_id: process.env.CLAUDE_CODE_SESSION_ID ?? null, ...event })}\n`);
  } catch { /* the answer matters more than its log line */ }
}
