#!/usr/bin/env python3
"""Local-only, dependency-free Claude/Codex usage ledger. Run --help for commands."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from adapters import TOKEN_FIELDS, VERSION, metadata, parse, timestamp, utc
from pricing import price

HERE = Path(__file__).resolve().parent
ATTRIBUTES = ("owner", "feature", "run", "task", "role", "stage")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@lru_cache(maxsize=None)
def git_common(path):
    try:
        return Path(subprocess.check_output(["git", "-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                           stderr=subprocess.DEVNULL, text=True).strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return None


def main_checkout():
    common = git_common(HERE.parent)
    return common.parent if common and common.name == ".git" else HERE.parent


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript('''
        CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sources (path TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bindings (session TEXT, since TEXT, payload TEXT NOT NULL, PRIMARY KEY(session, since));
        CREATE TABLE IF NOT EXISTS collection_state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS observations (source TEXT, request_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(source, request_id));
        CREATE INDEX IF NOT EXISTS observations_request ON observations(request_id);
    ''')
    return db


def paths(args, provider):
    if provider == "codex":
        for name in ("sessions", "archived_sessions"):
            yield from sorted((args.codex_home / name).rglob("*.jsonl"))
    else:
        yield from sorted((args.claude_home / "projects").rglob("*.jsonl"))


def project_scope(repo, config):
    roots = [repo.resolve()]
    roots += [(repo / p).resolve() for p in config.get("companion_paths", []) if (repo / p).is_dir()]
    common = {git_common(p): p.name for p in roots if git_common(p)}
    workspace = repo.parent.resolve() if len(roots) > 1 else None

    def match(cwd):
        if not cwd:
            return None
        path = Path(cwd).resolve()
        if workspace and path == workspace:
            return "workspace"
        for root in roots:
            if path == root or root in path.parents:
                return root.name
        return common.get(git_common(path))
    return match


def merge_request(old, new):
    # Forks/repeated extraction must not add spend or replace a fuller partial count.
    if old["session"] == new["session"]:
        result = {**old, **new}
    else:
        # Keep actor/turn/labels together with the originating session, independent of scan order.
        if old["session"] in (new.get("parent"), new.get("forked_from")):
            origin = old
        elif new["session"] in (old.get("parent"), old.get("forked_from")):
            origin = new
        else:
            origin = min((old, new), key=lambda r: (timestamp(r.get("session_start") or r["ts"]), r["session"]))
        result = dict(origin)
    result["ts"] = utc(min((old["ts"], new["ts"]), key=timestamp))
    result["tokens"] = {}
    for field in old["tokens"]:
        values = [r["tokens"].get(field) for r in (old, new)]
        known = [v for v in values if v is not None]
        result["tokens"][field] = max(known) if known else None
    result["context"] = max(old["context"], new["context"])
    if result["provider"] == "codex":
        result["tokens"]["input"] = result["context"] - result["tokens"]["cached"] - (result["tokens"]["write"] or 0)
        if result["tokens"]["input"] < 0:
            raise ValueError("Inconsistent merged input counters")
    result["context_band"] = "long" if result["context"] > 272000 else "short"
    return result


def collect(args, db, config):
    match = project_scope(main_checkout(), config)
    changed = kept = skipped = 0
    errors = []
    found = 0
    for provider in ("codex", "claude"):
        for path in paths(args, provider):
            found += 1
            try:
                st = path.stat()
                sidecar = path.with_suffix(".meta.json")
                extra = str(sidecar.stat().st_mtime_ns) if sidecar.exists() else ""
                fingerprint = f"{VERSION}:{st.st_size}:{st.st_mtime_ns}:{extra}"
                previous = db.execute("SELECT fingerprint FROM sources WHERE path=?", (str(path),)).fetchone()
                if not args.full and previous and previous[0] == fingerprint:
                    kept += 1
                    continue
                meta = metadata(path, provider)
                project = match(meta.get("cwd"))
                if not project:
                    skipped += 1
                    continue
                run, rows = parse(path, provider)
                run["project"] = project
                with db:
                    before = db.execute("SELECT payload FROM runs WHERE id=?", (run["id"],)).fetchone()
                    if not before or json.loads(before[0]).get("version", 0) < VERSION or json.loads(before[0])["request_count"] <= run["request_count"]:
                        db.execute("INSERT OR REPLACE INTO runs VALUES (?,?)", (run["id"], json.dumps(run)))
                    affected = {r[0] for r in db.execute("SELECT request_id FROM observations WHERE source=?", (str(path),))}
                    db.execute("DELETE FROM observations WHERE source=?", (str(path),))
                    for row in rows:
                        row["project"] = project
                        affected.add(row["id"])
                        db.execute("INSERT INTO observations VALUES (?,?,?)", (str(path), row["id"], json.dumps(row)))
                    # Reconcile only re-read sources. Observations whose source was purged remain durable.
                    for key in affected:
                        candidates = [json.loads(p) for (p,) in db.execute("SELECT payload FROM observations WHERE request_id=?", (key,))]
                        if candidates:
                            row = candidates[0]
                            for candidate in candidates[1:]:
                                row = merge_request(row, candidate)
                            db.execute("INSERT OR REPLACE INTO requests VALUES (?,?)", (key, json.dumps(row)))
                        else:
                            db.execute("DELETE FROM requests WHERE id=?", (key,))
                    db.execute("INSERT OR REPLACE INTO sources VALUES (?,?)", (str(path), fingerprint))
                changed += 1
            except (ValueError, OSError, sqlite3.Error) as exc:
                errors.append(f"{provider} {path.name}: {exc}")
    result = {"changed_sources": changed, "unchanged_sources": kept, "out_of_scope_sources": skipped,
              "sources_found": found, "requests": db.execute("SELECT count(*) FROM requests").fetchone()[0],
              "errors": errors, "snapshot_at": now()}
    if not found:
        result["warning"] = "No local transcript files found; this is missing coverage, not measured zero use."
    with db:
        db.execute("INSERT OR REPLACE INTO collection_state VALUES (1,?)", (json.dumps(result),))
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


def bind(args, db):
    session = args.session if args.session.startswith(args.provider + ":") else args.provider + ":" + args.session
    values = {k: getattr(args, k) for k in ATTRIBUTES if getattr(args, k) is not None}
    if not values:
        raise ValueError("Specify attribution fields")
    since = utc(args.since or now())
    with db:
        db.execute("INSERT OR REPLACE INTO bindings VALUES (?,?,?)", (session, since, json.dumps(values)))
    print(json.dumps({"session": session, "since": since, **values}, indent=2))


def load_rows(db, extra):
    requests, runs, bindings = {}, {}, {}
    # Read secondary ledgers without creating/migrating them; both repo copies may contain the same sessions.
    databases = [db]
    try:
        for path in extra:
            databases.append(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True))
        for source in databases:
            for key, payload in source.execute("SELECT id,payload FROM requests"):
                row = json.loads(payload)
                requests[key] = merge_request(requests[key], row) if key in requests else row
            for key, payload in source.execute("SELECT id,payload FROM runs"):
                row = json.loads(payload)
                if key not in runs or row["request_count"] >= runs[key]["request_count"]:
                    runs[key] = row
            for session, since, payload in source.execute("SELECT session,since,payload FROM bindings"):
                key = (session, utc(since))
                value = json.loads(payload)
                if key in bindings and bindings[key] != value:
                    raise ValueError(f"Conflicting attribution for {session} at {since}")
                bindings[key] = value
    finally:
        for source in databases[1:]:
            source.close()
    attributes = attribute_resolver(runs, bindings)
    for row in requests.values():
        row.update(attributes(row["session"], row["ts"]))
        row["owner"] = row.get("owner") or row["project"]
        row["role"] = row.get("role") or ("supervisor" if row["actor"] == "main" and row.get("stage") == "implement" else row["actor"])
    return list(requests.values()), runs


def attribute_resolver(runs, bindings):
    by_session = defaultdict(list)
    for (session, since), value in bindings.items():
        by_session[session].append((since, value))
    for values in by_session.values():
        values.sort()

    def attributes(session, ts, seen=None):
        seen = set() if seen is None else seen
        if session in seen:
            raise ValueError("Cycle in session parents")
        seen.add(session)
        run = runs.get(session, {})
        value = {}
        if run.get("parent"):
            # Feature/run inheritance survives unnamed agents. Role/task belong to the child.
            value = {k: v for k, v in attributes(run["parent"], run.get("start") or ts, seen).items()
                     if k in ("owner", "feature", "run", "stage")}
        inherited = dict(value)
        for since, data in by_session.get(session, []):
            if timestamp(since) <= timestamp(ts):
                # Each binding replaces local attribution; omitted fields cannot leak from old work.
                value = {**dict.fromkeys(ATTRIBUTES), **inherited, **data}
        return value
    return attributes


def coverage(db, extra, rows, filters):
    """Coverage is observed collection state plus registrations; unregistered sessions stay unknowable."""
    databases = [db]
    snapshots, bindings, runs = [], {}, {}
    try:
        for path in extra:
            databases.append(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True))
        for source in databases:
            if source.execute("SELECT 1 FROM sqlite_master WHERE name='collection_state'").fetchone():
                snapshots += [json.loads(p) for (p,) in source.execute("SELECT payload FROM collection_state")]
            for session, since, payload in source.execute("SELECT session,since,payload FROM bindings"):
                bindings[(session, utc(since))] = json.loads(payload)
            for key, payload in source.execute("SELECT id,payload FROM runs"):
                row = json.loads(payload)
                if key not in runs or row["request_count"] >= runs[key]["request_count"]:
                    runs[key] = row
    finally:
        for source in databases[1:]:
            source.close()
    missing = []
    attributes = attribute_resolver(runs, bindings)
    for session, since in bindings:
        attrs = attributes(session, since)
        until = min((t for s, t in bindings if s == session and t > since), default=None)
        # An unscopable registration remains visible rather than disappearing from every filtered report.
        if any(getattr(filters, f, None) and attrs.get(f) is not None and attrs[f] != getattr(filters, f) for f in ("owner", "feature", "run")):
            continue
        if getattr(filters, "since", None) and until and timestamp(until) <= timestamp(filters.since):
            continue
        if not any(r["session"] == session and timestamp(r["ts"]) >= timestamp(since) and
                   (not until or timestamp(r["ts"]) < timestamp(until)) for r in rows):
            missing.append({"session": session, "since": since, **attrs})
    errors = [e for s in snapshots for e in s.get("errors", [])]
    warnings = [s["warning"] for s in snapshots if s.get("warning")]
    if not snapshots:
        warnings.append("No collection snapshot recorded")
    if not rows:
        warnings.append("No matching measurements; zero usage has not been established")
    return {"scope": "Local retained transcripts and registered sessions; unregistered missing sessions cannot be detected",
            "last_collected_at": max((s["snapshot_at"] for s in snapshots), default=None),
            "errors": errors, "warnings": warnings, "registered_intervals_without_measurements": missing}


def summarize(rows, runs, card, surface):
    result = {"requests": len(rows), "priced_requests": 0, "unpriced_requests": 0, "known_amount": 0.0,
              "unit": "USD API-equivalent (tokens only)" if surface == "api" else "estimated Codex credits",
              "rate_card_as_of": card["as_of"], "pricing_basis": "revalued at rate-card date, not a historical bill",
              "unpriced_reasons": {}, "unattributed_requests": 0, "by_role": {}, "by_stage": {}, "by_model": {}, "tasks": [],
              "tokens": dict.fromkeys(TOKEN_FIELDS, 0), "missing_token_counts": dict.fromkeys(TOKEN_FIELDS, 0),
              "assumed_standard_mode_requests": sum(r.get("speed") is None for r in rows)}
    tasks, roles, stages, models = {}, {}, {}, {}
    def bucket(mapping, key):
        return mapping.setdefault(key, {"requests": 0, "known_amount": 0.0, "unpriced_requests": 0,
                                        "tokens": dict.fromkeys(TOKEN_FIELDS, 0), "missing_token_counts": dict.fromkeys(TOKEN_FIELDS, 0),
                                        "follow_up_known_amount": 0.0, "models": set(), "efforts": set()})
    for row in rows:
        amount, reason = price(row, card, surface)
        if reason:
            result["unpriced_requests"] += 1
            label = row["model"] + ": " + reason
            result["unpriced_reasons"][label] = result["unpriced_reasons"].get(label, 0) + 1
        else:
            result["priced_requests"] += 1
            result["known_amount"] += amount
        if not row.get("feature"):
            result["unattributed_requests"] += 1
        destinations = [bucket(roles, row["role"]), bucket(stages, row.get("stage") or "unknown"), bucket(models, row["model"])]
        if row.get("task") is not None:
            key = (row["owner"], row.get("feature"), row.get("run"), row["task"])
            destinations.append(bucket(tasks, key))
        for target in [result] + destinations:
            for field, value in row["tokens"].items():
                if value is None:
                    target["missing_token_counts"][field] += 1
                else:
                    target["tokens"][field] += value
        for data in destinations:
            data["requests"] += 1
            data["known_amount"] += amount or 0
            data["unpriced_requests"] += bool(reason)
            if row["actor"] == "subagent" and row["turn"] > 0:
                data["follow_up_known_amount"] += amount or 0
            data["models"].add(row["model"])
            data["efforts"].add(row.get("effort") or "unknown")
    def finish(data):
        return {**data, "initial_known_amount": data["known_amount"] - data["follow_up_known_amount"],
                "models": sorted(data["models"]), "efforts": sorted(data["efforts"])}
    result["by_role"] = {k: finish(v) for k, v in sorted(roles.items())}
    result["by_stage"] = {k: finish(v) for k, v in sorted(stages.items())}
    result["by_model"] = {k: finish(v) for k, v in sorted(models.items())}
    for key, data in sorted(tasks.items(), key=lambda x: str(x[0])):
        task_rows = [r for r in rows if (r["owner"], r.get("feature"), r.get("run"), r.get("task")) == key]
        sessions = {r["session"] for r in task_rows}
        impls = {r["session"] for r in task_rows if r["role"] in ("implementer-easy", "implementer", "implementer-hard")}
        active = 0
        incomplete_spans = 0
        for session in sessions:
            run = runs.get(session, {})
            if not run.get("parent"):
                continue
            selected = [r for r in task_rows if r["session"] == session]
            for span in run.get("turns", []):
                measured = [r for r in selected if r["turn"] == span["turn"]]
                if not measured:
                    continue
                if min(timestamp(r["ts"]) for r in measured) < timestamp(span["start"]) or len(measured) < span.get("requests", len(measured)):
                    incomplete_spans += 1
                else:
                    active += span["seconds"]
        result["tasks"].append({"owner": key[0], "feature": key[1], "run": key[2], "task": key[3],
                                **finish(data), "implementation_attempts": len(impls),
                                "agent_seconds": active, "partially_attributed_turns": incomplete_spans,
                                "requests_before_first_edit": [runs[s]["requests_before_first_edit"] for s in sorted(impls)
                                                               if s in runs and runs[s].get("requests_before_first_edit") is not None]})
    result["total_amount"] = result["known_amount"] if rows and not result["unpriced_requests"] else None
    result["task_median_known_amount"] = statistics.median([t["known_amount"] for t in result["tasks"]]) if tasks else None
    result["overhead_known_amount"] = result["known_amount"] - sum(t["known_amount"] for t in result["tasks"])
    return result


def report(args, db):
    rows, runs = load_rows(db, args.ledger)
    for field in ("owner", "feature", "run"):
        wanted = getattr(args, field)
        if wanted:
            rows = [r for r in rows if r.get(field) == wanted]
    if args.since:
        rows = [r for r in rows if timestamp(r["ts"]) >= timestamp(args.since)]
    card = json.loads(args.prices.read_text())
    data = summarize(rows, runs, card, args.surface)
    data["coverage"] = coverage(db, args.ledger, rows, args)
    if any(data["coverage"][k] for k in ("errors", "warnings", "registered_intervals_without_measurements")):
        data["total_amount"] = None
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    amount = data["total_amount"]
    print(f"Usage snapshot: {len(rows)} requests · {data['unit']} · rates {card['as_of']}")
    if not rows:
        print("No matching measurements. Check collection and attribution; this is not evidence of zero usage.")
    print(f"{'Measured total' if amount is not None else 'Known subtotal'}: {data['known_amount']:.4f}; unpriced: {data['unpriced_requests']}; unattributed: {data['unattributed_requests']}")
    print("Known tokens: " + "; ".join(f"{k} {data['tokens'][k]:,}" for k in ("input", "cached", "write", "output")))
    print(f"Coverage: {len(data['coverage']['errors'])} source errors; {len(data['coverage']['registered_intervals_without_measurements'])} registered intervals missing measurements. Standard mode assumed for {data['assumed_standard_mode_requests']} requests.")
    for warning in data["coverage"]["warnings"] + data["coverage"]["errors"]:
        print(f"  Coverage: {warning}")
    for role, v in data["by_role"].items():
        print(f"  {role}: {v['known_amount']:.4f} (follow-up {v['follow_up_known_amount']:.4f}); {v['requests']} requests; {', '.join(v['models'])}; effort {', '.join(v['efforts'])}")
    for t in data["tasks"]:
        print(f"  {t['owner']}/{t['feature']} run {t['run']} task {t['task']}: {t['known_amount']:.4f}; attempts {t['implementation_attempts']}; active {t['agent_seconds']/60:.1f} min")
    print(f"Unassigned-to-task overhead: {data['overhead_known_amount']:.4f}. No inference about completed-task quality or subscription limits.")
    for reason, count in data["unpriced_reasons"].items():
        print(f"  Unpriced: {reason} ({count} requests)")
    return 0


def export(args, db):
    rows, _ = load_rows(db, [])
    groups = defaultdict(lambda: defaultdict(int))
    dimensions = ("provider", "owner", "feature", "run", "task", "role", "stage", "model", "effort", "speed", "region", "context_band")
    for row in rows:
        key = (utc(row["ts"])[:10],) + tuple(row.get(k) for k in dimensions)
        groups[key]["requests"] += 1
        for field, value in row["tokens"].items():
            if value is not None:
                groups[key][field] += value
            else:
                groups[key][field + "_missing"] += 1
    measures = sorted({k for values in groups.values() for k in values})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(("date_utc",) + dimensions + tuple(measures))
        for key, values in sorted(groups.items(), key=lambda x: str(x[0])):
            writer.writerow(key + tuple(values.get(k, 0) for k in measures))
    print(f"Wrote {args.output} (aggregate metrics only; export deliberately, not auto-committed)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("AI_USAGE_DATA_DIR", main_checkout() / "ai-usage/.local")))
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="Incrementally preserve metrics from in-scope local transcripts")
    c.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    c.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")))
    c.add_argument("--full", action="store_true")
    b = sub.add_parser("bind", help="Replace local attribution from a timestamp onward; omitted fields clear (or inherit parent scope)")
    b.add_argument("--provider", choices=("codex", "claude"), required=True)
    b.add_argument("--session", required=True)
    b.add_argument("--since", help="UTC ISO timestamp; default now, not the beginning of a reused session")
    for field in ATTRIBUTES:
        b.add_argument("--" + field, type=int if field == "task" else str)
    r = sub.add_parser("report")
    r.add_argument("--surface", choices=("api", "credits"), default="api")
    r.add_argument("--prices", type=Path, default=HERE / "prices.json")
    r.add_argument("--ledger", type=Path, action="append", default=[], help="Merge another ledger.sqlite3, deduplicating requests")
    r.add_argument("--json", action="store_true")
    for field in ("owner", "feature", "run", "since"):
        r.add_argument("--" + field)
    e = sub.add_parser("export")
    e.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((HERE / "config.json").read_text())
    db = connect(args.data_dir.expanduser() / "ledger.sqlite3")
    try:
        return {"collect": lambda: collect(args, db, config), "bind": lambda: bind(args, db),
                "report": lambda: report(args, db), "export": lambda: export(args, db)}[args.command]()
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"ai-usage: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
