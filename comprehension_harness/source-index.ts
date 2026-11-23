/**
 * source-index.ts — the sites of the source with their identity, over what a stack's `SourceReader` reads
 * (`stack.ts`). The reader says where the calls are; what a site is to the tools is decided here, once for
 * every stack:
 *
 *  - a step's identity is derived, `<file>#<function>#<ordinal>`: the ordinal counts the `narrate` and `event`
 *    sites of one function in source order, so a story's hit is matched to a step by its call site alone;
 *  - a site a run recorded at a line that has since moved is found again by its sentence (`siteNow`, `realign`).
 *
 * Every other question goes to the reader as it is asked.
 */
import type { Around, Declaration, Location, RawSite, Resolution, SourceReader, Story, StoryFrame } from './stack';

export interface SourceSite extends RawSite {
  /** Among the `narrate`/`event` sites of the function; 0 for a planned site, which its piece's slug names. */
  ordinal: number;
  /** `<file>#<function>#<ordinal>`; `planned:<feature>#<slug>@<file>:<line>` for a planned site (a piece has several). */
  id: string;
}

export class SourceIndex {
  private readonly sitesByFile = new Map<string, Map<number, SourceSite>>();

  constructor(private readonly reader: SourceReader) {}

  /** The shape of a name the stack's language declares (`SourceReader.looksDeclared`). */
  get looksDeclared(): RegExp {
    return this.reader.looksDeclared;
  }

  /** The `narrate`, `event` and `planned` sites of a file, keyed by line, each with its function and ordinal. */
  sites(file: string): Map<number, SourceSite> {
    let sites = this.sitesByFile.get(file);
    if (sites) return sites;
    const found = this.reader.sites(file);
    sites = new Map();
    const byFn = new Map<string, RawSite[]>();
    for (const s of found) {
      if (s.kind === 'planned') {
        const planned = s.planned!;
        sites.set(s.line, { ...s, ordinal: 0, id: `planned:${planned.feature}#${planned.slug}@${s.file}:${s.line}` });
      } else {
        byFn.set(s.fn, [...(byFn.get(s.fn) ?? []), s]);
      }
    }
    for (const [fn, list] of byFn) {
      list.sort((a, b) => a.line - b.line);
      list.forEach((s, i) => sites!.set(s.line, { ...s, ordinal: i + 1, id: `${s.file}#${fn}#${i + 1}` }));
    }
    this.sitesByFile.set(file, sites);
    return sites;
  }

  /** Every `planned` call of the source, by file then line — the plan pages' and the archive gate's input. */
  plannedSites(): SourceSite[] {
    const out: SourceSite[] = [];
    for (const file of this.reader.sourceFiles()) {
      for (const site of this.sites(file).values()) if (site.kind === 'planned') out.push(site);
    }
    return out.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
  }

  /**
   * Where the site a run recorded at `file:line` is now. A run names a site by its line, and a line moves
   * whenever anything is added above it — a `planned` call, a comment — while the call itself has not changed.
   * So a recorded site is first looked for at its line, holding the sentence the run recorded; failing that, it
   * is the one call of the file, of that kind, with that sentence. Null when neither: the call was removed, its
   * sentence was rewritten, or two calls of the file say the same thing — then the run is truly older than the
   * source and its test must run again.
   */
  siteNow(file: string, line: number, kind: SourceSite['kind'], sentence: string): SourceSite | null {
    let sites: Map<number, SourceSite>;
    try { sites = this.sites(file); } catch { return null; }
    const at = sites.get(line);
    if (at && at.kind === kind && (at.sentence ?? sentence) === sentence) return at;
    const same = [...sites.values()].filter((x) => x.kind === kind && x.sentence === sentence);
    return same.length === 1 ? same[0] : at && at.kind === kind ? at : null;
  }

  /** Moves every hit of `stories` whose site has shifted to where that site is now (`siteNow`), in place;
   *  returns how many moved. Called once, right after the stories are read: everything downstream names a
   *  site by `hit.site`, and then a story stays good across an edit that only moves lines. */
  realign(stories: Story[]): number {
    let moved = 0;
    for (const story of stories) for (const hit of story.hits) {
      const now = this.siteNow(hit.site.file, hit.site.line, hit.kind, hit.sentence);
      if (!now || now.line === hit.site.line) continue;
      hit.site = { ...hit.site, line: now.line, column: now.column };
      moved += 1;
    }
    return moved;
  }

  /** The derived identity of a story's call site. Loud when the story is stale. */
  identity(site: StoryFrame): SourceSite {
    const found = this.sites(site.file).get(site.line);
    if (!found) throw new Error(`comprehension-render: no narrate/event call at ${site.file}:${site.line} — the story is older than the source; re-run its test`);
    return found;
  }

  /** How many narrate sites the function of a site has (one → the ordinal can be left unsaid). */
  siblings(site: SourceSite): number {
    return [...this.sites(site.file).values()].filter((s) => s.fn === site.fn && s.kind !== 'planned').length;
  }

  /** The `narrate` sites of every source file under one of `folders` — the mechanism folders `--check` sweeps. */
  sitesUnder(folders: string[]): SourceSite[] {
    const out: SourceSite[] = [];
    for (const file of this.reader.sourceFiles()) {
      if (!folders.some((f) => file.startsWith(f))) continue;
      for (const site of this.sites(file).values()) if (site.kind === 'step') out.push(site);
    }
    return out.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
  }

  // What follows is the reader's, asked as it is (`SourceReader` says what each answers).

  declaration(file: string, title: string): Declaration { return this.reader.declaration(file, title); }
  resolve(site: RawSite, name: string): Resolution { return this.reader.resolve(site, name); }
  resolveUnscoped(name: string, files: readonly string[]): Location | null { return this.reader.resolveUnscoped(name, files); }
  resolveNear(name: string, places: ReadonlyArray<{ file: string; line: number }>): Location | null { return this.reader.resolveNear(name, places); }
  useSite(site: RawSite, name: string, at: Location): Location | null { return this.reader.useSite(site, name, at); }
  useIn(file: string, fn: string, name: string, at: Location): Location | null { return this.reader.useIn(file, fn, name, at); }
  sourceFile(token: string): string | null { return this.reader.sourceFile(token); }
  around(site: RawSite): Around | null { return this.reader.around(site); }
  lines(file: string, fn: string): [number, number] | null { return this.reader.lines?.(file, fn) ?? null; }
  siteFiles(): string[] { return this.reader.siteFiles(); }
  narrativeTestFiles(): string[] { return this.reader.narrativeTestFiles(); }
}
