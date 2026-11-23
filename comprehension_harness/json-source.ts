/**
 * json-source.ts — `SourceReader` (`stack.ts`) answered from a source index written as a document
 * (`SourceIndexDocument`): what a stack that does not run in Node gives the tools. Its command prints the
 * document; this file reads the tables.
 *
 * A stack with a compiler follows a name to its declaration by identity. Here the document's own tables say
 * where a name is declared (`imports`, `uses`), as far as the stack's parser could tell, and what the tables do
 * not hold is found by name, in the order `SourceReader.resolve` gives: an import of the file, a local of the
 * functions around the call (nearest first), a top-level declaration of the file, one unique across the source.
 * Two methods of one name on two classes can be taken for each other; the remedy is the qualified name in the
 * sentence.
 *
 * A document that is not of the shape `stack.ts` gives stops the tool, naming the file and the table.
 */
import { execFileSync } from 'node:child_process';
import { PLANNED_CHANGES } from './stack';
import type { Around, Declaration, Location, Neighbour, RawSite, Resolution, SourceFileIndex, SourceIndexDocument, SourceReader } from './stack';

const IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;
const TABLES = ['sites', 'functions', 'declarations', 'imports', 'locals', 'uses'] as const;
/** A name is ambient when this many files use it (a logger, a helper everything calls): not a neighbour worth listing. */
const AMBIENT_FILES = 12;
const THE_CALLS = ['narrate', 'event', 'planned', 'canonical'];

type Fn = SourceFileIndex['functions'][number] & { file: string };
const same = (a: Location, b: Location) => a.file === b.file && a.line === b.line && a.column === b.column;
const holds = (fn: { line: number; endLine: number }, line: number) => fn.line <= line && line <= fn.endLine;

/** Refuses a document that is not one, naming what is wrong: nothing of it is skipped. */
export function checkSourceIndex(document: unknown, from: string): SourceIndexDocument {
  const fail = (what: string): never => { throw new Error(`comprehension-source: ${from} — ${what}`); };
  const doc = document as Partial<SourceIndexDocument> | null;
  if (doc === null || typeof doc !== 'object') return fail('the source index is not an object');
  if (!Array.isArray(doc.narratives)) return fail('"narratives" is not a list');
  try {
    if (typeof doc.looksDeclared !== 'string') throw new Error('not a string');
    new RegExp(doc.looksDeclared);
  } catch (error) {
    return fail(`"looksDeclared" is not the source of a regular expression, the shape of a name the language declares — ${(error as Error).message}`);
  }
  for (const n of doc.narratives) if (typeof n?.file !== 'string' || typeof n.title !== 'string' || typeof n.line !== 'number' || typeof n.summary !== 'string') fail(`a narrative is not { file, title, line, summary, firstTest }: ${JSON.stringify(n)}`);
  if (doc.files === null || typeof doc.files !== 'object' || Array.isArray(doc.files)) return fail('"files" is not an object, a file each');
  for (const [file, tables] of Object.entries(doc.files)) {
    for (const table of TABLES) if (!Array.isArray((tables as Partial<SourceFileIndex>)?.[table])) fail(`"${table}" of ${file} is not a list`);
    for (const site of tables.sites) {
      if (!['step', 'event', 'planned'].includes(site.kind) || typeof site.line !== 'number' || typeof site.column !== 'number' || typeof site.fn !== 'string') fail(`a site of ${file} is not { kind, line, column, fn, sentence }: ${JSON.stringify(site)}`);
      if (site.kind === 'planned' && (site.sentence === null || typeof site.planned?.feature !== 'string' || typeof site.planned.slug !== 'string' || !PLANNED_CHANGES.includes(site.planned.change))) {
        fail(`the planned call at ${file}:${site.line} needs a literal sentence and "planned": { feature, slug, change, signature }`);
      }
    }
    for (const fn of tables.functions) if (typeof fn.fn !== 'string' || typeof fn.line !== 'number' || typeof fn.endLine !== 'number') fail(`a function of ${file} is not { fn, line, column, endLine }: ${JSON.stringify(fn)}`);
  }
  return doc as SourceIndexDocument;
}

/** A reader over what `command` prints, run again by `fresh()`. `isSource` tells the product's source files from
 *  the test files the document lists for their narratives. */
export function openJsonSource(command: readonly string[], cwd: string, isSource: (file: string) => boolean): SourceReader {
  const [program, ...args] = command;
  const printed = execFileSync(program, args, { cwd, encoding: 'utf8', maxBuffer: 1024 * 1024 * 1024 });
  const named = `what \`${command.join(' ')}\` printed`;
  let document: unknown;
  try { document = JSON.parse(printed); } catch (error) { throw new Error(`comprehension-source: ${named} is not JSON — ${(error as Error).message}`); }
  return new JsonSource(checkSourceIndex(document, named), isSource, () => openJsonSource(command, cwd, isSource));
}

