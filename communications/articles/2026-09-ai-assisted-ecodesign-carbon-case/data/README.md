# Codex token usage data

`codex-token-usage-2026-09.csv` contains daily token usage reconstructed from locally retained Codex session logs. Dates use the `Europe/Paris` timezone. The precise extraction cutoff and covered period are recorded in `codex-token-usage-2026-09.metadata.json`.

## Refreshing the extract

Run the dependency-free Python extractor from this directory:

```bash
python3 extract_codex_token_usage.py
```

During September 2026 it extracts September 1 through the current day. After September it extracts the complete month. It rewrites both the CSV and its metadata file. A different inclusive range, timezone, output path or Codex data directory can be supplied explicitly:

```bash
python3 extract_codex_token_usage.py \
  --start 2026-09-01 \
  --end 2026-09-30 \
  --timezone Europe/Paris \
  --output codex-token-usage-2026-09.csv
```

## Columns

- `date`: local calendar date.
- `model`: model recorded in the session's turn context.
- `input_tokens`: all input tokens processed, including cached input.
- `cached_input_tokens`: the subset of input tokens served from cache.
- `output_tokens`: all output tokens, including reasoning output.

Every date-model combination is present. Zeroes mean that the local logs contain no recorded usage for that combination; they are not missing values.

## Provenance and method

The source files are the JSONL rollouts under `~/.codex/sessions/` and `~/.codex/archived_sessions/`. Each `token_count` event's `last_token_usage` values were assigned to the most recent model declared by its session's `turn_context`, then summed by local date and model. The cumulative `total_token_usage` counters were not summed, which avoids double-counting.

This is a local activity reconstruction, not an OpenAI invoice or a direct measure of ChatGPT subscription quota consumption. It excludes sessions that were deleted or never synchronized to this machine, and it may not cover provider-side activity absent from the local rollouts. Cached input is reported separately because it generally has different computational and billing implications from uncached input; uncached input can be derived as `input_tokens - cached_input_tokens`.

OpenAI's public Codex documentation does not currently promise a retention duration for these local rollout files. Treat them as working application data: archive reproducible extracts in the repository before deleting Codex tasks, clearing application data, uninstalling, or manually cleaning `~/.codex`.
