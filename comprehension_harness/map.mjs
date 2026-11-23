#!/usr/bin/env node
/**
 * map — the narratives and the specs, asked one question at a time, answered as text. For agents.
 *
 *   npm run map                                  the narratives, one line each
 *   npm run map -- narrative <slug>              a narrative: its steps under their causes, branches, mechanisms ridden
 *   npm run map -- step <slug>#<n>               one step: its function's source, who refers to it, its tests, the debts naming it
 *   npm run map -- where <file | function>       the steps a file or a function carries, or "unmapped"
 *   npm run map -- around <slug>                 the functions next to a narrative that hold no `narrate`
 *   npm run map -- spec <feature>                a feature's spec: intent, changed screens, cases to add, what it rides on
 *   npm run map -- plan <feature>                a feature's plan: plan.md, its pieces in run order with their sites and planned tests, the rules' owners
 *   npm run map -- brief <feature>#<piece>         one piece of a plan, with the code at each of its sites
 *   npm run map -- brief <feature>/<lot>           a lot of the plan's delivery: its pieces with their code, the decisions that bind them, its journey cases
 *   npm run map -- check <feature>                 a plan's check in a screen: what fails, what is not as approved, what each lot owes (exit 1 on a failure)
 *   npm run map -- feedback <feature>              the reviewer's answers from the pages: what is not approved and why, each question's answer, what is not read
 *   npm run map -- reach <feature>#<piece>         the tests that reach its sites today, by file (or <feature>/<lot>): read before a unit test is planned, kept or deleted
 *
 * A slug may be shortened to any part that names one narrative (`settings`, `checkout`).
 *
 * This file is plain JavaScript and imports nothing of the repo: it reads the snapshots
 * `comprehension_harness/map-build.ts` (the narratives) and `comprehension_harness/journey-render.ts` (the specs) write under
 * `map/` of the project's cache, so an answer costs a process start. Each snapshot lists the
 * files it was read from with their modification times; when one moved, the snapshot is rebuilt
 * first (a few seconds), and when source moved under the stories, the narrative tests are run again
 * before that. What cannot be refreshed from here (a journey test newer than its captures needs a
 * browser run) fails with the command to run. `--stale-ok` answers from what is there.
 */
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { logMapEvent } from './map-log.mjs';
import { readProject } from './project.mjs';

const { root: ROOT, config, tools: TOOLS, mapDir: MAP_DIR, stories: STORIES_FOLDER, features: FEATURES } = readProject();
const SNAPSHOT = join(MAP_DIR, 'narratives.json');
const STORIES = join(ROOT, STORIES_FOLDER);
/** The commands of the configuration: a tool of this folder, the narrative tests, the journeys. */
const tool = (name) => [...config.commands.tool, `${TOOLS}/${name}`];
const typed = (command, ...rest) => [...command, ...rest].join(' ');
const TESTS = config.commands.tests;
const JOURNEYS = typed(config.commands.journeys);

const args = process.argv.slice(2);
const staleOk = args.includes('--stale-ok');
const [verb = 'narratives', ...rest] = args.filter((a) => !a.startsWith('--'));
const arg = rest.join(' ');

// What a call cost and gave, logged when the process ends (`comprehension_harness/map-log.mjs`).
const started = Date.now();
const usage = { chars: 0, refreshed: [] };
process.on('exit', (code) => logMapEvent({ kind: 'verb', verb, arg, stale_ok: staleOk, refreshed: usage.refreshed, ms: Date.now() - started, chars: usage.chars, exit: code }));

const say = (...lines) => { const text = lines.join('\n'); usage.chars += text.length + 1; console.log(text); };
const note = (line) => console.error(`map: ${line}`);
const fail = (line) => { console.error(`map: ${line}`); process.exit(1); };
const run = ([cmd, ...argv], ...rest) => spawnSync(cmd, [...argv, ...rest], { cwd: ROOT, stdio: ['ignore', 'ignore', 'inherit'] }).status === 0;
const mtime = (file) => { try { return statSync(join(ROOT, file)).mtimeMs; } catch { return null; } };
const read = (file) => (existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null);

/** The inputs of a snapshot that moved since it was written (changed, or gone). */
const moved = (snapshot) => Object.entries(snapshot.inputs).filter(([file, at]) => mtime(file) !== at).map(([file]) => file);

// ── the snapshots, fresh ─────────────────────────────────────────────────────────────────────────────────

function snapshot() {
  let map = read(SNAPSHOT);
  const changed = map ? moved(map) : ['(no snapshot yet)'];
  const stories = existsSync(STORIES) ? readdirSync(STORIES).length : 0;
  const known = map ? Object.keys(map.inputs).filter((f) => f.startsWith(`${STORIES_FOLDER}/`)).length : -1;
  if (changed.length === 0 && stories === known) return map;
  if (staleOk && map) { note(`answering from a snapshot older than ${changed.slice(0, 3).join(', ')}`); return map; }
  // A moved file only needs the rebuild: a step whose line shifted is found again by its sentence. The rebuild
  // fails when a narrative's story names a call that is gone or reworded; then that narrative's tests run again.
  usage.refreshed.push('narratives-snapshot');
  if (stories > 0 && run(tool('map-build.ts'))) return read(SNAPSHOT);
  const tests = new Set();
  for (const n of map?.narratives ?? []) {
    const files = new Set([n.file, ...n.steps.map((s) => s.file), ...n.branches.map((b) => b.file)]);
    if (changed.some((f) => files.has(f))) tests.add(n.file);
  }
  if (tests.size === 0) for (const folder of config.tests.narrative) tests.add(folder.replace(/\/$/, ''));
  note(`the stories no longer match the source — running ${[...tests].join(', ')}`);
  usage.refreshed.push('narrative-tests');
  if (!run(TESTS, ...tests)) fail(`the narrative tests fail: the map cannot be rebuilt until they pass (${typed(TESTS, ...tests)})`);
  if (!run(tool('map-build.ts'))) fail(`${TOOLS}/map-build.ts failed (above). If it names a story older than its source, run that test file: ${typed(TESTS, '<file>')}`);
  map = read(SNAPSHOT);
  return map;
}

