/**
 * The line a generated page carries to say which tree it was rendered from. Generated pages are not
 * committed (specs/conventions.md § Generated pages), so a page open in a browser can be older than the
 * checkout beside it; the stamp is how a reader tells.
 */
import { execFileSync } from 'node:child_process';

function git(args: string[]): string {
  try {
    return execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return '';
  }
}

/** "rendered from 1eefd6ce" or "rendered from 1eefd6ce + uncommitted changes"; the token ledger never counts as a change. */
export function renderStamp(): string {
  const head = git(['rev-parse', '--short', 'HEAD']);
  if (!head) return 'rendered outside a git checkout';
  const dirty = git(['status', '--porcelain', '--', '.', ':(exclude)ai-usage']) !== '';
  return `rendered from ${head}${dirty ? ' + uncommitted changes' : ''}`;
}
