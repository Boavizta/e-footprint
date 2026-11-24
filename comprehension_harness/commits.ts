/**
 * commits.ts — the commits that deliver a plan's pieces, read from git.
 *
 * A commit delivers a piece when its message holds the line `Piece: <feature>#<slug>`: once for a piece's own
 * commit and for a fix of it, once per piece for a lot's closing commit. Nothing else ties a commit to the plan,
 * so a commit of the same branch that names no piece is other work and is not read.
 *
 * For each such commit: the files it touched, and what it did to the tests of each test file it touched, read
 * against the plan that file carried before it (`testChanges`, `comprehension_harness/plan.ts`): what it deleted or
 * changed as a comment said, kept with the commit for the page.
 *
 * What a lot did beyond the plan is judged on what the lot comes to, not on each commit's own steps: each test
 * file a commit made since the approval touched is read once, from the approved code to the file as it stands,
 * against the comments the approved code held. So a later commit that tags a test or restores one settles it; a
 * fix that renames a test an earlier commit added is neither an addition nor a deletion; and a test retitled in
 * a fix, after the commit that made the change its comment planned, is still a planned retitle. Each title so
 * found goes to the last commit that moved it.
 *
 * `base` is the commit of the approval on file. A commit made after it is what the lot check reads
 * (`PieceCommit.sinceApproval`); an earlier one is only listed with its piece. A base that is not in the
 * history of `HEAD` — the branch was rebuilt — tells no commit to come after it.
 *
 * Beside them, every commit of the branch from the oldest of them on, with the files it changed (`history`):
 * a commit that names no piece is not read as a delivery, and still tells that a piece's file moved between
 * two of the piece's commits, which then do not read as one diff (`commitBlocks`, `comprehension_harness/plan.ts`).
 *
 * What a commit did never changes: it is read once per process and kept by its hash. What the working tree
 * holds does change: a file's difference from the approval to it (`hunkReader`) is kept for one render only.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Layout } from './layout';
import type { TitleReader } from './stack';
import { testChanges, type CommitTouch, type Hunk, type PieceCommit } from './plan';

const KEBAB = '[a-z0-9]+(?:-[a-z0-9]+)*';

/** What a commit did, as git tells it: `came` and `gone` are every test title it brought in and took out. */
type Read = Omit<PieceCommit, 'sinceApproval' | 'untagged' | 'deleted'> & { feature: string; came: PieceCommit['untagged']; gone: PieceCommit['deleted'] };
const read = new Map<string, Read>();

/** The commits of `HEAD`'s history that name a piece of `feature`, oldest first, and every commit from the
 *  oldest of them on, oldest first, with the files it changed. */
