"""Revalue raw facts with a dated rate card; incomplete prices never become zero."""
import re


def price(row, card, surface):
    model = re.sub(r"\[[^]]*\]$", "", row["model"])
    model = re.sub(r"-\d{8}$", "", model)
    rate = card["models"].get(model)
    if not rate:
        return None, "unknown model"
    t = row["tokens"]
    if row.get("region") not in (None, "global", "not_available"):
        return None, "regional pricing unavailable"
    speed = row.get("speed")
    if speed not in (None, "standard", "default", "fast", "priority", "batch", "flex"):
        return None, "unknown processing mode"
    fast = speed in ("fast", "priority")
    if surface == "credits":
        if row["provider"] != "codex" or "credits_input" not in rate:
            return None, "no Codex credit rate"
        if speed in ("batch", "flex"):
            return None, "no Codex credit rate for processing mode"
        if fast and "credits_fast_multiplier" not in rate:
            return None, "no verified fast-mode credit rate"
        # Codex has no separate cache-write charge. Input includes cache writes at normal input rate.
        value = ((t["input"] + (t["write"] or 0)) * rate["credits_input"] +
                 t["cached"] * rate["credits_cached"] + t["output"] * rate["credits_output"])
        return value * (rate["credits_fast_multiplier"] if fast else 1) / 1_000_000, None
    if row["provider"] == "codex" and t["write"] is None:
        return None, "cache-write count unavailable for API equivalent"
    if fast and "fast_multiplier" not in rate:
        return None, "no verified fast-mode rate"
    long = row["provider"] == "codex" and row["context_band"] == "long"
    write = t["write"] or 0
    hour = t.get("write_1h") or 0
    if hour > write:
        return None, "inconsistent cache-write split"
    if row["provider"] == "claude" and write and t.get("write_1h") is None:
        return None, "cache-write TTL unavailable"
    value = ((t["input"] * rate["input"] + t["cached"] * rate["cached"] +
              (write - hour) * rate["write"] + hour * rate.get("write_1h", rate["write"])) * (2 if long else 1) +
             t["output"] * rate["output"] * (1.5 if long else 1))
    multiplier = rate["fast_multiplier"] if fast else 0.5 if speed in ("batch", "flex") else 1
    return value * multiplier / 1_000_000, None