function spec(feature) {
  const file = join(MAP_DIR, `spec-${feature}.json`);
  const t = snapshot();
  let map = read(file);
  if (!existsSync(join(ROOT, FEATURES, feature))) fail(`no feature folder ${FEATURES}/${feature}`);
  const changed = map ? moved(map) : ['(no snapshot yet)'];
  const behindNarratives = map ? map.builtAt < t.builtAt : true;
  if (changed.length === 0 && !behindNarratives) return map;
  if (staleOk && map) { note(`answering from a snapshot older than ${changed.slice(0, 3).join(', ') || 'the narratives'}`); return map; }
  // A journey test newer than its captures needs a browser run, which this script does not start.
  const isJourneyTest = new RegExp(config.tests.journeys);
  const journeys = changed.filter((f) => isJourneyTest.test(f));
  if (journeys.length) fail(`${journeys.join(', ')} changed since its captures were taken — ${JOURNEYS}, then ask again (or --stale-ok)`);
  usage.refreshed.push('spec-snapshot');
  if (!run(tool('journey-render.ts'))) fail(`${TOOLS}/journey-render.ts failed (above)`);
  map = read(file);
  if (!map) fail(`no journey plans a screen or a case for ${feature}, or the journeys have not run on this checkout — ${JOURNEYS}`);
  return map;
}

// ── the answers ──────────────────────────────────────────────────────────────────────────────────────────

const at = (x) => `${x.file}:${x.line}`;
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

function pick(map, name) {
  const [slug] = name.split('#');
  const hits = map.narratives.filter((n) => n.slug === slug);
  const loose = hits.length ? hits : map.narratives.filter((n) => n.slug.includes(slug));
  if (loose.length !== 1) fail(`"${slug}" names ${loose.length === 0 ? 'no narrative' : loose.map((n) => n.slug).join(' and ')}. The narratives:\n${map.narratives.map((n) => `  ${n.slug}`).join('\n')}`);
  return loose[0];
}

/** A list of neighbours on one line each; a long one is counted, its narrated members named. */
function neighbours(list, indent = '    ') {
  if (list.length === 0) return [`${indent}none`];
  const line = (x) => `${indent}${x.fn}  ${at(x)}${x.narrated ? '  · narrated' : ''}${x.how ? `  · ${x.how}` : ''}`;
  if (list.length <= 14) return list.map(line);
  const narrated = list.filter((x) => x.narrated);
  return [`${indent}${list.length} functions, ${narrated.length} of them narrated${narrated.length ? ':' : ''}`, ...narrated.map(line), `${indent}the others: ${list.filter((x) => !x.narrated).slice(0, 8).map((x) => x.fn).join(', ')}, …`];
}

function narratives(map) {
  say('Narratives — a flow told by its own code, step by step, in the order one test crosses it.', '');
  for (const n of map.narratives) say(`${n.kind === 'mechanism' ? 'mechanism' : 'product  '}  ${n.slug}`, `           ${n.title} — ${plural(n.steps.length, 'step')}, ${plural(n.branches.length, 'branch').replace('branchs', 'branches')}, ${n.file}`);
  say('', `next: npm run map -- narrative <slug>   (any part of a slug that names one)`);
}

/** Says when a narrative's files were edited after the run its steps were read from. */
const edited = (n) => (n.editedSince.length
  ? ['', `note: ${n.editedSince.join(', ')} changed after the run these steps were read from. They were found again by their sentences; to observe the flow again: ${typed(TESTS, n.file)}`]
  : []);

function narrative(map, name) {
  const n = pick(map, name);
  say(`# ${n.title}  [${n.kind}]`, `${n.file}:${n.line} — reference case "${n.canonical}"`, '', n.summary, '');
  let cause;
  for (const s of n.steps) {
    if (s.cause !== cause) { cause = s.cause; say(cause ? `▸ ${cause}` : '▸ (before any cause)'); }
    say(`  ${s.n}. ${s.sentence}`, `     ${at(s)}  in ${s.fn}${s.stops > 1 ? `  · ${s.stops} stops` : ''}${s.named.length ? `  · named by ${plural(s.named.length, 'debt/rule')}` : ''}`);
  }
  if (n.branches.length) {
    say('', 'Branches — a `narrate` the reference case does not reach, told by another case:');
    for (const b of n.branches) say(`  ${at(b)}  in ${b.fn} — ${b.sentence}`, `     told by "${b.toldBy}"`);
  }
  if (n.ridesOn.length) say('', `Rides on: ${n.ridesOn.map((r) => `${r.slug} (${plural(r.hits, 'hit')})`).join(', ')}`);
  if (n.exercisedBy.length) say('', `Exercised by: ${n.exercisedBy.join(', ')}`);
  if (n.variants.length) say('', 'Other cases:', ...n.variants.map((v) => `  "${v}"`));
  say(...edited(n), '', `next: npm run map -- step ${n.slug}#<n>   ·   npm run map -- around ${n.slug}`);
}

function step(map, name) {
  const n = pick(map, name);
  const k = Number(name.split('#')[1]);
  const s = n.steps.find((x) => x.n === k);
  if (!s) fail(`${n.slug} has steps 1 to ${n.steps.length}; ask for ${n.slug}#<n>`);
  say(`# ${n.title} — step ${s.n} of ${n.steps.length}`, s.sentence, '', `${at(s)}  in ${s.fn}${s.cause ? `\ncause: ${s.cause}` : ''}`, '');
  if (s.range) {
    const lines = readFileSync(join(ROOT, s.file), 'utf8').split('\n');
    const [from, to] = s.range;
    const MAX = 70;
    const numbered = (a, b) => lines.slice(a - 1, b).map((l, i) => `${String(a + i).padStart(5)}${a + i === s.line ? ' ▸' : '  '}${l}`);
    say(`${s.file}:${from}-${to}`);
    if (to - from < MAX) say(...numbered(from, to));
    else say(...numbered(Math.max(from, s.line - 25), Math.min(to, s.line + 25)), `      … the function runs from line ${from} to ${to}; read the rest there`);
    say('');
  }
  say('Referred to by:', ...neighbours(s.callers), '', 'Calls or hands on:', ...neighbours(s.callees), '');
  say(`Reached by ${plural(s.reachedBy.tests, 'test')} in ${plural(s.reachedBy.files.length, 'file')}${s.reachedBy.files.length ? ':' : ''}`, ...s.reachedBy.files.slice(0, 12).map((f) => `    ${f}`), ...(s.reachedBy.files.length > 12 ? [`    … and ${s.reachedBy.files.length - 12} more`] : []));
  if (s.named.length) say('', 'Named by:', ...s.named.map((m) => `    ${m.kind} · ${m.title}  ${m.page}:${m.line}`));
  say(...edited(n));
}

