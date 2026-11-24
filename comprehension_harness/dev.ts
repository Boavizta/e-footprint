/**
 * dev.ts — `npm run comprehension`: the narrative page kept live.
 *
 * One process, three parts:
 *  - the tests' watch command on every test file that declares a narrative (found in the
 *    source, `SourceReader.narrativeTestFiles`), so every save of a narrated file or of a test re-runs
 *    it and the collector rewrites its stories;
 *  - a watcher on the stories folder (under the project's cache) that re-renders the
 *    pages when a test file's stories land (debounced, since one run writes one file per test file),
 *    and one on what a plan is read from — the feature folders, the test files, `src/`, and git's log of
 *    `HEAD` — so an edit of `plan.md`, of a unit title or of a `@planned` comment shows without a test run,
 *    and a commit that delivers a piece shows under it;
 *  - a static server over `specs/` on a free port, whose own address lists every generated page and is said
 *    again at each render, and which injects a one-line live-reload
 *    into every HTML page it serves and pushes a reload when the page was re-rendered. It
 *    also takes the reviewer's answers from a plan's pages: `POST /__feedback` writes one to
 *    `specs/features/<feature>/plan-feedback.json`, `POST /__approve` approves the plan once
 *    every item is approved. Both re-render.
 *
 * The process holds the renderer as it was when it started: once one of the renderer's own
 * sources is saved, it stops rendering and says so on every page, until it is started again.
 *
 * Ctrl-C stops all three.
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, watch } from 'node:fs';
import { createServer, type ServerResponse } from 'node:http';
import { extname, join, normalize, relative } from 'node:path';
import { FEATURES, PAGES, ROOT, STORIES_DIR, config } from './config';
import { openSource, toolSources } from './project-stack';
import type { SourceReader } from './stack';
import { approveFromPage, generatedPages, planDbDiffs, readPlanSources, render, renderIndexPage, reproductionFiles, saveFeedback, SCANNED } from './render';

// The test files to keep running: every one that declares a narrative, found in the source, and every one that
// holds a reproduction of a plan and that `commands.tests` runs, whose page shows what it sees now. A reproduction
// another command runs (`commands.testsUnder`) is not run at each save: its page shows what the last render's run
// of it saw.
// The source reader is kept between renders: `fresh()` re-reads only what changed, so a
// re-render after one save pays for one file, not for the whole source.
let source: SourceReader = openSource();
const NARRATIVE_TESTS = [...new Set([...source.narrativeTestFiles(), ...reproductionFiles(readPlanSources()).filter((r) => r.command === config.commands.tests).map((r) => r.file)])];
const SERVE_ROOT = join(ROOT, config.docs);

const TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
};

const RELOAD_SNIPPET = `<script>new EventSource('/__reload').onmessage = () => location.reload();</script>`;

const clients = new Set<ServerResponse>();

// This process holds the renderer as it was when it started. Once one of its sources is edited, a render from
// here would overwrite the pages with what the old code draws: it stops rendering and says so, on the terminal
// and on every page it serves, until it is started again.
const STARTED = Date.now();
const RENDERER = toolSources().map((f) => join(ROOT, f));
const outdated = () => RENDERER.some((f) => existsSync(f) && statSync(f).mtimeMs > STARTED);
const OUTDATED_NOTE = 'This app is older than its renderer: the pages it serves may be out of date. Stop it (Ctrl-C) and run `npm run comprehension` again.';
const OUTDATED_BANNER = `<div style="position:sticky;top:0;z-index:9;background:#b91c1c;color:#fff;font:600 14px/1.5 system-ui,sans-serif;padding:.4rem .8rem">${OUTDATED_NOTE.replace(/`([^`]+)`/g, '<code>$1</code>')}</div>`;
let warned = false;



/** The address of the pages' list, once the server listens. */
let base = '';

/** The page at the server's own address: the index the render writes, its paths from the served folder. */
function pagesIndex(): string {
  return renderIndexPage(generatedPages(SERVE_ROOT), '/');
}

async function rerender(reason: string): Promise<void> {
  if (outdated()) {
    if (!warned) console.error(`[comprehension] ${OUTDATED_NOTE}`);
    warned = true;
    for (const c of clients) c.write('data: reload\n\n');
    return;
  }
  try {
    source = source.fresh();
    // The database diff of a plan's proposed migration is drawn once per SQL text, so a re-render pays nothing for it.
    const sources = readPlanSources();
    const { stories, pages } = render(source, await planDbDiffs(sources), sources);
    // The address is said again at each render: the tests' watcher redraws the terminal under its own lines,
    // and what this process printed while it ran can be erased with them.
    console.log(`[comprehension] rendered ${stories} stories → ${pages.length} pages (${reason})${base ? ` · ${base}` : ''}`);
    for (const c of clients) c.write('data: reload\n\n');
  } catch (err) {
    // A source file saved a moment ago: its tests are re-running, and their stories bring the next render.
    if (err instanceof Error && err.message.includes('older than the source')) console.log(`[comprehension] not rendered yet (${reason}): the narrative tests are re-running`);
    else console.error('[comprehension] render failed:', err);
  }
}

