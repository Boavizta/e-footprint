/**
 * commits — the commits that deliver a plan's pieces, read from git (`../commits.ts`).
 *
 * What is worth fencing: that only a commit naming a piece is read, that a commit made before the approval is
 * told from one made after it, and that a test added or deleted beyond the plan stops counting once a later
 * commit settles it. The repository is a throwaway one, built here. The tag word is spelled through `TAG` so
 * that no fixture of this file is itself a site when the renderer scans `tests/`.
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import * as commits from '../commits';
import { LAYOUT } from './layout';
import { lineTitles } from './titles';

// The commits' test files are read by this folder's own title reader.
const readPieceCommits = (feature: string, base: string | null, cwd: string) => commits.readPieceCommits(feature, base, cwd, lineTitles, LAYOUT);

const TAG = `@${'planned'}`;
const TEST = 'tests/x.test.ts';

describe('readPieceCommits', () => {
  let repo = '';
  const git = (...args: string[]) => execFileSync('git', ['-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', ...args], { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  const write = (file: string, text: string) => {
    mkdirSync(dirname(join(repo, file)), { recursive: true });
    writeFileSync(join(repo, file), text);
  };
  const commit = (message: string) => {
    git('add', '-A');
    git('commit', '-q', '--allow-empty', '-m', message);
    return git('rev-parse', 'HEAD');
  };
  const tests = (...lines: string[]) => `describe('x', () => {\n${lines.join('\n')}\n});\n`;
  let base = '';

  beforeAll(() => {
    repo = mkdtempSync(join(tmpdir(), 'comprehension-commits-'));
    git('init', '-q');
    write('src/reader.ts', 'export const cut = 1;\n');
    write(TEST, tests(`// ${TAG}.remove demo#cut held by the reference case`, `it('old cut', () => {});`, `it('goes quietly', () => {});`, `it.todo('demo#cut: lists two');`));
    commit('before the approval\n\nPiece: demo#column');
    base = commit('the plan is approved');
    write('src/reader.ts', 'export const cut = 1;\nexport const cap = 2;\n');
    write('src/other.ts', 'export const other = 1;\n');
    write(TEST, tests(`it('demo#cut: lists two', () => {});`, `it('one more belt', () => {});`));
    commit('the reader cuts\n\nSome words.\n\nPiece: demo#cut\nPiece: demo#save');
    write('README.md', 'other work\n');
    commit('other work, naming no piece');
  });
  afterAll(() => rmSync(repo, { recursive: true, force: true }));

  it('reads the commits that name a piece, oldest first, and tells those made since the approval', () => {
    const { list, baseKnown } = readPieceCommits('demo', base, repo);
    expect(baseKnown).toBe(true);
    expect(list.map((c) => [c.subject, c.pieces, c.sinceApproval])).toEqual([['before the approval', ['column'], false], ['the reader cuts', ['cut', 'save'], true]]);
    expect(readPieceCommits('other-feature', base, repo).list).toEqual([]);
  });

  it('reads what a commit touched, with the first line it changed, and what it did to the tests', () => {
    const cut = readPieceCommits('demo', base, repo).list[1];
    expect(cut.files).toEqual([
      { file: 'src/other.ts', added: 1, removed: 0, line: 1 },
      { file: 'src/reader.ts', added: 1, removed: 0, line: 2 },
      { file: TEST, added: 2, removed: 4, line: 2 },
    ]);
    expect(cut.planned).toEqual([{ file: TEST, title: 'old cut', removes: true, text: 'held by the reference case' }]);
    expect(cut.deleted).toEqual([{ file: TEST, title: 'goes quietly' }]);
    expect(cut.untagged).toEqual([{ file: TEST, title: 'one more belt' }]);
  });

  it('stops counting a test once the file settles it, and tells no commit to follow a base it does not know', () => {
    write(TEST, tests(`it('demo#cut: lists two', () => {});`, `it('demo#cut: one more belt', () => {});`, `it('goes quietly', () => {});`));
    const cut = readPieceCommits('demo', base, repo).list[1];
    expect([cut.untagged, cut.deleted]).toEqual([[], []]);
    const unknown = readPieceCommits('demo', '0000000000000000000000000000000000000000', repo);
    expect([unknown.baseKnown, unknown.list.map((c) => c.sinceApproval)]).toEqual([false, [false, false]]);
  });

  it('reads what the lot comes to: a fix that renames a test the lot added neither adds nor deletes one', () => {
    write(TEST, tests(`it('demo#cut: lists two', () => {});`, `it('one more belt, renamed', () => {});`));
    commit('a fix\n\nPiece: demo#cut');
    const [, cut, fix] = readPieceCommits('demo', base, repo).list;
    expect([cut.untagged, cut.deleted]).toEqual([[], [{ file: TEST, title: 'goes quietly' }]]);
    expect([fix.untagged, fix.deleted]).toEqual([[{ file: TEST, title: 'one more belt, renamed' }], []]);
  });

  it('still reads as planned a retitle made in a fix, after the commit that made the change its comment planned', () => {
    const other = 'tests/y.test.ts';
    write(other, tests(`// ${TAG} demo#cut the case below also reads the cap`, `it('reads the three figures', () => {});`));
    const approved = commit('approved again');
    write(other, tests(`it('reads the three figures', () => { /* and the cap */ });`));
    commit('the case reads the cap\n\nPiece: demo#cut');
    write(other, tests(`it('reads the rule\'s figures', () => { /* and the cap */ });`));
    commit('its title no longer counts them\n\nPiece: demo#cut');
    const since = readPieceCommits('demo', approved, repo).list.filter((c) => c.sinceApproval);
    expect(since.map((c) => [c.untagged, c.deleted])).toEqual([[[], []], [[], []]]);
  });
});