function around(map, name) {
  const n = pick(map, name);
  // One entry per function; its relations grouped, so three steps of one function read "steps 5, 7, 8".
  const seen = new Map();
  for (const s of n.steps) for (const [side, list] of [['refers to', s.callers], ['is called by', s.callees]]) {
    for (const x of list) {
      if (x.narrated) continue;
      const key = `${x.file}#${x.fn}`;
      const entry = seen.get(key) ?? { ...x, relations: new Map() };
      seen.set(key, entry);
      const relation = `${side}|${s.fn}|${x.how ?? ''}`;
      entry.relations.set(relation, [...(entry.relations.get(relation) ?? []), s.n]);
    }
  }
  const list = [...seen.values()].sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
  say(`# Around "${n.title}" — ${plural(list.length, 'function')} next to its steps that hold no \`narrate\``,
    'Found in the source index, not by a run: a function that refers to a step\'s function (one level further through un-narrated code), or that a step\'s function calls. A candidate list: a handler reached only through a context value is missed.', '');
  let file;
  for (const x of list) {
    if (x.file !== file) { file = x.file; say(file); }
    const rel = [...x.relations].map(([relation, steps]) => {
      const [side, fn, how] = relation.split('|');
      return `${side} step${steps.length > 1 ? 's' : ''} ${steps.join(', ')} (${fn})${how ? `, ${how}` : ''}`;
    });
    say(`  ${x.fn}:${x.line} — ${rel.length > 3 ? `${rel.slice(0, 3).join('; ')}; and ${rel.length - 3} more` : rel.join('; ')}`);
  }
  if (n.ridesOn.length) say('', `It rides on ${n.ridesOn.map((r) => r.slug).join(', ')}: their surroundings are under  npm run map -- around <mechanism>`);
}

function where(map, what) {
  if (!what) fail('where <file | function>');
  const isFile = what.includes('/') || /\.[a-z]+$/.test(what);
  const match = (x) => (isFile ? x.file === what || x.file.endsWith(`/${what}`) : x.fn === what);
  const out = [];
  for (const n of map.narratives) {
    for (const s of n.steps) if (match(s)) out.push(`  step ${s.n} of ${n.slug}  ${at(s)}  in ${s.fn}\n     ${s.sentence}`);
    for (const b of n.branches) if (match(b)) out.push(`  a branch of ${n.slug}  ${at(b)}  in ${b.fn}, told by "${b.toldBy}"\n     ${b.sentence}`);
  }
  const near = new Map();
  for (const n of map.narratives) for (const s of n.steps) for (const [side, list] of [['refers to', s.callers], ['is called by', s.callees]]) {
    for (const x of list) if (!x.narrated && match(x)) near.set(`${x.fn}|${n.slug}|${s.n}`, `  ${x.fn}  ${at(x)} — ${side} step ${s.n} of ${n.slug} (${s.fn})${x.how ? `, ${x.how}` : ''}`);
  }
  if (out.length === 0 && near.size === 0) {
    say(`unmapped: no narrative step is in ${what}, and nothing in it refers to or is called by a step's function.`, 'Read the code directly. If the change makes this a flow worth telling, that is a narrative to write.');
    return;
  }
  if (out.length) say(`${what} carries ${plural(out.length, 'narrated site')}:`, ...out);
  if (near.size) say(out.length ? '' : `${what} holds no \`narrate\`, and is next to narrated code:`, ...(out.length ? ['Also next to narrated code, holding no `narrate` itself:'] : []), ...[...near.values()].slice(0, 20), ...(near.size > 20 ? [`  … and ${near.size - 20} more`] : []));
  const tests = new Set();
  for (const n of map.narratives) if (n.steps.some(match) || n.branches.some(match)) tests.add(`${n.file} (the narrative's test)`);
  if (tests.size) say('', 'Before editing, the tests that tell it:', ...[...tests].map((t) => `  ${t}`));
  say('', 'next: npm run map -- step <slug>#<n>');
}

