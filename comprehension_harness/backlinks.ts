/**
 * backlinks.ts — the pages that name code, indexed.
 *
 * A step should show which open debt, which constitution rule and which convention apply at
 * its line, and nobody should write that link. The three pages already name the code they are
 * about in backticks; this module reads them, splits each into entries, resolves every
 * backticked token the way a sentence's symbols are resolved — with no step scope: a top-level
 * declaration of a source file the same entry names, else one unique across the source; a source
 * file's path (or a unique basename) to the file — and builds a map from symbol or file to the entries
 * that name it. The renderer marks a step whose function, file, or linked sentence symbol the
 * map names, and `--check` prints the two informative lists.
 *
 * The entry split differs per page, since the pages are shaped differently:
 *  - `tech-debt.md` is list-structured: an entry is a top-level list item (`- **lead.** …`) with
 *    its indented continuation and nested items; the title is the bold lead;
 *  - the constitution's rules are bold-led paragraphs (`**1.12 …**`) under `## §1`, neither
 *    headings nor list items: an entry is one such paragraph and what follows it until the next;
 *    the title is `§1.12`; the other sections are entries by heading;
 *  - `conventions.md` is heading-structured: an entry is the nearest enclosing heading.
 * Every page's text outside a sub-entry belongs to its nearest heading.
 *
 * An entry is reached by its line in the markdown file (through `data-review-source-href`, so
 * `review-links.js` opens it in VS Code): none of the three files carries an id of its own (the
 * constitution's `§1.12` is text, not a mark), and a browser link to the `.md` only shows plain
 * text.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { config, type PageNamingCode } from './config';
import type { Location } from './stack';

export type PageKind = PageNamingCode['kind'];

type PageSpec = PageNamingCode;

/** The pages whose entries name code, read in this order (`pagesNamingCode` of the configuration). */
export const PAGES: readonly PageSpec[] = config.pagesNamingCode;

export type { Location };

/** What the index asks of the source (`SourceIndex` answers it). */
export interface UnscopedResolver {
  /** Rules 2 and 3 with no step scope: a top-level declaration in one of `files`, else one unique across the source. */
  resolveUnscoped(name: string, files: readonly string[]): Location | null;
  /** The source file a path or a unique basename names; null for a folder, a glob or a file outside the program. */
  sourceFile(token: string): string | null;
}

export interface PageToken {
  raw: string;
  /** The identifier, path or basename the raw token reduces to; null when it is none of those. */
  name: string | null;
  shape: 'symbol' | 'file' | 'other';
  /** `<file>#<name>` for a symbol, `<file>` for a file; null when unresolved. */
  key: string | null;
  at: Location | null;
}

export interface PageEntry {
  kind: PageKind;
  page: string;
  /** The marker's text: the bold lead of a list item, `§1.N` for a rule, the heading's text for a section. */
  title: string;
  /** The entry's first line, plain, for the tooltip. */
  lead: string;
  line: number;
  tokens: PageToken[];
  keys: Set<string>;
}

export interface BacklinkIndex {
  entries: PageEntry[];
  /** symbol (`<file>#<name>`) or file → the entries that name it, in page order. */
  byKey: Map<string, PageEntry[]>;
}

const IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

// ── Splitting ──────────────────────────────────────────────────────────────────

interface RawEntry {
  kind: PageKind;
  page: string;
  level: 'heading' | 'sub';
  headingText: string;
  firstLine: string;
  line: number;
  lines: string[];
}

