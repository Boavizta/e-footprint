/**
 * intent-md.ts — a feature's hand-written markdown (`specs/features/<feature>/spec.md`, `plan.md`) as data.
 *
 * Both files hold what has no line in the code or in a test: a `# ` title, the lines under it (the lead), then
 * one `## ` section per topic. A section holds paragraphs and `- ` lists and nothing else — what has a structure
 * is declared where it runs (a journey test, a `planned` site) and the page is rendered from there.
 *
 * A list item may open with a bold kebab-case slug, `- **rule-is-the-judge** The rule stays…`: the item's
 * name, by which a test claims it (`comprehension_harness/plan.ts`, the ownership check). The slug is parsed off the
 * text and drawn as a chip.
 *
 * One parser for the two renderers: `comprehension_harness/journey-render.ts` (the spec page) and `comprehension_harness/render.ts`
 * (the plan page).
 */

export interface MdItem {
  /** The item's text, its slug taken off, continuation lines joined. Markdown-lite, not yet HTML. */
  text: string;
  /** 1-based, the line the item opens on. */
  line: number;
  /** The bold kebab-case word the item opens with, if any. */
  slug: string | null;
}

export type MdBlock =
  | { kind: 'p'; text: string; line: number }
  | { kind: 'ul'; items: MdItem[] };

export interface MdSection {
  title: string;
  line: number;
  blocks: MdBlock[];
}

export interface Intent {
  title: string;
  /** What stands between the title and the first section. */
  lead: MdBlock[];
  sections: MdSection[];
}

const ITEM_SLUG = /^\*\*([a-z0-9]+(?:-[a-z0-9]+)*)\*\*\s+/;
/** A heading deeper than `##`, a table, a code fence, a numbered list: structure the file does not hold. */
const NOT_PROSE = /^(#{1,6}\s|\||```|\d+\. )/;

function blocksOf(lines: Array<{ text: string; line: number }>, file: string): MdBlock[] {
  const out: MdBlock[] = [];
  let para: { text: string[]; line: number } | null = null;
  let items: Array<{ text: string[]; line: number }> = [];
  const flush = () => {
    if (para) out.push({ kind: 'p', text: para.text.join(' '), line: para.line });
    if (items.length) {
      out.push({
        kind: 'ul',
        items: items.map((i) => {
          const text = i.text.join(' ');
          const m = ITEM_SLUG.exec(text);
          return { text: m ? text.slice(m[0].length) : text, line: i.line, slug: m ? m[1] : null };
        }),
      });
    }
    para = null;
    items = [];
  };
  for (const { text, line } of lines) {
    if (NOT_PROSE.test(text)) throw new Error(`${file}:${line} — "${text.slice(0, 40)}": a section holds paragraphs and "- " lists only`);
    if (text.trim() === '') flush();
    else if (text.startsWith('- ')) {
      if (para) flush();
      items.push({ text: [text.slice(2).trim()], line });
    } else if (items.length && /^\s/.test(text)) items[items.length - 1].text.push(text.trim());
    else {
      if (items.length) flush();
      para = para ?? { text: [], line };
      para.text.push(text.trim());
    }
  }
  flush();
  return out;
}

/** `file` is named in the errors only; nothing is read here. */
export function parseIntent(text: string, file: string): Intent {
  const lines = text.split('\n').map((t, i) => ({ text: t, line: i + 1 }));
  if (!lines[0].text.startsWith('# ')) throw new Error(`${file}:1 — the file must open with its "# " title`);
  const sections: Array<{ title: string; line: number; lines: typeof lines }> = [{ title: '', line: 1, lines: [] }];
  for (const l of lines.slice(1)) {
    if (l.text.startsWith('## ')) sections.push({ title: l.text.slice(3).trim(), line: l.line, lines: [] });
    else sections[sections.length - 1].lines.push(l);
  }
  return {
    title: lines[0].text.slice(2).trim(),
    lead: blocksOf(sections[0].lines, file),
    sections: sections.slice(1).map((s) => ({ title: s.title, line: s.line, blocks: blocksOf(s.lines, file) })),
  };
}

/** The slugged items of the section titled `title`, in order; empty when the file has no such section. */
export function sluggedItems(intent: Intent, title: string): MdItem[] {
  const section = intent.sections.find((s) => s.title === title);
  if (!section) return [];
  return section.blocks.flatMap((b) => (b.kind === 'ul' ? b.items.filter((i) => i.slug !== null) : []));
}

/**
 * Blocks as HTML. `inline` turns a paragraph's or an item's markdown-lite text into HTML (each page has its own
 * links to make); an item's slug is drawn before its text as `<span class="slug">`, with `id="<slug>"` so a page
 * can link the item.
 */
export function blocksHtml(blocks: MdBlock[], inline: (text: string) => string): string {
  return blocks.map((b) => (b.kind === 'p'
    ? `<p>${inline(b.text)}</p>`
    : `<ul>${b.items.map((i) => (i.slug ? `<li id="${i.slug}"><span class="slug">${i.slug}</span> ${inline(i.text)}</li>` : `<li>${inline(i.text)}</li>`)).join('')}</ul>`)).join('');
}