export class JsonSource implements SourceReader {
  readonly looksDeclared: RegExp;
  private declaredByName: Map<string, Location[]> | null = null;
  private filesUsing: Map<string, Set<string>> | null = null;

  constructor(
    private readonly document: SourceIndexDocument,
    private readonly isSource: (file: string) => boolean,
    private readonly reopen: () => SourceReader = () => this,
  ) {
    this.looksDeclared = new RegExp(document.looksDeclared);
  }

  fresh(): SourceReader {
    return this.reopen();
  }

  private tables(file: string): SourceFileIndex {
    const tables = this.document.files[file];
    if (!tables) throw new Error(`comprehension-source: ${file} is not in the source index — a story names a site outside it`);
    return tables;
  }

  sites(file: string): RawSite[] {
    return this.tables(file).sites.map((s): RawSite => ({
      file, line: s.line, column: s.column, kind: s.kind, fn: s.fn, sentence: s.sentence,
      ...(s.planned ? { planned: { ...s.planned, sentence: s.sentence! } } : {}),
    }));
  }

  sourceFiles(): string[] {
    return Object.keys(this.document.files).filter((file) => this.isSource(file));
  }

  siteFiles(): string[] {
    return this.sourceFiles().filter((file) => this.document.files[file].sites.length > 0);
  }

  narrativeTestFiles(): string[] {
    return [...new Set(this.document.narratives.map((n) => n.file))].sort();
  }

  declaration(file: string, title: string): Declaration {
    const found = this.document.narratives.find((n) => n.file === file && n.title === title);
    if (!found) throw new Error(`comprehension-source: ${file} declares no narrative titled "${title}" — a story is older than the source; re-run its test`);
    return { summary: found.summary, firstTest: found.firstTest, line: found.line };
  }

  /** The functions of a file whose lines hold `line`, the innermost first. */
  private around_(file: string, line: number): Fn[] {
    return this.document.files[file].functions.filter((fn) => holds(fn, line)).sort((a, b) => b.line - a.line).map((fn) => ({ ...fn, file }));
  }

  /** Every top-level declaration of the source, by name: rule 3's index. */
  private declared(): Map<string, Location[]> {
    if (this.declaredByName) return this.declaredByName;
    const index = new Map<string, Location[]>();
    for (const file of this.sourceFiles()) for (const d of this.document.files[file].declarations) index.set(d.name, [...(index.get(d.name) ?? []), { file, line: d.line, column: d.column }]);
    return (this.declaredByName = index);
  }

  resolve(site: RawSite, name: string): Resolution {
    if (!IDENTIFIER.test(name)) return { linked: false, reason: 'not an identifier' };
    const tables = this.tables(site.file);
    const at = (x: { line: number; column: number }): Location => ({ file: site.file, line: x.line, column: x.column });
    // 1. an import of the site's file → the declaration in the imported module
    const imported = tables.imports.find((i) => i.name === name);
    if (imported) return { linked: true, rule: 1, at: imported.at };
    // 1b. a local of the functions around the call, nearest first
    for (const fn of this.around_(site.file, site.line)) {
      const local = tables.locals.find((l) => l.name === name && holds(fn, l.line));
      if (local) return { linked: true, rule: '1b', at: at(local) };
    }
    // 2. a top-level declaration of the site's file
    const own = tables.declarations.find((d) => d.name === name);
    if (own) return { linked: true, rule: 2, at: at(own) };
    // 3. a top-level declaration of that name, unique across the source
    const declared = this.declared().get(name) ?? [];
    if (declared.length === 1) return { linked: true, rule: 3, at: declared[0] };
    // 4. otherwise, plain code — with the reason, for `--check`
    if (declared.length > 1) return { linked: false, reason: `declared at top level in ${declared.length} places: ${declared.map((l) => `${l.file}:${l.line}`).join(', ')}` };
    const elsewhere = tables.locals.find((l) => l.name === name);
    if (elsewhere) return { linked: false, reason: `a local of ${this.around_(site.file, elsewhere.line)[0]?.fn ?? '(module)'}, not of ${site.fn} (${site.file}:${elsewhere.line})` };
    return { linked: false, reason: 'no declaration of that name in the source' };
  }

  resolveUnscoped(name: string, files: readonly string[]): Location | null {
    if (!IDENTIFIER.test(name)) return null;
    for (const file of files) {
      const own = this.document.files[file]?.declarations.find((d) => d.name === name);
      if (own) return { file, line: own.line, column: own.column };
    }
    const declared = this.declared().get(name) ?? [];
    return declared.length === 1 ? declared[0] : null;
  }