function specText(feature) {
  if (!feature) fail('spec <feature>');
  const m = spec(feature);
  const t = snapshot();
  say(m.intent.trim(), '', '─'.repeat(60), `What changes on screen — declared in the journey tests`, '');
  for (const j of m.journeys) {
    say(`Journey "${j.name}"  ${j.file}`, `  who: ${j.who}`, `  wants: ${j.wants}`, `  now: ${j.now}`, `  screens: ${j.path.map((id) => (j.changed.some((c) => c.id === id) ? `[${id}]` : id)).join(' → ')}`);
    for (const c of j.changed) {
      say(`  ${j.slug}#${c.id} — today: ${c.why}`);
      if (c.planned) say(`    planned: ${c.planned.what}`, `    mockup:  ${c.planned.mockup}`);
      if (c.todos.length) say(`    cases to add (${j.file}):`, ...c.todos.map((x) => `      :${x.line}  ${x.title}`));
    }
    for (const u of j.unreached) say(`  at a screen this journey does not reach yet (${u.screen}): ${u.title}  :${u.line}`);
    say('');
  }
  say('─'.repeat(60), 'What the change rides on — read from the journey run. Candidates: a step crossed is not a step the feature changes, and a change with no screen (a migration, a type) is on no list.', '');
  for (const r of [...m.rides.narratives].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'product' ? -1 : 1))) {
    const n = t.narratives.find((x) => x.slug === r.slug);
    say(`${r.kind === 'mechanism' ? 'mechanism' : 'narrative'} ${r.slug} — ${r.title}`);
    for (const a of r.at) {
      say(`  ${a.screen}: ${[a.to.length ? `to reach it, steps ${a.to.join(' ')}` : '', a.from.length ? `from it, steps ${a.from.join(' ')}` : ''].filter(Boolean).join('; ')}`);
    }
    if (r.kind === 'product' && n) {
      const crossed = new Set(r.at.flatMap((a) => [...a.to, ...a.from]));
      for (const s of n.steps) if (crossed.has(s.n)) say(`    ${s.n}. ${at(s)}  ${s.fn}`);
    }
    for (const b of r.branches) say(`  branch ${at(b)} in ${b.fn ?? '?'}, told by "${b.toldBy}" — at ${b.at.join(', ')}`);
  }
  if (m.rides.orphans.length || m.rides.silent.length) {
    say('', 'Crossed and told by no narrative:');
    for (const o of m.rides.orphans) say(`  ${at(o)} in ${o.fn ?? '?'} — a narrate no narrative case reaches (at ${o.at.join(', ')})`);
    for (const s of m.rides.silent) say(`  ${s.what} — crosses no step of a product narrative (${s.at.join(', ')})`);
  }
  say('', 'Answered by a stub — the journey did not see the server; the test named pins what the real one does:');
  if (m.rides.server.length === 0) say('  no server step on these paths');
  // A family of steps (the sync pull's thirteen tables) is one line: what a plan needs of it is that it is there.
  const family = (s) => s.name.split('-')[0];
  const sizes = new Map();
  for (const s of m.rides.server) sizes.set(family(s), (sizes.get(family(s)) ?? 0) + 1);
  for (const s of m.rides.server) if (sizes.get(family(s)) < 6) say(`  ${s.name} [${s.method}] — ${s.does}`, `    pinned by ${s.truth}`);
  for (const [name, size] of sizes) if (size >= 6) say(`  ${name}-* — ${size} steps of one family, each pinned by its own test: ${m.rides.server.filter((s) => family(s) === name).map((s) => s.name.slice(name.length + 1)).join(', ')}`);
  const product = m.rides.narratives.filter((r) => r.kind === 'product').map((r) => r.slug);
  say('', `next: ${product.map((p) => `npm run map -- narrative ${p}`).join('   ·   ') || 'npm run map'}`, ...product.map((p) => `      npm run map -- around ${p}`));
}

function pickPlan(map, feature) {
  const plan = map.plans.find((p) => p.feature === feature);
  if (!plan) fail(`no plan for "${feature}": no planned(…) call, @planned comment or tagged test to write names it${map.plans.length ? `. Features with one: ${map.plans.map((p) => p.feature).join(', ')}` : ''}`);
  return plan;
}

const TIERS = ['narrative', 'server', 'unit'];

/** `plan.md` blocks as lines: a paragraph one line, a list one line an item. */
function blockLines(blocks, first) {
  const pad = ' '.repeat(first.length);
  return blocks.flatMap((b) => (b.kind === 'p' ? [b.text] : b.items.map((i) => `- ${i.text}`))).map((t, i) => `${i === 0 ? first : pad}${t}`);
}

/** A piece of a plan as text. `code` adds the lines around each of its sites: what an implementer starts from.
 *  What is left to do is told in full; what is done is one line, unless `whole` asks for each place that became
 *  code and each test written (one piece asked for by name). A piece with nothing left is its statement and
 *  that line. */
