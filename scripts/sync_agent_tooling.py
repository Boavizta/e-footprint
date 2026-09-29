#!/usr/bin/env python3
"""Copy explicit shared tooling files from e-footprint; protect local variants and detect drift."""
import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = ".agent-tooling-sync.json"
LOCAL_ONLY = {".agents/repository.md", "ai-usage/config.json", "AGENTS.md", "CLAUDE.md", ".claude/settings.local.json"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def sync(source, target, *, check=False, accept_target=False):
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise ValueError("Source and target must be distinct repositories")
    manifest = json.loads((source / MANIFEST).read_text())
    baseline_path = target / MANIFEST
    baseline = json.loads(baseline_path.read_text()).get("hashes", {}) if baseline_path.exists() else {}
    files = manifest["files"]
    if len(files) != len(set(files)):
        raise ValueError("Duplicate manifest entry")
    for rel in files:
        path = Path(rel)
        if (not path.parts or path.is_absolute() or ".." in path.parts or rel in LOCAL_ONLY or path.as_posix() == MANIFEST
                or path.parts[0] in {".git", ".env", ".env.local"} or path.is_relative_to("ai-usage/.local")):
            raise ValueError(f"Invalid shared path: {rel}")
        if not (source / path).is_file() or (source / path).is_symlink():
            raise ValueError(f"Missing or symlinked source: {rel}")
        # Do not copy through symlinks into private/unlisted locations in either checkout.
        for root in (source, target):
            cursor = root
            for part in path.parts:
                cursor /= part
                if cursor.is_symlink():
                    raise ValueError(f"Symlinked path: {rel}")
    current = {rel: digest(source / rel) for rel in files}
    changed = [rel for rel in files if digest(target / rel) != current[rel]]
    conflicts = [rel for rel in changed if (target / rel).exists() and digest(target / rel) != baseline.get(rel)]
    removed = sorted(set(baseline) - set(files))
    manifest_changed = not baseline_path.exists() or json.loads(baseline_path.read_text()) != {**manifest, "hashes": current}
    if check:
        for rel in changed:
            print(f"DIFF {rel}")
        if removed:
            print("Previously managed paths require explicit retirement: " + ", ".join(removed))
        if manifest_changed:
            print(f"DIFF {MANIFEST}")
        return 1 if changed or removed or manifest_changed else 0
    if removed:
        raise ValueError("Retire removed managed files explicitly before syncing: " + ", ".join(removed))
    if conflicts and not accept_target:
        raise ValueError("Target has unreviewed differences; reconcile them or use --accept-target-overwrite after review: " + ", ".join(conflicts))
    for rel in changed:
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source / rel).read_bytes())
    payload = {**manifest, "hashes": current}
    text = json.dumps(payload, indent=2) + "\n"
    (source / MANIFEST).write_text(text)
    baseline_path.write_text(text)
    print(f"Synchronized {len(changed)} files; preserved local references, settings and unlisted skills.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--accept-target-overwrite", action="store_true", help="Only after reviewing initial/drifted target copies")
    args = parser.parse_args()
    try:
        return sync(args.source, args.target, check=args.check, accept_target=args.accept_target_overwrite)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"sync: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
