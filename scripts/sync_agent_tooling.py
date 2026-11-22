#!/usr/bin/env python3
"""Keep the shared tooling files of this checkout in step with the reference checkout's.

The reference repository lists the shared files in its manifest, in named lists. This checkout
takes some of those lists and records, in its lock, the hash of each file at the last sync, with
the reference's commit and licence. Run here, with the reference checkout as `--upstream`:

- a file changed there only is pulled, a file changed here only is pushed;
- a file changed on both sides is a conflict: nothing is merged and neither side is overwritten.
  Both changes are shown against the last synced version, for a person to settle;
- a file is copied whole, never expanded from a template, and no directory is swept.

Nothing of this checkout is written upstream but the pushed files themselves: the lock stays here,
and a push refuses a file that holds one of the lock's `private_words`.
"""
import argparse
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

MANIFEST = ".agent-tooling-sync.json"
LOCK = ".agent-tooling-lock.json"
# What a project writes itself: a manifest that lists one of these is refused.
LOCAL_ONLY = {".agents/repository.md", "ai-usage/config.json", "AGENTS.md", "CLAUDE.md", "comprehension.config.json",
              ".claude/settings.json", ".claude/settings.local.json", MANIFEST, LOCK}
LOCAL_FOLDERS = (".claude/agents", ".codex/agents", "ai-usage/.local")
NOTICE = ("The files under \"hashes\" are copied from the repository named in \"upstream\", at the commit named in "
          "\"commit\", where they are published under the licence named in \"licence\" (the LICENSE file of that "
          "repository). A file edited here differs from that commit until the next sync.")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def checked(rel, roots):
    """The path of a manifest entry, refused when it could reach outside the shared files."""
    path = Path(rel)
    if (not path.parts or path.is_absolute() or ".." in path.parts or path.as_posix() in LOCAL_ONLY
            or path.parts[0] in {".git", ".env", ".env.local"} or any(path.is_relative_to(folder) for folder in LOCAL_FOLDERS)):
        raise ValueError(f"Invalid shared path: {rel}")
    # Never copy through a symlink into a private or unlisted place of either checkout.
    for root in roots:
        cursor = root
        for part in path.parts:
            cursor /= part
            if cursor.is_symlink():
                raise ValueError(f"Symlinked path: {rel}")
    return path


def naming(here, files, words):
    """`file:line` for each line of `files` that holds one of `words`, whatever its case."""
    found = []
    for rel in files:
        for number, line in enumerate((here / rel).read_text(errors="replace").splitlines(), 1):
            if any(word.lower() in line.lower() for word in words):
                found.append(f"{rel}:{number}")
    return found


def shown(rel, upstream, here, commit, was):
    """A conflict as two diffs against the last synced version, read in the upstream checkout at the locked commit."""
    def lines(text):
        return text.splitlines(keepends=True)

    def diff(old, new, a, b):
        return "".join(difflib.unified_diff(lines(old), lines(new), a, b)) or "  (the same text)\n"

    mine, theirs = (here / rel).read_text(errors="replace"), (upstream / rel).read_text(errors="replace")
    base = git(upstream, "show", f"{commit}:{rel}") if commit else None
    if base is None or hashlib.sha256(base.encode()).hexdigest() != was:
        return f"CONFLICT {rel}: no last synced version to compare with; upstream against here:\n" + diff(theirs, mine, "upstream", "here")
    return (f"CONFLICT {rel}: since the last sync ({commit[:10]}), here:\n" + diff(base, mine, "last sync", "here")
            + "and upstream:\n" + diff(base, theirs, "last sync", "upstream"))