function pieceText(plan, piece, code, whole = false, printed = new Map()) {
  const out = [`#${piece.slug}${piece.doc ? ` — ${piece.doc.what}` : ''}`];
  // A comment standing on a test this piece writes is a note on that test: it is told under the test's title,
  // once, and is no place of its own.
  const fullTitle = (t) => `${t.feature}#${t.slug}: ${t.title}${t.rule ? ` [${t.rule}]` : ''}`;
  const notes = new Map();
  const statics = piece.statics.filter((x) => {
    const on = /^(?:it|test) "(.*)"$/.exec(x.on ?? '')?.[1];
    const t = on === undefined || x.removes ? undefined : piece.todos.find((o) => fullTitle(o) === on);
    if (!t) return true;
    notes.set(t, [...(notes.get(t) ?? []), x]);
    return false;
  });
  const builtLines = [...piece.built.sites, ...piece.built.comments];
  const toWrite = piece.todos.filter((t) => !t.written).length;
  const done = piece.sites.length + piece.statics.length + toWrite === 0 && builtLines.length + piece.todos.length > 0;
  const commits = piece.commits.map((c) => c.sha.slice(0, 8)).join(', ');
  const builtLine = builtLines.length || piece.commits.length
    ? [`  built: ${plural(builtLines.length, 'place')}${piece.todos.length > toWrite ? `, ${plural(piece.todos.length - toWrite, 'test')} written` : ''} — ${commits ? `git show ${commits}` : 'no commit names the piece'}`]
    : [];
  // What it was built with that no line of the plan says: whoever builds on the piece reads it.
  const pieceNotes = (piece.doc?.notes ?? []).map((n) => `  note: ${n.text}`);
  if (done && !whole) return [...out, ...builtLine, ...pieceNotes];
  if (piece.doc) {
    out.push(...blockLines(piece.doc.why, '  why: '));
    if (piece.doc.ask) out.push(`  TO CONFIRM: ${piece.doc.ask.question}${piece.doc.ask.detail ? ` ${piece.doc.ask.detail}` : ''}`);
    out.push(...pieceNotes);
  } else if (plan.doc) out.push(`  (no section "## #${piece.slug}" in ${plan.doc.file}: the piece has no statement)`);
  if (piece.bug && code) out.push(`  fixes the bug: ${piece.bug.title}  (${plan.doc.file}:${piece.bug.line})`);
  if (piece.decidedIn.length) out.push(`  also decided in: ${piece.decidedIn.map((d) => `"${d.title}"`).join(', ')}`);
  // What a place says it should see: values, and the keys each crossing should see its own of.
  const should = (x) => `${x.expect ? `  · should see ${x.expect}` : ''}${x.distinct?.length ? `  · each crossing its own ${x.distinct.join(', ')}` : ''}`;
  const siteHead = (x) => {
    const inside = x.crossedBy.map((c) => `${c.narrative}${c.step ? ` step ${c.step.n} (${c.step.how === 'in' ? 'in' : c.step.how === 'via' ? 'through' : 'right after'} ${c.step.label})` : ', in no step'}`).join('; ');
    const tests = x.reachedBy.reduce((a, r) => a + r.tests, 0);
    // Evidence marks no change: it says what a reproduction saw at the place, and goes with the fix.
    if (x.change === 'evidence') {
      // A crossing whose watch is not what it should have seen is said first, with what it should: that is the bug.
      const differs = (c) => Object.entries(c.expect ?? {}).some(([key, value]) => JSON.stringify(c.watch?.[key]) !== JSON.stringify(value));
      const said = (c) => `${JSON.stringify(c.watch)}${differs(c) ? ` (should be ${JSON.stringify(c.expect)})` : ''}`;
      const crossings = (x.seenBy ?? []).flatMap((s) => s.crossings).filter((c) => c.watch !== null).sort((a, b) => Number(differs(b)) - Number(differs(a)));
      const seen = [...new Set(crossings.map(said))];
      return [`  evidence ${at(x)}  in ${x.fn} — ${x.sentence}`,
        `    goes with the fix${should(x)}${seen.length ? `  · a reproduction saw ${seen.slice(0, 3).join(' | ')}${seen.length > 3 ? ` … (${seen.length} values)` : ''}` : '  · crossed by no reproduction yet'}`];
    }
    return [`  ${x.change}  ${at(x)}  in ${x.fn} — ${x.sentence}${should(x)}`,
      ...(x.change === 'added' ? [`    called from: ${(plan.calledFrom?.[x.id] ?? []).map((c) => `${at(c)} (#${c.slug})`).join(', ') || 'NOWHERE — no site names it'}`] : []),
      `    ${x.change === 'added' ? `new seam: ${x.signature ?? x.fn}` : inside ? `lands in ${inside}` : 'crossed by no narrative'}${tests ? `  · reached by ${plural(tests, 'test')} in ${plural(x.reachedBy.length, 'file')}` : x.change === 'added' ? '' : '  · seen by no run yet: run the narrative tests it should sit in, then ask again'}`];
  };
  // A comment on a test names the test on its own line, then says what becomes of it: the two together run long.
  const staticHead = (x) => (/^(?:it|test)\b/.test(x.on ?? '')
    ? [`  ${x.removes ? 'removed ' : 'static  '} ${at(x)}  ${x.on}`, `    ${x.text}`]
    : [`  ${x.removes ? 'removed ' : 'static  '} ${at(x)}${x.on ? `  on ${x.on}` : ''} — ${x.text}`]);
  if (!code) {
    for (const x of piece.sites) out.push(...siteHead(x));
    for (const x of statics) out.push(...staticHead(x));
  } else {
    // With the code: the places in file order, each file's lines printed once — places whose surroundings
    // overlap share one excerpt, a mark on each, and lines an earlier piece of the same brief printed are not
    // printed again. A test that goes is named and not printed. A place in a page of prose is its own line and
    // one each side: the lines around it are paragraphs.
    const places = [...piece.sites.map((x) => ({ x, site: true })), ...statics.map((x) => ({ x, site: false }))]
      .sort((a, b) => a.x.file.localeCompare(b.x.file) || a.x.line - b.x.line);
    let open = null;
    const flush = () => {
      if (!open) return;
      const lines = readFileSync(join(ROOT, open.file), 'utf8').split('\n');
      const to = Math.min(lines.length, open.to);
      const seen = printed.get(open.file) ?? new Set();
      printed.set(open.file, seen);
      let skipped = 0;
      const shown = () => {
        if (skipped) out.push(`             … ${plural(skipped, 'line')} shown above`);
        skipped = 0;
      };
      for (let n = open.from; n <= to; n += 1) {
        if (seen.has(n) && !open.marks.has(n)) { skipped += 1; continue; }
        shown();
        seen.add(n);
        const l = lines[n - 1];
        // A line of a page can run to a thousand characters: its start is enough to place it.
        out.push(`      ${String(n).padStart(5)}${open.marks.has(n) ? ' ▸' : '  '}${l.length > 200 ? `${l.slice(0, 200)} …` : l}`);
      }
      shown();
      open = null;
    };
    for (const { x, site } of places) {
      const removal = !site && x.removes;
      const [before, after] = site ? [12, 8] : /\.(?:md|html?)$/.test(x.file) ? [1, 1] : [4, 6];
      if (open && (removal || open.file !== x.file || x.line - before > open.to + 1)) flush();
      out.push(...(site ? siteHead(x) : staticHead(x)));
      if (removal) continue;
      if (!open) open = { file: x.file, from: Math.max(1, x.line - before), to: x.line + after, marks: new Set() };
      open.to = Math.max(open.to, x.line + after);
      open.marks.add(x.line);
    }
    flush();
  }
  out.push(...builtLine);
  if (whole) out.push(...builtLines.map((line) => `    ${line}`));
  for (const f of piece.sql) out.push(`  migration proposed in ${f}`);
  for (const tier of TIERS) {
    const todos = piece.todos.filter((t) => t.tier === tier);
    const toWrite = todos.filter((t) => !t.written).length;
    const failing = todos.filter((t) => t.reproduction).length;
    // A reproduction is written and fails today: it is owed until the piece is built and it is declared a test like another.
    const said = (t) => (t.reproduction ? `FAILS TODAY, a reproduction${t.run?.failure ? ` (${t.run.failure.message.split('\n')[0].slice(0, 120)})` : ''} — ` : t.written ? 'written — ' : '');
    if (todos.length) out.push(`  ${tier} tests (${toWrite} to write${failing ? `, ${failing} failing today` : ''}${todos.length > toWrite + failing ? `, ${todos.length - toWrite - failing} written` : ''}):`, ...todos.filter((t) => whole || !t.written || t.reproduction).flatMap((t) => [`    ${at(t)}  ${said(t)}${t.title}${t.rule ? `  [owns ${t.rule}]` : ''}`, ...(notes.get(t) ?? []).map((x) => `      how: ${x.text}  (the comment at :${x.line}, which goes)`)]));
  }
  if (piece.todos.length === 0) out.push('  no test to write');
  const moved = code ? (plan.delta ?? []).find((d) => d.kind === 'piece' && d.name === `#${piece.slug}`) : undefined;
  if (moved) out.push(`  not as approved (${moved.state}):`, ...unitLines(plan, moved).map((l) => `  ${l}`));
  return out;
}

function plan(map, feature) {
  if (!feature) fail('plan <feature>');
  const p = pickPlan(map, feature);
  if (p.doc) say(`# ${p.doc.title}   (${p.doc.file}: each piece's statement and reason)`, ...blockLines(p.doc.lead, ''), '', '─'.repeat(60));
  else say(`(no ${FEATURES}/${feature}/plan.md: the pieces have no statement and no reason)`, '');
  const bySlug = new Map(p.pieces.map((s) => [s.slug, s]));
  // A piece of a bug is told under its bug, below: the groups hold the others.
  for (const g of p.groups) {
    const slugs = g.slugs.filter((slug) => !bySlug.get(slug).bug);
    if (slugs.length === 0) continue;
    say(g.kind === 'narrative' ? `In run order — ${g.narrative}` : g.kind === 'uncrossed' ? 'Pieces crossed by no narrative' : 'Pieces with no runtime line', '');
    for (const slug of slugs) say(...pieceText(p, bySlug.get(slug), false), '');
  }
  // A bug at a time, as the plan page tells them: what is wrong, then the pieces that fix it, in the file's order.
  const sections = p.doc?.sections ?? [];
  for (const bug of sections.filter((x) => x.bug)) {
    const fixing = p.pieces.filter((piece) => piece.bug?.anchor === bug.anchor).sort((a, b) => (a.doc?.section.line ?? 0) - (b.doc?.section.line ?? 0));
    say(`Bug — ${bug.title}   (${p.doc.file}:${bug.line}, fixed by ${fixing.map((piece) => `#${piece.slug}`).join(', ') || 'NO PIECE'})`, ...blockLines(bug.blocks, '  '), '');
    for (const piece of fixing) say(...pieceText(p, piece, false), '');
  }
  for (const section of sections.filter((x) => x.piece === null && !x.bug)) say(`Decided across pieces — ${section.title}`, ...blockLines(section.blocks, '  '), '');
  if (p.journeyCases?.length) {
    say('─'.repeat(60), `Journey cases of the spec, to write — ${p.journeyCases.length}, each once the pieces behind it are in`);
    for (const journey of [...new Set(p.journeyCases.map((c) => c.journey))]) {
      say(`  ${journey}`);
      for (const c of p.journeyCases.filter((x) => x.journey === journey)) say(`    ${at(c)}  at ${c.screen} — ${c.title}`);
    }
    say('');
  }
  if (p.pointers?.length) {
    say('─'.repeat(60), `Planned elsewhere — ${plural(p.pointers.length, 'piece')} this plan relies on and holds none of: each is planned and built in its repository's plan of ${p.feature}`);
    for (const x of p.pointers) {
      const there = x.target === null ? 'not checked: no checkout known here' : x.target.statement === null ? 'NO SUCH PIECE THERE' : `${x.target.approvedOn ? `approved ${x.target.approvedOn}` : 'not approved yet'} — ${x.target.statement}`;
      say(`  ${x.repository} #${x.slug} (${there})`, `    ${x.reason}`);
    }
    say('');
  }
  if (p.rules.length) {
    say('─'.repeat(60), `Rules of ${p.rulesFile} — one test owns each, or ${p.doc ? p.doc.file : 'plan.md'} waives it`);
    for (const r of p.rules) say(`  ${r.slug}: ${r.waiver ? `no test${r.waiver.toConfirm ? ' (TO CONFIRM)' : ''} — ${r.waiver.reason}` : r.owners.length === 0 ? 'NO OWNER YET' : r.owners.length === 1 ? `owned by ${at(r.owners[0])}` : `TWO OWNERS — ${r.owners.map(at).join(', ')}`}`);
  }
  if (p.doc?.lots.length) {
    say('─'.repeat(60), `Delivery — ${plural(p.doc.lots.length, 'lot')}, in order: one implementer and one review a lot, one commit a piece`);
    for (const lot of p.doc.lots) say(`  ${lotLine(p, lot)}`, `    ${lot.reason}`);
    say('');
  }
  say('─'.repeat(60), ...deltaText(p));
  if (p.failures.length) say('', 'Fails the check:', ...p.failures.map((f) => `  ${f}`));
  say('', `next: npm run map -- brief ${feature}#<piece>   (a piece with the code at its sites)${p.doc?.lots.length ? `\n      npm run map -- brief ${feature}/<lot>     (a lot: what one implementer is handed)` : ''}`);
}

const lotLine = (p, lot) => {
  const left = p.lotsLeft[lot.slug];
  const owed = left.sites + left.tests + left.cases;
  return `lot ${lot.slug} (${lot.difficulty}) — ${owed === 0 ? 'delivered' : `${plural(left.sites, 'site')}, ${plural(left.tests, 'test')}, ${plural(left.cases, 'journey case')} to go`}: ${[...lot.pieces.map((x) => `#${x}`), ...lot.screens.map((x) => `@${x}`)].join(' ')}`;
};

/** For a comment line of the delta, what that comment stands on today (the approval holds the line, not the
 *  place): two removals worded alike are told apart by the test each goes with. */
function standsOn(p, unit, line) {
  const piece = p.pieces.find((x) => `#${x.slug}` === unit);
  const sites = (piece?.statics ?? []).filter((x) => `${x.removes ? 'removes' : 'changes'} ${x.file} — ${x.text}` === line && x.on);
  return sites.length ? `   [on ${sites.map((x) => x.on).join(' · ')}]` : '';
}

/** What differs from the approved plan, a unit at a time: `+` a line the approval did not hold, `−` one it did. */
function deltaText(p) {
  if (!p.approved) return [p.doc ? `Never approved. On the reviewer's word: ${typed(tool('render.ts'))} --approve ${p.feature}` : 'No plan.md to approve.'];
  const head = `Approved on ${p.approved.approvedOn} at ${p.approved.base.slice(0, 8)} (${p.approved.file})`;
  if (p.delta.length === 0) return [`${head} — as approved`];
  return [`${head} — ${plural(p.delta.length, 'unit')} not as approved`, ...p.delta.flatMap((d) => [
    `  ${d.state} ${d.kind} ${d.name}${d.reason === 'needed' ? '  — NO "Changed:" in its section' : ''}`,
    ...unitLines(p, d),
  ]), ...(p.moves?.length ? [`  moved between pieces, unchanged — nothing to answer:`, ...p.moves.map((m) => `    ${m.from} → ${m.to} — ${m.facet}: ${m.text}`)] : [])];
}

/** One unit's delta, an edit at a time: what moved and why, then the lines that edit comes to; then the lines no
 *  edit names. */
function unitLines(p, d) {
  const line = (l, pad) => `${pad}${l.sign} ${l.facet}: ${l.text}${l.facet === 'comments' && l.sign === '+' ? standsOn(p, d.name, l.text) : ''}`;
  return [
    ...d.edits.flatMap((e) => [`    edit: ${e.change.what ? `${e.change.what} — ` : ''}${e.change.why}`, ...e.lines.map((l) => line(l, '      '))]),
    ...(d.edits.length > 1 && d.unclaimed.some((l) => l.facet !== 'question' && l.facet !== 'notes') ? ['    NAMED BY NO EDIT:'] : []),
    ...d.unclaimed.map((l) => line(l, '    ')),
  ];
}

/** The reviewer's answers, given from the plan's pages (`specs/features/<feature>/plan-feedback.json`): what to
 *  act on first, then what is still unread. An answer to an item reworded since is of an earlier wording. */
function feedback(map, feature) {
  if (!feature) fail('feedback <feature>');
  const p = pickPlan(map, feature);
  const given = (i) => p.feedback[i.key];
  const refused = p.items.filter((i) => given(i)?.verdict === 'refused');
  const approved = p.items.filter((i) => given(i)?.verdict === 'approved');
  const unread = p.items.filter((i) => !given(i));
  const stale = Object.entries(p.feedback).filter(([key]) => !p.items.some((i) => i.key === key));
  say(`Feedback on ${feature} — ${p.items.length} to answer: ${refused.length} not approved, ${approved.length} approved, ${unread.length} not read`, '');
  for (const i of refused) say(`${i.kind === 'question' ? 'ANSWERED    ' : 'NOT APPROVED'} ${i.unit} — ${i.what}`, `  the reviewer: ${given(i).note}`, '');
  for (const i of approved.filter((x) => x.kind === 'question')) say(`YES, AS PROPOSED ${i.unit} — ${i.what}`, '');
  if (approved.some((x) => x.kind === 'edit')) say(`Approved: ${approved.filter((x) => x.kind === 'edit').map((i) => `${i.unit} "${i.what}"`).join('; ')}`, '');
  if (unread.length) say(`Not read yet: ${unread.map((i) => `${i.unit} "${i.what}"`).join('; ')}`, '');
  if (stale.length) say(`Of an earlier wording, to drop — ${stale.length}:`, ...stale.map(([, a]) => `  ${a.verdict} ${a.unit} — ${a.what}${a.note ? `: ${a.note}` : ''}`));
}

/** A plan's check in a screen, for whoever edits it: the lots, each unit that is not as approved in one line,
 *  and what fails. The whole `comprehension-render --check` prints every narrative and every page token (18k tokens a
 *  run); a plan edit needs these lines and the typecheck. */
function check(map, feature) {
  if (!feature) fail('check <feature>');
  const p = pickPlan(map, feature);
  for (const lot of p.doc?.lots ?? []) say(lotLine(p, lot));
  if (!p.approved) say(p.doc ? 'never approved' : 'no plan.md');
  else {
    say(`approved on ${p.approved.approvedOn} at ${p.approved.base.slice(0, 8)} — ${p.delta.length ? `${plural(p.delta.length, 'unit')} not as approved` : 'as approved'}`);
    for (const d of p.delta) say(`  ${d.state} ${d.kind} ${d.name} — ${d.facets.map((f) => `${f.facet}${f.added.length ? ` +${f.added.length}` : ''}${f.removed.length ? ` −${f.removed.length}` : ''}`).join(', ')}${d.reason === 'needed' ? '  — NO "Changed:" in its section' : ''}`);
  }
  for (const m of p.moves ?? []) say(`  moved, unchanged: ${m.from} → ${m.to} — ${m.facet}: ${m.text}`);
  for (const line of p.info) say(`info: ${line}`);
  if (p.failures.length === 0) return say('', `check ${feature}: the plan passes. Its lines: npm run map -- brief ${feature}/<lot>`);
  say('', `check ${feature}: ${plural(p.failures.length, 'failure')}`, ...p.failures.map((f) => `  ${f}`));
  process.exitCode = 1;
}

/** `<feature>#<piece>` or `<feature>/<lot>`: the plan, and the pieces it names. */
function scope(map, name, verb) {
  const m = /^([^#/]+)([#/])(.+)$/.exec(name);
  if (!m) fail(`${verb} <feature>#<piece>   or   ${verb} <feature>/<lot>`);
  const p = pickPlan(map, m[1]);
  if (m[2] === '#') {
    const piece = p.pieces.find((s) => s.slug === m[3]);
    if (!piece) fail(`${m[1]} has no piece #${m[3]}. Its pieces: ${p.pieces.map((s) => `#${s.slug}`).join(', ')}`);
    return { p, lot: null, pieces: [piece] };
  }
  const lot = p.doc?.lots.find((l) => l.slug === m[3]);
  if (!lot) fail(`${m[1]} has no lot "${m[3]}". ${p.doc?.lots.length ? `Its lots: ${p.doc.lots.map((l) => l.slug).join(', ')}` : `Its plan.md has no "## Delivery" yet`}`);
  // A piece whose every site is implemented and that has no tagged test is no longer in the plan: the lot still names it.
  return { p, lot, pieces: lot.pieces.map((slug) => p.pieces.find((s) => s.slug === slug)).filter(Boolean) };
}

function brief(map, name) {
  const { p, lot, pieces } = scope(map, name, 'brief');
  if (lot) say(lotLine(p, lot), `  ${lot.reason}`, `  One commit per piece, in this order. Its message ends with the line "Piece: ${p.feature}#<piece>". A piece that cannot typecheck alone lands with the one it needs, in one commit naming both.${lot.screens.length ? ' The journey cases come last.' : ''}`, '');
  const printed = new Map();
  for (const piece of pieces) say(...pieceText(p, piece, true, !lot, printed), '');
  // The decisions across pieces are told whole: they hold what no site carries (a snapshot to regenerate, a doc made stale).
  const decisions = (p.doc?.sections ?? []).filter((d) => d.piece === null && pieces.some((piece) => (d.bug ? piece.bug?.anchor === d.anchor : d.slugs.includes(piece.slug))));
  for (const d of decisions) say(`${d.bug ? 'Bug' : 'Decided across pieces'} — ${d.title}  (${p.doc.file}:${d.line})`, ...blockLines(d.blocks, '  '), '');
  // What the pieces outside this brief were built with, that this work may stand on.
  const before = p.pieces.filter((x) => !pieces.includes(x)).flatMap((x) => (x.doc?.notes ?? []).map((n) => `  #${x.slug}: ${n.text}`));
  if (before.length) say('Notes on what is built elsewhere in the plan:', ...before, '');
  const cases = lot ? (p.journeyCases ?? []).filter((c) => lot.screens.includes(c.screen)) : [];
  if (cases.length) say(`Journey cases the lot writes last — ${cases.length}`, ...cases.map((c) => `  ${at(c)}  at ${c.screen} — ${c.title}`), '');
  const owned = p.rules.filter((r) => r.owners.some((o) => pieces.some((piece) => piece.slug === o.slug)));
  if (owned.length) say(`Rules of the spec ${lot ? 'the lot' : 'this piece'}'s tests own:`, ...owned.map((r) => `  ${r.slug}: ${r.text}`));
}

/** The tests that reach the sites of a piece or of a lot today, by file. A test listed here already crosses the
 *  place the change lands in: a planned unit test that says what one of these says is not written, and one of
 *  these that a planned narrative case now holds is deleted (`@planned.remove` above it). */
function reach(map, name) {
  const { p, lot, pieces } = scope(map, name, 'reach');
  const sites = pieces.flatMap((piece) => piece.sites);
  const byFile = new Map();
  for (const x of sites) for (const r of x.reachedBy) for (const title of r.titles ?? []) {
    const tests = byFile.get(r.file) ?? byFile.set(r.file, new Map()).get(r.file);
    tests.set(title, (tests.get(title) ?? 0) + 1);
  }
  const total = [...byFile.values()].reduce((n, tests) => n + tests.size, 0);
  say(`${lot ? `lot ${lot.slug}` : `#${pieces[0].slug}`} — ${plural(total, 'test')} in ${plural(byFile.size, 'file')} reach its ${plural(sites.length, 'site')} today${sites.length ? `   (the number after a title: how many of the ${sites.length} it reaches)` : ''}`, '');
  for (const [file, tests] of [...byFile].sort(([a], [b]) => a.localeCompare(b))) say(`${file} — ${tests.size}`, ...[...tests].map(([title, n]) => `    ${title}  · ${n}`), '');
  // Only a `planned(…)` call is crossed by a run. A comment on code that runs is seen by no test: say so, or the list reads as whole.
  const untraced = pieces.flatMap((piece) => piece.statics).filter((x) => !config.tests.roots.some((folder) => x.file.startsWith(folder)) && !x.file.startsWith(`${config.docs}/`));
  if (untraced.length) say(`NOT LISTED ABOVE — the tests of what ${untraced.length === 1 ? 'this comment site changes' : `these ${untraced.length} comment sites change`}: a comment is crossed by no run, so find them by the symbol`, ...untraced.map((x) => `    ${at(x)} — ${x.text}`), '');
  const planned = pieces.flatMap((piece) => piece.todos.filter((t) => !t.written));
  if (planned.length) say(`Planned, to write — ${planned.length}`, ...planned.map((t) => `    ${at(t)}  ${t.tier} — ${t.title}`));
  const failing = pieces.flatMap((piece) => piece.todos.filter((t) => t.reproduction));
  if (failing.length) say(`Failing today, the reproductions — ${failing.length}`, ...failing.map((t) => `    ${at(t)}  ${t.tier} — ${t.title}`));
}

const VERBS = {
  narratives: () => narratives(snapshot()),
  narrative: () => (arg ? narrative(snapshot(), arg) : narratives(snapshot())),
  step: () => (/#\d+$/.test(arg) ? step(snapshot(), arg) : fail('step <slug>#<n>')),
  around: () => (arg ? around(snapshot(), arg) : fail('around <slug>')),
  where: () => where(snapshot(), arg),
  spec: () => specText(arg),
  plan: () => plan(snapshot(), arg),
  brief: () => brief(snapshot(), arg),
  reach: () => reach(snapshot(), arg),
  check: () => check(snapshot(), arg),
  feedback: () => feedback(snapshot(), arg),
  help: () => say(readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 18).map((l) => l.replace(/^ \* ?/, '')).join('\n')),
};

if (!VERBS[verb]) fail(`no verb "${verb}". Verbs: ${Object.keys(VERBS).join(', ')} — npm run map -- help`);
VERBS[verb]();
