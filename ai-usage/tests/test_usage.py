import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters import parse
from pricing import price
from usage import bind, collect, connect, coverage, load_rows, merge_request, project_scope, summarize


def record(kind, payload, n=0):
    return {"type": kind, "timestamp": f"2026-09-29T10:{n:02}:00Z", "payload": payload}


def token(n, total, *, inp=100, cached=60, write=20, output=10):
    u = {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": output, "reasoning_output_tokens": 3}
    if write is not None:
        u["cache_write_input_tokens"] = write
    return record("event_msg", {"type": "token_count", "info": {"total_token_usage": {"total_tokens": total}, "last_token_usage": u}}, n)


def codex(session="session", parent=None):
    return [record("session_meta", {"id": session, "cwd": "/project", "parent_thread_id": parent, "cli_version": "fixture"}),
            record("turn_context", {"model": "gpt-6-sol", "effort": "medium", "turn_id": "turn-1"})]


def claude(n, output, request="req"):
    return {"type": "assistant", "timestamp": f"2026-09-29T10:{n:02}:00Z", "cwd": "/project",
            "sessionId": "session", "requestId": request, "effort": "high",
            "message": {"model": "claude-opus-5-5", "content": [], "usage": {
                "input_tokens": 10, "cache_read_input_tokens": 60, "cache_creation_input_tokens": 20,
                "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 20},
                "output_tokens": output}}}


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.card = json.loads((ROOT / "prices.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def file(self, rows, name="session.jsonl"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return path

    def test_codex_repeated_status_counts_once_and_normalizes_cache(self):
        run, rows = parse(self.file(codex() + [token(1, 110), token(2, 110), token(3, 220)]), "codex")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["tokens"], {"input": 20, "cached": 60, "write": 20,
                         "write_5m": None, "write_1h": None, "output": 10, "reasoning": 3})
        self.assertEqual(run["request_count"], 2)

    def test_codex_fork_prefix_has_same_request_identity(self):
        a = parse(self.file(codex("a") + [token(1, 110)], "a.jsonl"), "codex")[1][0]
        b = parse(self.file(codex("b", "a") + [token(1, 110)], "b.jsonl"), "codex")[1][0]
        self.assertEqual(a["id"], b["id"])
        for left, right in ((a, b), (b, a)):
            merged = merge_request(left, right)
            self.assertEqual((merged["session"], merged["actor"], merged["turn"]), ("codex:a", "main", 0))

    def test_enriched_cache_writes_recompute_fresh_input(self):
        a = parse(self.file(codex() + [token(1, 110, write=None)]), "codex")[1][0]
        b = parse(self.file(codex() + [token(1, 110, write=20)]), "codex")[1][0]
        for left, right in ((a, b), (b, a)):
            merged = merge_request(left, right)
            self.assertEqual(merged["tokens"]["input"], 20)
            self.assertEqual(merged["context"], 100)

    def test_codex_native_turns_exclude_idle_and_tool_messages(self):
        rows = codex() + [token(1, 110), record("event_msg", {"type":"task_complete"}, 2),
                         record("event_msg", {"type":"task_started", "turn_id":"turn-2"}, 20),
                         record("response_item", {"role":"user", "content":[{"type":"input_text", "text":"continue"}]}, 20),
                         record("turn_context", {"turn_id":"turn-2", "model":"gpt-6-sol"}, 20),
                         token(21, 220), record("event_msg", {"type":"task_complete"}, 22)]
        run, measured = parse(self.file(rows), "codex")
        self.assertEqual([r["turn"] for r in measured], [0, 1])
        self.assertEqual(run["active_seconds"], 240)

    def test_codex_new_turn_repeating_previous_total_is_not_new_spend(self):
        events = codex()+[token(1,110),record("event_msg",{"type":"task_complete"},2),
                         record("event_msg",{"type":"task_started","turn_id":"two"},20),
                         token(20,110),token(21,220)]
        _,rows=parse(self.file(events),"codex")
        self.assertEqual(len(rows),2)
        self.assertEqual([r["turn"] for r in rows],[0,1])

    def test_claude_content_blocks_use_largest_partial_usage(self):
        rows = parse(self.file([claude(1, 7), claude(2, 232)]), "claude")[1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tokens"]["output"], 232)
        self.assertEqual(rows[0]["context"], 90)

    def test_claude_resume_excludes_idle_and_records_first_edit(self):
        first = claude(1, 10)
        first["message"]["stop_reason"] = "end_turn"
        resume = {"type": "user", "timestamp": "2026-09-29T10:20:00Z", "origin": {"kind": "coordinator"},
                  "cwd": "/project", "sessionId": "session", "message": {"content": "Apply the accepted fixes"}}
        last = claude(21, 5, "next")
        last["message"]["content"] = [{"type": "tool_use", "name": "Edit", "input": {}}]
        run, rows = parse(self.file([first, resume, last], "session/subagents/agent-worker.jsonl"), "claude")
        self.assertEqual(rows[1]["turn"], 1)
        self.assertEqual(run["active_seconds"], 60)
        self.assertEqual(run["duration_seconds"], 1200)
        self.assertEqual(run["requests_before_first_edit"], 1)

    def test_claude_human_resume_reopens_span_but_tool_result_does_not(self):
        first = claude(1, 10)
        first["message"]["stop_reason"] = "end_turn"
        user = lambda n, content: {"type":"user", "timestamp":f"2026-09-29T10:{n:02}:00Z",
                                  "cwd":"/project", "sessionId":"session", "message":{"content":content}}
        last = claude(22, 5, "next")
        last["message"]["stop_reason"] = "end_turn"
        run, measured = parse(self.file([user(0,"Start"), first, user(20,"Continue"),
                                        user(21,[{"type":"tool_result", "content":"done"}]), last]), "claude")
        self.assertEqual([r["turn"] for r in measured], [0,1])
        self.assertEqual(run["active_seconds"], 180)

    def test_partial_tail_tolerated_interior_corruption_rejected(self):
        path = self.file(codex() + [token(1, 110)])
        with path.open("a") as f:
            f.write('{"unfinished":')
        self.assertEqual(len(parse(path, "codex")[1]), 1)
        path.write_text(path.read_text() + "\n{}\n")
        with self.assertRaises(ValueError):
            parse(path, "codex")

    def test_invalid_usage_fails_instead_of_zero(self):
        event = token(1, 110)
        event["payload"]["info"]["last_token_usage"]["output_tokens"] = "10"
        with self.assertRaises(ValueError):
            parse(self.file(codex() + [event]), "codex")

    def test_prices_distinguish_credits_api_and_context_band(self):
        row = parse(self.file(codex() + [token(1, 110)]), "codex")[1][0]
        self.assertAlmostEqual(price(row, self.card, "api")[0], (20*2 + 60*.2 + 20*2.5 + 10*10)/1e6)
        self.assertAlmostEqual(price(row, self.card, "credits")[0], (40*50 + 60*5 + 10*250)/1e6)
        row["context_band"] = "long"
        row["speed"] = "fast"
        self.assertAlmostEqual(price(row, self.card, "api")[0], ((40+12+50)*2 + 100*1.5)*2/1e6)
        self.assertAlmostEqual(price(row, self.card, "credits")[0], (2000+300+2500)*2.5/1e6)

    def test_missing_price_or_writes_never_silently_free(self):
        row = parse(self.file(codex() + [token(1, 110, write=None)]), "codex")[1][0]
        self.assertIsNone(price(row, self.card, "api")[0])
        self.assertIsNotNone(price(row, self.card, "credits")[0])
        row["model"] = "gpt-6-sol-new"
        self.assertEqual(price(row, self.card, "credits"), (None, "unknown model"))
        row["model"] = "gpt-6-sol"
        row["region"] = "us"
        self.assertEqual(price(row, self.card, "api"), (None, "regional pricing unavailable"))

    def test_incremental_collection_preserves_purged_sources(self):
        path = self.file(codex() + [token(1, 110)], "codex/sessions/file.jsonl")
        args = SimpleNamespace(codex_home=self.root/"codex", claude_home=self.root/"claude", full=False)
        db = connect(self.root/"ledger.sqlite3")
        with patch("usage.project_scope", return_value=lambda cwd: "e-footprint" if cwd == "/project" else None):
            self.assertEqual(collect(args, db, {}), 0)
            self.assertEqual(collect(args, db, {}), 0)
            path.unlink()
            args.full = True
            self.assertEqual(collect(args, db, {}), 0)
        self.assertEqual(db.execute("select count(*) from requests").fetchone()[0], 1)
        db.close()

    def test_reimport_reconciles_changed_source_without_erasing_purged_history(self):
        a = self.file(codex()+[token(1,110),token(2,220)],"codex/sessions/a.jsonl")
        b = self.file(codex("other")+[token(3,330)],"codex/sessions/b.jsonl")
        args = SimpleNamespace(codex_home=self.root/"codex",claude_home=self.root/"claude",full=True)
        db = connect(self.root/"ledger.sqlite3")
        with patch("usage.project_scope",return_value=lambda cwd:"e-footprint"):
            collect(args,db,{})
            b.unlink()
            self.file(codex()+[token(1,110)],"codex/sessions/a.jsonl")
            collect(args,db,{})
        rows,_=load_rows(db,[])
        self.assertEqual(len(rows),2)
        self.assertTrue(any(r["session"]=="codex:other" for r in rows))
        db.close()

    def test_binding_boundaries_parent_inheritance_and_task_namespace(self):
        db = connect(self.root/"ledger.sqlite3")
        for sid, parent in [("main", None), ("child", "main")]:
            run, rows = parse(self.file(codex(sid, parent) + [token(1 if sid=='main' else 2, 110)], sid+".jsonl"), "codex")
            db.execute("insert into runs values (?,?)", (run["id"], json.dumps(run)))
            for row in rows:
                row["project"] = "e-footprint"
                db.execute("insert into requests values (?,?)", (row["id"], json.dumps(row)))
        db.execute("insert into bindings values (?,?,?)", ("codex:main", "2026-09-29T10:00:00Z", json.dumps({"owner":"e-footprint", "feature":"feature", "run":"A", "stage":"implement", "role":"supervisor"})))
        db.execute("insert into bindings values (?,?,?)", ("codex:child", "2026-09-29T10:00:00Z", json.dumps({"role":"implementer", "task":1})))
        db.execute("insert into bindings values (?,?,?)", ("codex:main", "2026-09-29T11:00:00Z", json.dumps({"feature":"later"})))
        db.commit()
        rows, runs = load_rows(db, [])
        child = next(r for r in rows if r["session"]=="codex:child")
        self.assertEqual((child["feature"], child["role"]), ("feature", "implementer"))
        twin = {**child, "id":"another", "owner":"e-footprint-interface"}
        result = summarize(rows+[twin], runs, self.card, "api")
        self.assertEqual(len(result["tasks"]), 2)
        db.close()

    def test_separate_ledgers_deduplicate_same_request(self):
        paths = [self.root/"a.db", self.root/"b.db"]
        run, rows = parse(self.file(codex() + [token(1,110)]), "codex")
        row = {**rows[0], "project":"e-footprint"}
        for path in paths:
            db = connect(path)
            db.execute("insert into requests values (?,?)", (row["id"], json.dumps(row)))
            db.commit(); db.close()
        db = connect(paths[0])
        self.assertEqual(len(load_rows(db, [paths[1]])[0]), 1)
        db.close()

    def test_rebinding_replaces_task_and_run_at_equivalent_timezone(self):
        db = connect(self.root/"ledger.sqlite3")
        run, rows = parse(self.file(codex() + [token(1,110),token(2,220)]), "codex")
        for row in rows:
            row.update(project="e-footprint", task=9)
            db.execute("insert into requests values (?,?)", (row["id"], json.dumps(row)))
        fields = dict(provider="codex", session="session", owner="e-footprint", feature="first", stage="implement", run="A", task=1, role="implementer")
        bind(SimpleNamespace(**fields, since="2026-09-29T10:00:00Z"),db)
        fields.update(feature="second",run=None,task=None,role="supervisor")
        bind(SimpleNamespace(**fields, since="2026-09-29T12:02:00+02:00"),db)
        result, _ = load_rows(db, [])
        result.sort(key=lambda r:r["ts"])
        self.assertEqual(result[0]["feature"], "first")
        self.assertEqual(result[1]["feature"], "second")
        self.assertIsNone(result[1]["task"])
        self.assertIsNone(result[1]["run"])
        db.close()

    def test_child_inherits_parent_scope_at_creation_not_request_time(self):
        db = connect(self.root/"ledger.sqlite3")
        run, rows = parse(self.file(codex("child", "main") + [token(20, 110)]), "codex")
        db.execute("insert into runs values (?,?)", (run["id"],json.dumps(run)))
        row = {**rows[0], "project":"e-footprint"}
        db.execute("insert into requests values (?,?)", (row["id"], json.dumps(row)))
        for minute,feature in [(0,"original"),(10,"next")]:
            db.execute("insert into bindings values (?,?,?)", ("codex:main",f"2026-09-29T10:{minute:02}:00Z",json.dumps({"feature":feature})))
        self.assertEqual(load_rows(db,[])[0][0]["feature"],"original")
        db.close()

    def test_empty_coverage_and_registered_missing_session_are_visible(self):
        db = connect(self.root/"ledger.sqlite3")
        db.execute("insert into bindings values (?,?,?)", ("codex:missing","2026-09-29T10:00:00Z",json.dumps({"feature":"feature"})))
        missing = coverage(db,[],[],SimpleNamespace(feature="feature"))
        self.assertEqual(len(missing["registered_intervals_without_measurements"]),1)
        self.assertTrue(missing["warnings"])
        self.assertIsNone(summarize([],{},self.card,"api")["total_amount"])
        db.close()

    def test_missing_child_measurements_inherit_feature_filter(self):
        db = connect(self.root/"ledger.sqlite3")
        run, _ = parse(self.file(codex("child","main")),"codex")
        db.execute("insert into runs values (?,?)",(run["id"],json.dumps(run)))
        for sid,attrs in [("main",{"feature":"feature"}),("child",{"role":"reviewer","task":1})]:
            db.execute("insert into bindings values (?,?,?)",("codex:"+sid,"2026-09-29T10:00:00Z",json.dumps(attrs)))
        result = coverage(db,[],[],SimpleNamespace(feature="feature"))
        missing = result["registered_intervals_without_measurements"]
        self.assertEqual(len(missing),2)
        self.assertTrue(all(r["feature"]=="feature" for r in missing))
        db.close()

    def test_collection_failure_persists_for_reports(self):
        self.file(codex()+[token(1,110)],"codex/sessions/good.jsonl")
        bad = self.file(codex(),"codex/sessions/bad.jsonl")
        bad.write_text(bad.read_text()+"not-json\n")
        db = connect(self.root/"ledger.sqlite3")
        args = SimpleNamespace(codex_home=self.root/"codex",claude_home=self.root/"claude",full=False)
        with patch("usage.project_scope",return_value=lambda cwd:"e-footprint"):
            self.assertEqual(collect(args,db,{}),1)
        state = coverage(db,[],load_rows(db,[])[0],SimpleNamespace())
        self.assertEqual(len(state["errors"]),1)
        db.close()

    def test_task_duration_does_not_recount_other_turns(self):
        run, rows = parse(self.file(codex("child","main") + [token(1,110),record("event_msg",{"type":"task_complete"},2),
              record("event_msg",{"type":"task_started","turn_id":"two"},20),token(21,220),
              record("event_msg",{"type":"task_complete"},22)]),"codex")
        for n,row in enumerate(rows):
            row.update(owner="e-footprint",feature="feature",role="implementer",task=n+1)
        result = summarize(rows,{run["id"]:run},self.card,"api")
        self.assertEqual([t["agent_seconds"] for t in result["tasks"]],[120,120])


if __name__ == "__main__":
    unittest.main()