def sync(upstream, here, *, lists=None, check=False, settle=None, retire=False):
    upstream, here = upstream.resolve(), here.resolve()
    if upstream == here:
        raise ValueError("The upstream checkout and this one must be distinct")
    manifest = json.loads((upstream / MANIFEST).read_text())
    if not isinstance(manifest.get("lists"), dict):
        raise ValueError(f"{MANIFEST} of the upstream checkout has no \"lists\": is it the reference checkout?")
    lock_path = here / LOCK
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    taken = list(lists or lock.get("lists") or [])
    if not taken:
        raise ValueError("Name the lists this checkout takes with --lists; upstream has: " + ", ".join(manifest["lists"]))
    unknown = [name for name in taken if name not in manifest["lists"]]
    if unknown:
        raise ValueError("No such list upstream: " + ", ".join(unknown))
    listed = [rel for paths in manifest["lists"].values() for rel in paths]
    if len(listed) != len(set(listed)):
        raise ValueError("Duplicate manifest entry: " + ", ".join(sorted({rel for rel in listed if listed.count(rel) > 1})))
    files = [rel for name in taken for rel in manifest["lists"][name]]
    for rel in files:
        checked(rel, (upstream, here))

    base = lock.get("hashes", {})
    pulls, pushes, conflicts = [], [], []
    for rel in files:
        up, down, was = digest(upstream / rel), digest(here / rel), base.get(rel)
        if up is None and (down is None or was is not None):
            raise ValueError(f"Listed upstream and absent there: {rel}")
        if down is None and was is not None:
            raise ValueError(f"Deleted here: {rel}; restore it, or take it off the upstream manifest and retire it")
        if up == down:
            continue
        if down == was:
            pulls.append(rel)
        elif up == was:
            pushes.append(rel)
        elif settle:
            (pushes if settle == "here" else pulls).append(rel)
        else:
            conflicts.append(rel)
    gone = sorted(set(base) - set(files))
    named = naming(here, pushes, lock.get("private_words", []))

    if check:
        for label, rels in (("PULL", pulls), ("PUSH", pushes), ("CONFLICT", conflicts), ("NO LONGER SHARED", gone), ("NAMES A PRIVATE WORD", named)):
            for rel in rels:
                print(f"{label} {rel}")
        return 1 if pulls or pushes or conflicts or gone else 0
    if named:
        raise ValueError("A file to push holds a private word of the lock: " + ", ".join(named))
    if gone and not retire:
        raise ValueError("No longer listed upstream; --retire drops them from the lock and leaves the files here: " + ", ".join(gone))
    if conflicts:
        for rel in conflicts:
            print(shown(rel, upstream, here, lock.get("commit"), base.get(rel)))
        raise ValueError("Changed on both sides since the last sync; edit one side to settle, or after reading both "
                         "pass --settle here or --settle upstream for all of them: " + ", ".join(conflicts))

    for sources, source, target in ((pulls, upstream, here), (pushes, here, upstream)):
        for rel in sources:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_bytes((source / rel).read_bytes())

    # The commit is the one that holds every shared file as it was synced: not recorded while upstream has any uncommitted.
    head = (git(upstream, "rev-parse", "HEAD") or "").strip() or None
    dirty = git(upstream, "status", "--porcelain", "--", MANIFEST, *files)
    commit = head if head and dirty == "" else lock.get("commit")
    lock_path.write_text(json.dumps({
        "upstream": manifest.get("repository"),
        "commit": commit,
        "licence": manifest.get("licence"),
        "notice": NOTICE,
        "lists": taken,
        "private_words": lock.get("private_words", []),
        "hashes": {rel: digest(here / rel) for rel in files},
    }, indent=2) + "\n")
    print(f"Pulled {len(pulls)}, pushed {len(pushes)}; {len(files) - len(pulls) - len(pushes)} already the same.")
    if dirty:
        print("Upstream has uncommitted shared files: commit them there, then run this again to record that commit in the lock.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--upstream", type=Path, required=True, help="the reference checkout, which holds the manifest")
    parser.add_argument("--here", type=Path, default=Path(__file__).resolve().parents[1], help="this checkout (default: the one this script is in)")
    parser.add_argument("--lists", nargs="+", help="the manifest's lists this checkout takes; needed once, then read from the lock")
    parser.add_argument("--check", action="store_true", help="say what a sync would do and write nothing")
    parser.add_argument("--settle", choices=("here", "upstream"), help="after reading every conflict: the side that wins them all")
    parser.add_argument("--retire", action="store_true", help="drop from the lock the files upstream no longer lists; they stay here")
    args = parser.parse_args()
    try:
        return sync(args.upstream, args.here, lists=args.lists, check=args.check, settle=args.settle, retire=args.retire)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"sync: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
