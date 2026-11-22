/**
 * backlinks — which token of a page names a file, which one `--check` takes for a declared symbol, and where
 * it looks for one that resolved to nothing (`../backlinks.ts`).
 *
 * What is worth fencing: that a file is named by a path of any folder and any language, the stack saying
 * whether it is a source file; that the shape of a declared symbol is not one language's naming style; and
 * that a word written in a file of any language the code folders hold is seen. No project's configuration is
 * read: the module is handed one here, and the page and the code it reads are written to a temporary folder.
 */
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { buildBacklinks, unresolvedDeclaredLooking, type BacklinkIndex, type PageEntry, type PageToken, type UnscopedResolver } from '../backlinks';

vi.mock('../config', () => ({
  config: { docs: 'docs', pagesNamingCode: [{ page: 'docs/conventions.md', kind: 'convention', split: 'heading' }], source: { words: ['app', 'tests'] } },
}));

describe('buildBacklinks', () => {
  let root = '';
  beforeAll(() => {
    root = mkdtempSync(join(tmpdir(), 'comprehension-backlinks-'));
    mkdirSync(join(root, 'docs'));
    writeFileSync(join(root, 'docs/conventions.md'), [
      '# Conventions',
      '',
      '## Pricing',
      '',
      'A discount is computed in `app/pricing.py:12-20` and drawn by `basket.ts`, never in `app/ui/`.',
      'A speed is in `km/h`, a total is `basket.total`, the rate is read from `settings.toml`.',
    ].join('\n'));
  });
  afterAll(() => rmSync(root, { recursive: true, force: true }));

  const SOURCE = ['app/pricing.py', 'app/ui/basket.ts', 'app/ui/index.ts', 'server/index.ts'];
  /** A stack's answer: a source file by its path, or by its name when one file alone has it. */
  const resolver: UnscopedResolver = {
    resolveUnscoped: () => null,
    sourceFile: (token) => {
      if (token.includes('/')) return SOURCE.includes(token) ? token : null;
      const named = SOURCE.filter((file) => file.endsWith(`/${token}`));
      return named.length === 1 ? named[0] : null;
    },
  };

  it('keys an entry by the source files it names, by a path from the root or by a name one file alone has', () => {
    const pricing = buildBacklinks(resolver, root).entries.find((entry) => entry.title === 'Pricing')!;
    expect([...pricing.keys]).toEqual(['app/pricing.py', 'app/ui/basket.ts']);
    expect(pricing.tokens.find((token) => token.raw === 'app/pricing.py:12-20')).toMatchObject({ name: 'app/pricing.py', shape: 'file', key: 'app/pricing.py' });
  });

  it('leaves what is written like a file and names no source file without a key', () => {
    const { entries, byKey } = buildBacklinks(resolver, root);
    const unplaced = entries.flatMap((entry) => entry.tokens).filter((token) => token.key === null).map((token) => token.raw);
    expect(unplaced).toEqual(['app/ui/', 'km/h', 'basket.total', 'settings.toml']);
    expect([...byKey.keys()]).toEqual(['app/pricing.py', 'app/ui/basket.ts']);
  });
});

describe('unresolvedDeclaredLooking', () => {
  let root = '';
  beforeAll(() => {
    root = mkdtempSync(join(tmpdir(), 'comprehension-backlinks-'));
    const write = (file: string, text: string) => {
      mkdirSync(dirname(join(root, file)), { recursive: true });
      writeFileSync(join(root, file), text);
    };
    write('app/pricing.py', 'def apply_discount(basket):\n    return basket.total * RATE_OF_DISCOUNT\n');
    write('app/basket.ts', 'export const emptyBasket = () => [];\n');
    write('tests/test_pricing.py', 'def test_a_discount():\n    assert apply_discount(basket) == 9\n');
    write('elsewhere/notes.py', 'renamed_helper = None\n');
  });
  afterAll(() => rmSync(root, { recursive: true, force: true }));

  const symbol = (name: string, key: string | null = null): PageToken => ({ raw: name, name, shape: 'symbol', key, at: null });
  const indexOf = (...tokens: PageToken[]): BacklinkIndex => {
    const entry: PageEntry = { kind: 'convention', page: 'docs/conventions.md', title: 'Pricing', lead: 'Pricing', line: 3, tokens, keys: new Set() };
    return { entries: [entry], byKey: new Map() };
  };
  // What a name is shaped like is the stack's to say; here a stack that declares in every style.
  const ANY_STYLE = /^(?:[A-Z][A-Za-z0-9]{2,}|[a-z][a-z0-9]*[A-Z][A-Za-z0-9]*|_*[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$/;
  const found = (...tokens: PageToken[]) => unresolvedDeclaredLooking(indexOf(...tokens), root, ANY_STYLE).map((u) => [u.token.name, u.appearsIn]);

  it('says in which code folders a word still appears, whatever language the file is written in', () => {
    expect(found(symbol('apply_discount'), symbol('RATE_OF_DISCOUNT'), symbol('emptyBasket'))).toEqual([
      ['apply_discount', ['app', 'tests']],
      ['RATE_OF_DISCOUNT', ['app']],
      ['emptyBasket', ['app']],
    ]);
  });

  it('lists a word no code folder holds as appearing nowhere', () => {
    expect(found(symbol('renamed_helper'), symbol('removedHelper'))).toEqual([['renamed_helper', []], ['removedHelper', []]]);
  });

  it('leaves out a token that resolved, one that is not shaped like a declared symbol, and a second mention in the entry', () => {
    expect(found(symbol('apply_discount', 'app/pricing.py#apply_discount'), symbol('total'), symbol('renamed_helper'), symbol('renamed_helper')))
      .toEqual([['renamed_helper', []]]);
  });
});