  resolveNear(name: string, places: ReadonlyArray<{ file: string; line: number }>): Location | null {
    if (!IDENTIFIER.test(name)) return null;
    let best: { at: Location; distance: number } | null = null;
    for (const file of new Set(places.map((p) => p.file))) {
      const tables = this.document.files[file];
      if (!tables) continue;
      const lines = places.filter((p) => p.file === file).map((p) => p.line);
      for (const d of [...tables.declarations, ...tables.locals].sort((a, b) => a.line - b.line || a.column - b.column)) {
        if (d.name !== name) continue;
        const distance = Math.min(...lines.map((l) => Math.abs(l - d.line)));
        if (!best || distance < best.distance) best = { at: { file, line: d.line, column: d.column }, distance };
      }
    }
    return best?.at ?? null;
  }

  /** The first reference, inside a function, to the symbol declared at `at`. */
  private firstUse(fn: Fn, name: string, at: Location): Location | null {
    const use = this.document.files[fn.file].uses
      .filter((u) => u.name === name && holds(fn, u.line) && same(u.at, at))
      .sort((a, b) => a.line - b.line || a.column - b.column)[0];
    return use ? { file: fn.file, line: use.line, column: use.column } : null;
  }

  useSite(site: RawSite, name: string, at: Location): Location | null {
    this.tables(site.file);
    const fn = this.around_(site.file, site.line)[0];
    return fn ? this.firstUse(fn, name, at) : null;
  }

  useIn(file: string, fn: string, name: string, at: Location): Location | null {
    const named = (this.document.files[file]?.functions ?? []).filter((f) => f.fn === fn);
    return named.length === 1 ? this.firstUse({ ...named[0], file }, name, at) : null;
  }

  sourceFile(token: string): string | null {
    const files = this.sourceFiles();
    if (token.includes('/')) return files.includes(token) ? token : null;
    const matches = files.filter((file) => file.slice(file.lastIndexOf('/') + 1) === token);
    return matches.length === 1 ? matches[0] : null;
  }

  /** Every function of the source with its file. */
  private functions(): Fn[] {
    return this.sourceFiles().flatMap((file) => this.document.files[file].functions.map((fn) => ({ ...fn, file })));
  }

  /** Whether a function holds a `narrate` of its own: a step whose innermost function it is. */
  private narrated(fn: Fn): boolean {
    return this.document.files[fn.file].sites.some((s) => s.kind === 'step' && this.around_(fn.file, s.line)[0]?.line === fn.line);
  }

  private neighbour(fn: Fn): Neighbour {
    return { file: fn.file, line: fn.line, fn: fn.fn, narrated: this.narrated(fn) };
  }

  /** The functions that refer to `target`: one of their own references is declared where its name is. */
  private referrers(target: Fn): Fn[] {
    const at: Location = { file: target.file, line: target.line, column: target.column };
    const out: Fn[] = [];
    for (const file of this.sourceFiles()) for (const use of this.document.files[file].uses) {
      if (!same(use.at, at)) continue;
      const owner = this.around_(file, use.line)[0];
      if (owner && !(owner.file === target.file && owner.line === target.line) && !out.some((x) => x.file === owner.file && x.line === owner.line)) out.push(owner);
    }
    return out;
  }

  around(site: RawSite): Around | null {
    this.tables(site.file);
    const target = this.around_(site.file, site.line)[0];
    if (!target) return null;
    const unique = (list: Neighbour[]) => [...new Map(list.map((n) => [`${n.file}#${n.fn}`, n])).values()].sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
    // Who refers to it, and who refers to those of them that hold no `narrate`: the walk stops at narrated code.
    const first = this.referrers(target);
    const callers: Neighbour[] = first.map((fn) => this.neighbour(fn));
    for (const owner of first) {
      if (this.narrated(owner)) continue;
      for (const second of this.referrers(owner)) {
        if (second.file === target.file && second.line === target.line) continue;
        callers.push({ ...this.neighbour(second), how: `via ${owner.fn}` });
      }
    }
    // What it calls or hands on: its references declared as a function of the source.
    if (!this.filesUsing) {
      this.filesUsing = new Map();
      for (const file of this.sourceFiles()) for (const use of this.document.files[file].uses) this.filesUsing.set(use.name, (this.filesUsing.get(use.name) ?? new Set<string>()).add(file));
    }
    const functions = this.functions();
    const callees: Neighbour[] = [];
    for (const use of this.document.files[target.file].uses) {
      if (!holds(target, use.line) || THE_CALLS.includes(use.name) || (this.filesUsing.get(use.name)?.size ?? 0) > AMBIENT_FILES) continue;
      const callee = functions.find((fn) => same({ file: fn.file, line: fn.line, column: fn.column }, use.at));
      if (callee && !(callee.file === target.file && callee.line === target.line)) callees.push(this.neighbour(callee));
    }
    return { range: [target.line, target.endLine], callers: unique(callers), callees: unique(callees) };
  }
}
