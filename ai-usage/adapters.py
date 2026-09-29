"""Read local coding-agent transcripts; retain metrics and attribution, never message bodies."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = 3
STAGES = {
    "spec-specify": "specify", "spec-plan": "plan", "spec-tasks": "tasks",
    "task-implement": "implement", "feature-implement": "implement", "task-review": "implement",
    "feature-archive": "archive", "bug-fixes": "diagnosis",
}
TOKEN_FIELDS = ("input", "cached", "write", "write_5m", "write_1h", "output", "reasoning")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp needs a timezone")
    return parsed.astimezone(timezone.utc)


def utc(value):
    return timestamp(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def seconds(start, end):
    return max(0, (timestamp(end) - timestamp(start)).total_seconds())


def number(data, key, *, required=False):
    value = data.get(key)
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
        raise ValueError(f"Invalid/missing token count: {key}")
    return int(value)


def records(path):
    with path.open(encoding="utf-8") as source:
        for n, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # Writers can be midway through the final line. Interior corruption must be visible.
                if not line.endswith("\n") and not source.read(1):
                    return
                raise ValueError(f"Malformed JSON at line {n}") from None
            if not isinstance(row, dict):
                raise ValueError(f"Non-object record at line {n}")
            yield row


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def attribution(text):
    """Only explicit workflow labels and invocations; do not guess from arbitrary prose."""
    found = {}
    label = re.search(r"\b([a-z0-9]+(?:-[a-z0-9]+)*)--(impl|review|brief|diag|gate)(?:-task-(\d+)|-(global|[^\s:]+))?", text)
    if label:
        found.update(feature=label[1], role={"impl": "implementer", "review": "reviewer", "brief": "brief-writer",
                                            "diag": "diagnostician", "gate": "gate"}[label[2]],
                     task=int(label[3]) if label[3] else None, attribution="label")
        if label[4] == "global":
            found["role"] = "global-review"
    skill = re.search(r"(?:/|\$|<command-name>/)(spec-specify|spec-plan|spec-tasks|task-implement|feature-implement|task-review|feature-archive|bug-fixes)\b", text)
    if skill:
        found.update(stage=STAGES[skill[1]], skill=skill[1])
    return found


def metadata(path, provider):
    """Inspect only enough metadata to filter project scope before reading a whole transcript."""
    for r in records(path):
        if provider == "codex" and r.get("type") == "session_meta":
            m = r.get("payload") or {}
            source = m.get("source") or {}
            spawn = (source.get("subagent") or {}).get("thread_spawn") or {} if isinstance(source, dict) else {}
            return {"cwd": m.get("cwd"), "id": m.get("id"),
                    "parent": m.get("parent_thread_id") or spawn.get("parent_thread_id"),
                    "forked_from": m.get("forked_from_id"), "start": m.get("timestamp") or r.get("timestamp"),
                    "cli_version": m.get("cli_version"), "source": source}
        if provider == "claude" and r.get("cwd"):
            sub = path.parent.name == "subagents"
            session = r.get("sessionId") or (path.parent.parent.name if sub else path.stem)
            agent = path.stem.removeprefix("agent-") if sub else None
            return {"cwd": r["cwd"], "id": f"{session}/{agent}" if sub else session,
                    "parent": session if sub else None, "cli_version": r.get("version")}
    return {}


def parse(path: Path, provider: str):
    meta = metadata(path, provider)
    if not meta.get("id"):
        raise ValueError("Missing session identity")
    run = {"id": f"{provider}:{meta['id']}", "provider": provider, "cwd": meta.get("cwd"),
           "parent": f"{provider}:{meta['parent']}" if meta.get("parent") else None,
           "cli_version": meta.get("cli_version"), "version": VERSION, "first_edit_ts": None,
           "requests_before_first_edit": None}
    ctx = {}
    if provider == "claude":
        sidecar = path.with_suffix(".meta.json")
        if sidecar.exists():
            agent = json.loads(sidecar.read_text())
            ctx.update(attribution(str(agent.get("description") or agent.get("name") or "")))
            run["agent_type"] = agent.get("agentType")
    elif isinstance(meta.get("source"), dict):
        run["agent_type"] = (meta["source"].get("subagent") or {}).get("other")
    by_id = {}
    model = "unknown"
    effort = None
    speed = None
    turn = 0
    turn_id = None
    spans = {}
    seen_totals = set()
    previous_total = None
    native_turn = None
    spans_closed = False
    for r in records(path):
        ts = r.get("timestamp")
        if ts:
            ts = utc(ts)
        p = r.get("payload") or {}
        message = r.get("message") or {}
        is_user = r.get("type") == "user" if provider == "claude" else (r.get("type") == "response_item" and p.get("role") == "user")
        text = text_content(message.get("content") if provider == "claude" else p.get("content"))
        if is_user:
            ctx.update(attribution(text))
            # Claude uses user records for tool results too; those are not resumed work.
            content = message.get("content") if provider == "claude" else p.get("content")
            tool_result = isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
            if by_id and not tool_result and (spans_closed or (provider == "claude" and
                    ((r.get("origin") or {}).get("kind") == "coordinator" or text.lstrip().startswith("<teammate-message")))):
                turn += 1
                spans_closed = False
                native_turn = None
        if provider == "codex" and ((r.get("type") == "event_msg" and p.get("type") == "task_started") or r.get("type") == "turn_context"):
            if by_id and (spans_closed or (p.get("turn_id") and native_turn and p["turn_id"] != native_turn)):
                turn += 1
            spans_closed = False
            native_turn = p.get("turn_id") or native_turn
            turn_id = native_turn
        if provider == "codex" and r.get("type") == "turn_context":
            model = p.get("model") or "unknown"
            effort = p.get("effort") or p.get("reasoning_effort")
            speed = p.get("service_tier") or p.get("speed")
        if ts:
            run.setdefault("start", ts)
            run["end"] = ts
            if not spans_closed:
                spans.setdefault(turn, [ts, ts])[1] = ts
        blocks = message.get("content") or [] if provider == "claude" else [p]
        if not isinstance(blocks, list):
            blocks = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            name = str(b.get("name", ""))
            if name in {"Edit", "Write", "NotebookEdit", "apply_patch", "functions.apply_patch"} and not run["first_edit_ts"]:
                run["first_edit_ts"] = ts
                run["requests_before_first_edit"] = len(by_id)
            if name == "Skill":
                args = b.get("input") or {}
                skill = args.get("skill")
                if skill in STAGES:
                    ctx = {"stage": STAGES[skill], "skill": skill}
                    slug = str(args.get("args", "")).split()
                    if slug and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", slug[0]):
                        ctx.update(feature=slug[0], attribution="skill-args")
        if provider == "claude":
            usage = message.get("usage") if r.get("type") == "assistant" else None
            if not usage:
                continue
            model = message.get("model") or "unknown"
            if model == "<synthetic>":
                continue
            key = r.get("requestId") or message.get("id") or r.get("uuid")
            if not key:
                raise ValueError("Usage record has no request identity")
            key = f"claude:{key}"
            split = usage.get("cache_creation") or {}
            tokens = {"input": number(usage, "input_tokens", required=True),
                      "cached": number(usage, "cache_read_input_tokens") or 0,
                      "write": number(usage, "cache_creation_input_tokens") or 0,
                      "write_5m": number(split, "ephemeral_5m_input_tokens"),
                      "write_1h": number(split, "ephemeral_1h_input_tokens"),
                      "output": number(usage, "output_tokens", required=True),
                      "reasoning": number(usage.get("output_tokens_details") or {}, "thinking_tokens")}
            effort = r.get("effort") or effort
            speed = usage.get("speed") or usage.get("service_tier")
            region = usage.get("inference_geo") or usage.get("region")
            context = tokens["input"] + tokens["cached"] + tokens["write"]
            if message.get("stop_reason") == "end_turn":
                spans_closed = True
        else:
            if r.get("type") == "event_msg" and p.get("type") in {"task_complete", "turn_complete", "turn_aborted"}:
                spans_closed = True
            if r.get("type") != "event_msg" or p.get("type") != "token_count":
                continue
            info = p.get("info") or {}
            usage = info.get("last_token_usage")
            if not usage:
                continue
            total = info.get("total_token_usage")
            total_key = json.dumps(total, sort_keys=True) if total else None
            # Codex repeats the last count in status updates. Cumulative counters identify repeats,
            # but are never summed or differenced (compaction can reset them).
            signature = (turn_id, total_key)
            if total_key and (signature in seen_totals or total_key == previous_total):
                continue
            if total_key:
                seen_totals.add(signature)
                previous_total = total_key
            inp = number(usage, "input_tokens", required=True)
            cached = number(usage, "cached_input_tokens") or 0
            write = number(usage, "cache_write_input_tokens")
            if cached + (write or 0) > inp:
                raise ValueError("Cached/cache-written input exceeds total input")
            tokens = {"input": inp - cached - (write or 0), "cached": cached, "write": write,
                      "write_5m": None, "write_1h": None,
                      "output": number(usage, "output_tokens", required=True),
                      "reasoning": number(usage, "reasoning_output_tokens")}
            context = inp
            region = usage.get("inference_geo") or usage.get("region")
            # Shared prefixes of forked/archived transcripts retain timestamp and counters.
            # Excluding the file/session path keeps that copied usage from becoming new spend.
            identity = [ts, model, turn_id, total or usage]
            key = "codex:" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        if not ts:
            raise ValueError("Usage record has no timestamp")
        if tokens["reasoning"] is not None and tokens["reasoning"] > tokens["output"]:
            raise ValueError("Reasoning exceeds inclusive output count")
        row = {"id": key, "session": run["id"], "provider": provider, "ts": ts, "model": model,
               "effort": effort, "speed": speed, "region": region, "turn": turn,
               "parent": run["parent"], "forked_from": f"{provider}:{meta['forked_from']}" if meta.get("forked_from") else None,
               "session_start": utc(meta.get("start") or run["start"]),
               "actor": "subagent" if run["parent"] else "main",
               "context": context, "context_band": "long" if context > 272000 else "short",
               "tokens": tokens, "version": VERSION, **ctx}
        if key in by_id:
            existing = by_id[key]
            for field, value in tokens.items():
                if value is not None:
                    existing["tokens"][field] = max(existing["tokens"][field] or 0, value)
            existing["context"] = max(existing["context"], context)
        else:
            by_id[key] = row
    run["turns"] = [{"turn": n, "start": times[0], "end": times[1], "seconds": seconds(*times),
                     "requests": sum(r["turn"] == n for r in by_id.values())} for n, times in spans.items()]
    run["active_seconds"] = sum(t["seconds"] for t in run["turns"])
    run["duration_seconds"] = seconds(run["start"], run["end"]) if "start" in run else 0
    run["first_edit_method"] = "explicit-edit-tools-only"
    run["request_count"] = len(by_id)
    return run, list(by_id.values())