export function readPieceCommits(feature: string, base: string | null, cwd: string, titles: TitleReader, layout: Layout): { list: PieceCommit[]; baseKnown: boolean; history: CommitTouch[] } {
  const git = (...args: string[]) => execFileSync('git', args, { cwd, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] });
  const tried = (...args: string[]) => { try { return git(...args); } catch { return null; } };
  const names = new RegExp(`^Piece:[ \\t]*${feature}#(${KEBAB})[ \\t]*$`, 'gm');
  const log = tried('log', '--reverse', '--no-merges', '-E', `--grep=^Piece: *${feature}#`, '--format=%H%x1f%s%x1f%b%x1e') ?? '';
  const found = log.split('\x1e').map((entry) => entry.replace(/^\n/, '').split('\x1f')).filter((parts) => parts.length === 3);
  const baseKnown = base !== null && tried('merge-base', '--is-ancestor', base, 'HEAD') !== null;
  const after = new Set(baseKnown ? git('rev-list', `${base}..HEAD`).split('\n').filter(Boolean) : []);
  // Read anew at each call: the branch grows. The oldest commit that has no parent is the root, read from there.
  const touches = ['log', '--topo-order', '--reverse', '--no-renames', '--name-only', '--format=%x1e%H'];
  const history: CommitTouch[] = found.length === 0 ? [] : (tried(...touches, `${found[0][0]}^..HEAD`) ?? git(...touches, 'HEAD'))
    .split('\x1e').map((entry) => entry.split('\n').filter(Boolean)).filter((rows) => rows.length > 0).map(([sha, ...files]) => ({ sha, files }));

  const list = found.map(([sha, subject, body]): Read => {
    const key = `${feature} ${sha}`;
    let commit = read.get(key);
    if (!commit) {
      const pieces = [...new Set([...`${subject}\n${body}`.matchAll(names)].map((m) => m[1]))];
      const files = new Map<string, PieceCommit['files'][number]>();
      for (const row of git('show', '--format=', '--numstat', '--no-renames', sha).split('\n')) {
        const m = /^(\d+|-)\t(\d+|-)\t(.+)$/.exec(row);
        if (m) files.set(m[3], { file: m[3], added: Number(m[1]) || 0, removed: Number(m[2]) || 0, line: null });
      }
      // The first line the commit changed in each file it left standing, off the hunk headers.
      let current: string | null = null;
      for (const row of git('show', '--format=', '--unified=0', '--no-renames', sha).split('\n')) {
        if (row.startsWith('+++ ')) current = row === '+++ /dev/null' ? null : row.slice(6);
        const hunk = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/.exec(row);
        const file = current === null ? undefined : files.get(current);
        // A hunk that only deletes names the line before the gap.
        if (hunk && file && file.line === null) file.line = Math.max(1, Number(hunk[1]) + (hunk[2] === '0' ? 1 : 0));
      }
      const came: Read['came'] = [];
      const gone: Read['gone'] = [];
      const planned: PieceCommit['planned'] = [];
      for (const file of [...files.keys()].filter((f) => layout.isTestFile(f))) {
        const did = testChanges(feature, file, tried('show', `${sha}^:${file}`) ?? '', tried('show', `${sha}:${file}`) ?? '', titles);
        came.push(...did.came.map((title) => ({ file, title })));
        gone.push(...did.gone.map((title) => ({ file, title })));
        planned.push(...did.planned.map((p) => ({ file, ...p })));
      }
      commit = { feature, sha, subject, pieces, files: [...files.values()], planned, came, gone };
      read.set(key, commit);
    }
    return commit;
  });

  // What the lot comes to, a test file at a time, from the approved code to the file as it stands; each title
  // found goes to the last commit made since the approval that moved it, else to the last that touched the file.
  const since = list.filter((c) => after.has(c.sha));
  const untagged = new Map<string, PieceCommit['untagged']>();
  const deleted = new Map<string, PieceCommit['deleted']>();
  for (const file of new Set(since.flatMap((c) => c.files.map((f) => f.file)).filter((f) => layout.isTestFile(f)))) {
    const now = existsSync(join(cwd, file)) ? readFileSync(join(cwd, file), 'utf8') : '';
    const lot = testChanges(feature, file, tried('show', `${base}:${file}`) ?? '', now, titles);
    const give = (to: Map<string, Array<{ file: string; title: string }>>, title: string, moved: (c: Read) => Array<{ file: string; title: string }>) => {
      const touched = since.filter((c) => c.files.some((f) => f.file === file));
      const by = [...touched].reverse().find((c) => moved(c).some((t) => t.file === file && t.title === title)) ?? touched[touched.length - 1];
      to.set(by.sha, [...(to.get(by.sha) ?? []), { file, title }]);
    };
    for (const title of lot.untagged) give(untagged, title, (c) => c.came);
    for (const title of lot.deleted) give(deleted, title, (c) => c.gone);
  }
  return {
    list: list.map(({ came: _came, gone: _gone, feature: _feature, ...rest }): PieceCommit => ({ ...rest, sinceApproval: after.has(rest.sha), untagged: untagged.get(rest.sha) ?? [], deleted: deleted.get(rest.sha) ?? [] })),
    baseKnown,
    history,
  };
}

/** A file's difference from the commit of an approval to the working tree; null where git cannot read that commit. */
export type HunkReader = (file: string) => Hunk[] | null;

/**
 * A reader of a file's difference from `base`, the commit of an approval, to the working tree, a stretch at a
 * time (`Hunk`): what the lot check reads a place and a change into. Null where git cannot read `base`.
 *
 * A reader is made for one render and reads each file once in it, however many places ask. It is never kept
 * between two renders: the working tree moves, and an old difference laid over the functions as they now stand
 * puts a change in a function it never touched.
 */
export function hunkReader(base: string, cwd: string): HunkReader {
  const read = new Map<string, Hunk[] | null>();
  return (file) => {
    if (read.has(file)) return read.get(file)!;
    let hunks: Hunk[] | null = null;
    try {
      const diff = execFileSync('git', ['diff', '--unified=0', '--no-renames', base, '--', file], { cwd, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] });
      hunks = [];
      for (const row of diff.split('\n')) {
        const head = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/.exec(row);
        const last = hunks[hunks.length - 1];
        if (head) {
          const [oldAt, oldN, nowAt, nowN] = [Number(head[1]), Number(head[2] ?? 1), Number(head[3]), Number(head[4] ?? 1)];
          hunks.push({ was: oldN ? [oldAt, oldAt + oldN - 1] : null, now: nowN ? [nowAt, nowAt + nowN - 1] : null, at: { old: oldAt, now: nowAt }, removed: [], added: [] });
        } else if (last && row.startsWith('-') && !row.startsWith('---')) last.removed.push(row.slice(1));
        else if (last && row.startsWith('+') && !row.startsWith('+++')) last.added.push(row.slice(1));
      }
    } catch { hunks = null; }
    read.set(file, hunks);
    return hunks;
  };
}

/**
 * The commits that changed the lines `from` to `to` of `file`, oldest first, among those from `since` on: what
 * `git log -L` traces back from the lines as `HEAD` holds them. Null when the working tree's file is not
 * `HEAD`'s, since the lines asked about are then other lines, and where git cannot tell.
 */
export function commitsOfLines(file: string, from: number, to: number, since: string, cwd: string): string[] | null {
  const git = (...args: string[]) => execFileSync('git', args, { cwd, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] });
  try {
    git('diff', '--quiet', 'HEAD', '--', file);
    return git('log', '--format=%x1e%H', `-L${from},${to}:${file}`, `${since}^..HEAD`).split('\x1e').slice(1).map((entry) => entry.slice(0, 40)).reverse();
  } catch {
    return null;
  }
}