function splitEntries(spec: PageSpec, root: string): RawEntry[] {
  const lines = readFileSync(join(root, spec.page), 'utf8').split('\n');
  const entries: RawEntry[] = [];
  let heading: RawEntry | null = null;
  let sub: RawEntry | null = null;
  let fence = false;
  lines.forEach((line, i) => {
    if (/^\s*```/.test(line)) {
      fence = !fence;
      return;
    }
    if (fence) return; // a fenced block is code, not a name
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    if (h) {
      heading = { kind: spec.kind, page: spec.page, level: 'heading', headingText: h[2], firstLine: h[2], line: i + 1, lines: [] };
      sub = null;
      entries.push(heading);
      return;
    }
    if (!heading) return;
    const opens = spec.split === 'list' ? /^- /.test(line) : spec.split === 'rule' ? /^\*\*\d+\.\d+ /.test(line) : false;
    if (opens) {
      sub = { kind: spec.kind, page: spec.page, level: 'sub', headingText: heading.headingText, firstLine: line, line: i + 1, lines: [] };
      entries.push(sub);
    } else if (spec.split === 'list' && sub && line.trim() && !/^\s/.test(line)) {
      sub = null; // an unindented paragraph ends the item
    }
    (sub ?? heading).lines.push(line);
  });
  return entries;
}

// ── Titles and leads ───────────────────────────────────────────────────────────

/** Markdown-lite stripped: bold, backticks, links. */
const plain = (md: string) => md.replace(/\*\*/g, '').replace(/`/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').trim();

function shorten(s: string, max = 64): string {
  if (s.length <= max) return s;
  const cut = s.slice(0, max).replace(/\s+\S*$/, '');
  return `${cut}…`;
}

function titleOf(spec: PageSpec, e: RawEntry): string {
  if (e.level === 'heading') return plain(e.headingText);
  if (spec.split === 'rule') return `§${/^\*\*(\d+\.\d+) /.exec(e.firstLine)![1]}`;
  const bold = /^- \*\*(.+?)\*\*/.exec(e.firstLine);
  const lead = plain(bold ? bold[1] : e.firstLine.replace(/^- /, ''));
  return shorten(lead.split(/:| — /)[0].replace(/\.$/, ''));
}

function leadOf(e: RawEntry): string {
  return plain(e.firstLine.replace(/^- /, ''));
}

// ── Tokens ─────────────────────────────────────────────────────────────────────

/** A token written like a file, with the line or the lines that may follow it (`:12`, `:12-20`): a path from
 *  the root, or a file's name with its extension. Which folders hold the source and in which languages is not
 *  read here: the stack says whether the token names a source file (`sourceFile`), and one that names none
 *  (a folder, a unit like `km/h`, `object.field`) resolves to nothing. */
const PATH_TOKEN = /^(\w[\w.-]*\/[\w./-]*?)(?::\d+(?:-\d+)?)?$/;
const BASENAME_TOKEN = /^(\w[\w.-]*\.[A-Za-z]\w*)(?::\d+(?:-\d+)?)?$/;

function tokenShape(raw: string): { name: string | null; shape: PageToken['shape'] } {
  let t = raw.trim();
  const call = /^([A-Za-z_$][\w$]*)\([^)]*\)$/.exec(t);
  if (call) t = call[1];
  const file = PATH_TOKEN.exec(t) ?? BASENAME_TOKEN.exec(t);
  if (file) return { name: file[1], shape: 'file' };
  if (IDENTIFIER.test(t)) return { name: t, shape: 'symbol' };
  return { name: null, shape: 'other' };
}

function tokensOf(lines: string[]): string[] {
  const out: string[] = [];
  for (const line of lines) for (const m of line.matchAll(/`([^`]+)`/g)) out.push(m[1]);
  return out;
}

// ── The index ──────────────────────────────────────────────────────────────────

export function buildBacklinks(resolver: UnscopedResolver, root: string): BacklinkIndex {
  const entries: PageEntry[] = [];
  const byKey = new Map<string, PageEntry[]>();
  for (const spec of PAGES) {
    for (const raw of splitEntries(spec, root)) {
      const tokens: PageToken[] = tokensOf(raw.lines).map((t) => ({ raw: t, ...tokenShape(t), key: null, at: null }));
      // Files first: a symbol resolves against the files its own entry names (rule 2).
      const files: string[] = [];
      for (const t of tokens) {
        if (t.shape !== 'file' || t.name === null) continue;
        const file = resolver.sourceFile(t.name);
        if (file === null) continue;
        t.key = file;
        t.at = { file, line: 1, column: 1 };
        if (!files.includes(file)) files.push(file);
      }
      for (const t of tokens) {
        if (t.shape !== 'symbol' || t.name === null) continue;
        const at = resolver.resolveUnscoped(t.name, files);
        if (at === null) continue;
        t.at = at;
        t.key = `${at.file}#${t.name}`;
      }
      const entry: PageEntry = {
        kind: spec.kind, page: spec.page,
        title: titleOf(spec, raw), lead: leadOf(raw), line: raw.line,
        tokens, keys: new Set(tokens.map((t) => t.key).filter((k): k is string => k !== null)),
      };
      entries.push(entry);
      for (const key of entry.keys) byKey.set(key, [...(byKey.get(key) ?? []), entry]);
    }
  }
  return { entries, byKey };
}