mkdirSync(STORIES_DIR, { recursive: true });
void rerender('start');

let pending: NodeJS.Timeout | null = null;
const soon = (reason: string) => {
  if (pending) clearTimeout(pending);
  pending = setTimeout(() => void rerender(reason), 400);
};
watch(STORIES_DIR, { recursive: true }, () => soon('stories changed'));
// What a plan is read from beside the stories: its markdown, its approval and its proposed migration; the test
// files, for a title to write and a comment on a test; the source, for a `@planned` comment. The reviewer's
// answers are not watched: the request that saves one renders.
const PLAN_INPUTS: Array<[folder: string, reads: RegExp]> = [
  [FEATURES, /(?:^|\/)(?:plan\.md|spec\.md|plan\.approved\.json|[^/]+\.sql)$/],
  ...[...config.tests.roots, ...config.source.app].map((folder): [string, RegExp] => [folder.replace(/\/$/, ''), SCANNED]),
];
for (const [folder, reads] of PLAN_INPUTS) {
  watch(join(ROOT, folder), { recursive: true }, (_event, file) => {
    if (file && reads.test(file.toString())) soon(`${folder}/${file.toString()} changed`);
  });
}

// A commit moves no file the watchers above see, and a piece lists its commits: git's own log of `HEAD` says one
// was made. A checkout with no such file (a linked worktree keeps it elsewhere) renders at the next save.
const HEAD_LOG = join(ROOT, '.git/logs/HEAD');
if (existsSync(HEAD_LOG)) watch(HEAD_LOG, () => soon('a commit'));

const server = createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost');
  if (url.pathname === '/__reload') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    res.write('\n');
    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }
  if (req.method === 'POST' && (url.pathname === '/__feedback' || url.pathname === '/__approve')) {
    // Only a page this server served may answer: the browser names the page's origin.
    if (req.headers.origin !== `http://${req.headers.host}`) {
      res.writeHead(403).end('answers come from a page of this server');
      return;
    }
    let body = '';
    req.on('data', (chunk: Buffer) => { body += chunk.toString('utf8'); });
    req.on('end', () => {
      try {
        if (outdated()) throw new Error(OUTDATED_NOTE);
        const sent = JSON.parse(body) as { feature: string; key: string; unit: string; what: string; verdict: string; note: string };
        let said = 'saved';
        if (url.pathname === '/__feedback') saveFeedback(sent.feature, sent);
        else {
          const done = approveFromPage(sent.feature, source);
          said = `${done.file} written`;
        }
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' }).end(said);
        void rerender(url.pathname === '/__approve' ? 'plan approved' : 'feedback');
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' }).end(err instanceof Error ? err.message : String(err));
      }
    });
    return;
  }
  if (url.pathname === '/') {
    const html = pagesIndex().replace('</body>', `${RELOAD_SNIPPET}</body>`);
    res.writeHead(200, { 'Content-Type': TYPES['.html'], 'Cache-Control': 'no-store' }).end(outdated() ? html.replace(/<body[^>]*>/, (tag) => `${tag}${OUTDATED_BANNER}`) : html);
    return;
  }
  const file = normalize(join(SERVE_ROOT, decodeURIComponent(url.pathname)));
  if (!file.startsWith(SERVE_ROOT) || !existsSync(file) || statSync(file).isDirectory()) {
    res.writeHead(404).end('not found');
    return;
  }
  const type = TYPES[extname(file)] ?? 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  if (type.startsWith('text/html')) {
    const html = readFileSync(file, 'utf8').replace('</body>', `${RELOAD_SNIPPET}</body>`);
    res.end(outdated() ? html.replace(/<body[^>]*>/, (tag) => `${tag}${OUTDATED_BANNER}`) : html);
  } else {
    res.end(readFileSync(file));
  }
});

server.listen(0, '127.0.0.1', () => {
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : 0;
  base = `http://127.0.0.1:${port}/`;
  console.log(`[comprehension] every page: ${base}`);
  // A plan's two pages, where the reviewer answers: the design, then the delivery and what moved since the approval.
  const plans = join(ROOT, PAGES, 'plans');
  for (const f of existsSync(plans) ? readdirSync(plans).filter((x) => x.endsWith('.html')).sort() : []) {
    console.log(`[comprehension] ${f.endsWith('-delivery.html') ? 'delivery' : 'plan'}: http://127.0.0.1:${port}/${relative(SERVE_ROOT, join(plans, f))}`);
  }
});

// The watch command of the configuration: one that keeps running with no TTY, or the app would stop at once.
const [watcher, ...watcherArgs] = config.commands.watch;
const tests = spawn(watcher, [...watcherArgs, ...NARRATIVE_TESTS], { cwd: ROOT, stdio: 'inherit' });
tests.on('exit', (code) => {
  console.log(`[comprehension] the tests' watcher exited (${code ?? 'signal'}); stopping`);
  server.close();
  process.exit(code ?? 0);
});
process.on('SIGINT', () => {
  tests.kill('SIGINT');
});
