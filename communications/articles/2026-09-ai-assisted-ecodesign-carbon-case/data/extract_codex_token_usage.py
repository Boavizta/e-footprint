#!/usr/bin/env python3
"""Aggregate locally retained Codex token events into a daily CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ARTICLE_START = date(2026, 9, 1)
ARTICLE_END = date(2026, 9, 30)
DEFAULT_OUTPUT = Path(__file__).with_name("codex-token-usage-2026-09.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate Codex JSONL token events by local date and model."
    )
    parser.add_argument("--start", type=date.fromisoformat, default=ARTICLE_START)
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        help="Inclusive end date; defaults to today, capped at 2026-09-30.",
    )
    parser.add_argument("--timezone", default="Europe/Paris")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    return parser.parse_args()


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iter_rollouts(codex_home: Path):
    for source in (codex_home / "sessions", codex_home / "archived_sessions"):
        if source.exists():
            yield from sorted(source.rglob("*.jsonl"))


def extract(
    files: list[Path],
    start: date,
    end: date,
    local_timezone: ZoneInfo,
    cutoff: datetime,
):
    usage = defaultdict(lambda: [0, 0, 0])
    models = set()
    event_count = 0

    for rollout in files:
        model = "unknown"
        with rollout.open(encoding="utf-8") as lines:
            for line in lines:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if item.get("type") == "turn_context":
                    model = (item.get("payload") or {}).get("model") or "unknown"
                    continue

                payload = item.get("payload") or {}
                if (
                    item.get("type") != "event_msg"
                    or payload.get("type") != "token_count"
                ):
                    continue

                last_usage = (payload.get("info") or {}).get("last_token_usage")
                timestamp = item.get("timestamp")
                if not last_usage or not timestamp:
                    continue

                event_time = parse_timestamp(timestamp)
                if event_time > cutoff:
                    continue
                local_date = event_time.astimezone(local_timezone).date()
                if not start <= local_date <= end:
                    continue

                values = usage[(local_date, model)]
                values[0] += last_usage.get("input_tokens", 0)
                values[1] += last_usage.get("cached_input_tokens", 0)
                values[2] += last_usage.get("output_tokens", 0)
                models.add(model)
                event_count += 1

    return usage, sorted(models), event_count


def write_csv(
    output: Path,
    usage,
    models: list[str],
    start: date,
    end: date,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(
            ["date", "model", "input_tokens", "cached_input_tokens", "output_tokens"]
        )
        current_date = start
        while current_date <= end:
            for model in models:
                writer.writerow([current_date, model, *usage[(current_date, model)]])
            current_date += timedelta(days=1)


def write_metadata(
    output: Path,
    args: argparse.Namespace,
    start: date,
    end: date,
    cutoff: datetime,
    local_timezone: ZoneInfo,
    files: list[Path],
    event_count: int,
) -> Path:
    metadata_path = output.with_suffix(".metadata.json")
    local_cutoff = cutoff.astimezone(local_timezone)
    metadata = {
        "generated_at_utc": cutoff.isoformat().replace("+00:00", "Z"),
        "generated_at_local": local_cutoff.isoformat(),
        "timezone": args.timezone,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "partial_end_date": end == local_cutoff.date(),
        "codex_home": str(args.codex_home.expanduser()),
        "rollout_files_scanned": len(files),
        "token_events_included": event_count,
        "csv": output.name,
    }
    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)
        metadata_file.write("\n")
    return metadata_path


def main() -> None:
    args = parse_args()
    local_timezone = ZoneInfo(args.timezone)
    cutoff = datetime.now(timezone.utc)
    local_today = cutoff.astimezone(local_timezone).date()
    start = args.start
    end = args.end or min(local_today, ARTICLE_END)
    if end < start:
        raise SystemExit("--end must be on or after --start")

    codex_home = args.codex_home.expanduser()
    files = list(iter_rollouts(codex_home))
    usage, models, event_count = extract(files, start, end, local_timezone, cutoff)
    if not models:
        raise SystemExit("No token events found in the requested date range")

    output = args.output.resolve()
    write_csv(output, usage, models, start, end)
    metadata_path = write_metadata(
        output,
        args,
        start,
        end,
        cutoff,
        local_timezone,
        files,
        event_count,
    )
    print(f"Wrote {output}")
    print(f"Wrote {metadata_path}")


if __name__ == "__main__":
    main()