/** One step's keys: its function, its file, and the symbols its sentence links. */
export interface StepKeys {
  fn: string;
  file: string;
  /** `<file>#<name>` of each linked sentence symbol, with the name as written. */
  linked: Array<{ key: string; name: string }>;
}

export interface Marker {
  entry: PageEntry;
  /** How the entry reaches the step: by its function (the strong tier), by its file, or by a symbol its
   *  sentence links — the two weaker tiers, which the page draws dashed. */
  via: { tier: 'fn' | 'file' | 'sentence'; text: string };
}

/** The entries that name a step, each once, by the strongest tier that reaches it (function, then file, then sentence). */
export function markersFor(index: BacklinkIndex, step: StepKeys): Marker[] {
  const out = new Map<PageEntry, Marker['via']>();
  const add = (key: string, via: Marker['via']) => {
    for (const e of index.byKey.get(key) ?? []) if (!out.has(e)) out.set(e, via);
  };
  add(`${step.file}#${step.fn}`, { tier: 'fn', text: `names \`${step.fn}\`` });
  add(step.file, { tier: 'file', text: `names \`${step.file}\`` });
  for (const { key, name } of step.linked) add(key, { tier: 'sentence', text: `names \`${name}\`, which the sentence links` });
  return [...out].map(([entry, via]) => ({ entry, via }));
}

// ── `--check` ──────────────────────────────────────────────────────────────────

const CODE_FOLDERS = config.source.words;
const CODE_EXT = /\.(?:[cm]?[jt]sx?|py|sql|json|toml|css|html|md)$/;

/** Every identifier-shaped word in the code folders, with the top folders it appears in — so a token
 *  that resolves to nothing can be told apart: absent from the code altogether (stale), or present but
 *  not as a top-level declaration of the source (a local, a property, a column, declared elsewhere). */
function codeWords(root: string): Map<string, Set<string>> {
  const words = new Map<string, Set<string>>();
  const walk = (dir: string, top: string): void => {
    for (const entry of readdirSync(dir)) {
      if (entry === 'node_modules' || entry.startsWith('.')) continue;
      const p = join(dir, entry);
      if (statSync(p).isDirectory()) walk(p, top);
      else if (CODE_EXT.test(entry)) {
        for (const m of readFileSync(p, 'utf8').matchAll(/[A-Za-z_$][\w$]{2,}/g)) {
          const seen = words.get(m[0]) ?? new Set<string>();
          seen.add(top);
          words.set(m[0], seen);
        }
      }
    }
  };
  for (const top of CODE_FOLDERS) walk(join(root, top), top);
  return words;
}

export interface Unresolved {
  entry: PageEntry;
  token: PageToken;
  /** The top folders the word appears in; empty when it appears nowhere — the stale candidate. */
  appearsIn: string[];
}

/** List 1: a token that looks declared and resolved to nothing, with where (if anywhere) the word still appears. */
export function unresolvedDeclaredLooking(index: BacklinkIndex, root: string, looksDeclared: RegExp): Unresolved[] {
  const words = codeWords(root);
  const out: Unresolved[] = [];
  const seen = new Set<string>();
  for (const entry of index.entries) {
    for (const token of entry.tokens) {
      if (token.shape !== 'symbol' || token.name === null || token.key !== null || !looksDeclared.test(token.name)) continue;
      const dedupe = `${entry.page}:${entry.line}:${token.name}`;
      if (seen.has(dedupe)) continue;
      seen.add(dedupe);
      out.push({ entry, token, appearsIn: [...(words.get(token.name) ?? [])].sort() });
    }
  }
  return out;
}

/** List 2: an entry whose resolved symbols and files no story's hit or frame ever touched. */
export function untracedEntries(index: BacklinkIndex, hitKeys: ReadonlySet<string>): PageEntry[] {
  return index.entries.filter((e) => e.keys.size > 0 && ![...e.keys].some((k) => hitKeys.has(k)));
}

export const describeEntry = (e: PageEntry) => `${e.kind} · ${e.title} (${relative(config.docs, e.page)}:${e.line})`;
