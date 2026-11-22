"""Tests of sync_agent_tooling.py, on checkouts built in a temporary folder.

Run with `python3 scripts/test_sync_agent_tooling.py`.
"""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sync_agent_tooling", Path(__file__).with_name("sync_agent_tooling.py"))
tooling = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tooling)


class SyncTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.upstream, self.here = self.root / "upstream", self.root / "here"
        self.upstream.mkdir()
        self.here.mkdir()
        self.manifest({"core": ["shared.md"]})
        (self.upstream / "shared.md").write_text("one\n")

    def manifest(self, lists):
        (self.upstream / tooling.MANIFEST).write_text(json.dumps({"repository": "https://example.org/reference", "licence": "Apache-2.0", "lists": lists}))

    def lock(self):
        return json.loads((self.here / tooling.LOCK).read_text())

    def run_sync(self, **options):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = tooling.sync(self.upstream, self.here, **options)
        return code, printed.getvalue()

    def commit_upstream(self):
        def git(*args):
            subprocess.run(["git", "-C", str(self.upstream), "-c", "user.name=t", "-c", "user.email=t@example.org", *args], check=True, capture_output=True)
        if not (self.upstream / ".git").exists():
            git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "sync")
        return subprocess.run(["git", "-C", str(self.upstream), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

    def test_the_lists_are_named_once_then_read_from_the_lock(self):
        with self.assertRaisesRegex(ValueError, "--lists; upstream has: core"):
            self.run_sync()
        with self.assertRaisesRegex(ValueError, "No such list upstream: python"):
            self.run_sync(lists=["python"])
        self.assertEqual(self.run_sync(lists=["core"])[0], 0)
        self.assertEqual((self.here / "shared.md").read_text(), "one\n")
        self.assertEqual(self.lock()["lists"], ["core"])
        self.assertEqual(self.run_sync(check=True), (0, ""))

    def test_only_the_lists_taken_are_copied(self):
        self.manifest({"core": ["shared.md"], "other-stack": ["stack.py"]})
        (self.upstream / "stack.py").write_text("stack\n")
        self.run_sync(lists=["core"])
        self.assertFalse((self.here / "stack.py").exists())
        self.assertEqual(list(self.lock()["hashes"]), ["shared.md"])

    def test_a_change_on_one_side_goes_to_the_other(self):
        self.run_sync(lists=["core"])
        (self.upstream / "shared.md").write_text("two\n")
        self.assertEqual(self.run_sync(check=True), (1, "PULL shared.md\n"))
        self.assertEqual((self.here / "shared.md").read_text(), "one\n")
        self.run_sync()
        self.assertEqual((self.here / "shared.md").read_text(), "two\n")
        (self.here / "shared.md").write_text("three\n")
        self.assertEqual(self.run_sync(check=True), (1, "PUSH shared.md\n"))
        self.run_sync()
        self.assertEqual((self.upstream / "shared.md").read_text(), "three\n")
        self.assertEqual(self.run_sync(check=True), (0, ""))

    def test_a_new_file_listed_upstream_is_pushed_from_here(self):
        self.run_sync(lists=["core"])
        self.manifest({"core": ["shared.md", "tools/new.md"]})
        with self.assertRaisesRegex(ValueError, "absent there: tools/new.md"):
            self.run_sync()
        (self.here / "tools").mkdir()
        (self.here / "tools/new.md").write_text("new\n")
        self.run_sync()
        self.assertEqual((self.upstream / "tools/new.md").read_text(), "new\n")

    def test_a_change_on_both_sides_is_shown_and_overwrites_neither(self):
        self.run_sync(lists=["core"])
        self.commit_upstream()
        self.run_sync()
        (self.upstream / "shared.md").write_text("one\ntheirs\n")
        (self.here / "shared.md").write_text("one\nmine\n")
        self.assertEqual(self.run_sync(check=True), (1, "CONFLICT shared.md\n"))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), self.assertRaisesRegex(ValueError, "both sides.*shared.md"):
            tooling.sync(self.upstream, self.here)
        self.assertIn("+mine", printed.getvalue())
        self.assertIn("+theirs", printed.getvalue())
        self.assertEqual((self.upstream / "shared.md").read_text(), "one\ntheirs\n")
        self.assertEqual((self.here / "shared.md").read_text(), "one\nmine\n")
        self.run_sync(settle="here")
        self.assertEqual((self.upstream / "shared.md").read_text(), "one\nmine\n")

    def test_a_first_sync_of_two_different_copies_is_a_conflict_shown_as_one_diff(self):
        (self.here / "shared.md").write_text("mine\n")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), self.assertRaises(ValueError):
            tooling.sync(self.upstream, self.here, lists=["core"])
        self.assertIn("no last synced version", printed.getvalue())
        self.run_sync(lists=["core"], settle="upstream")
        self.assertEqual((self.here / "shared.md").read_text(), "one\n")

    def test_the_lock_names_the_source_and_the_commit_that_holds_what_was_synced(self):
        first = self.commit_upstream()
        self.run_sync(lists=["core"])
        lock = self.lock()
        self.assertEqual((lock["upstream"], lock["licence"], lock["commit"]), ("https://example.org/reference", "Apache-2.0", first))
        self.assertIn("LICENSE", lock["notice"])
        (self.here / "shared.md").write_text("two\n")
        code, printed = self.run_sync()
        self.assertIn("uncommitted shared files", printed)
        self.assertEqual(self.lock()["commit"], first)
        second = self.commit_upstream()
        self.run_sync()
        self.assertEqual(self.lock()["commit"], second)

    def test_a_push_refuses_a_file_that_holds_a_private_word(self):
        self.run_sync(lists=["core"])
        lock = self.lock()
        lock["private_words"] = ["Secretproject"]
        (self.here / tooling.LOCK).write_text(json.dumps(lock))
        (self.here / "shared.md").write_text("one\nas in secretproject\n")
        self.assertEqual(self.run_sync(check=True), (1, "PUSH shared.md\nNAMES A PRIVATE WORD shared.md:2\n"))
        with self.assertRaisesRegex(ValueError, "private word.*shared.md:2"):
            self.run_sync()
        self.assertEqual((self.upstream / "shared.md").read_text(), "one\n")
        self.assertEqual(self.lock()["private_words"], ["Secretproject"])

    def test_a_file_upstream_no_longer_lists_stays_here_once_retired(self):
        self.manifest({"core": ["shared.md", "old.md"]})
        (self.upstream / "old.md").write_text("old\n")
        self.run_sync(lists=["core"])
        self.manifest({"core": ["shared.md"]})
        self.assertEqual(self.run_sync(check=True), (1, "NO LONGER SHARED old.md\n"))
        with self.assertRaisesRegex(ValueError, "--retire.*old.md"):
            self.run_sync()
        self.run_sync(retire=True)
        self.assertEqual((self.here / "old.md").read_text(), "old\n")
        self.assertEqual(list(self.lock()["hashes"]), ["shared.md"])

    def test_a_shared_file_deleted_here_is_not_deleted_upstream(self):
        self.run_sync(lists=["core"])
        (self.here / "shared.md").unlink()
        with self.assertRaisesRegex(ValueError, "Deleted here: shared.md"):
            self.run_sync()
        self.assertTrue((self.upstream / "shared.md").exists())

    def test_what_a_project_writes_itself_cannot_be_listed(self):
        for local in (".agents/repository.md", "ai-usage/config.json", "ai-usage/.local/ledger.sqlite3", "AGENTS.md", "comprehension.config.json",
                      ".claude/settings.json", ".claude/settings.local.json", ".claude/agents/reviewer.md", ".codex/agents/reviewer.toml",
                      tooling.LOCK, "../outside.md", ".git/config"):
            self.manifest({"core": [local]})
            with self.assertRaisesRegex(ValueError, "Invalid shared path"):
                self.run_sync(lists=["core"])
        self.manifest({"core": ["shared.md"], "other": ["shared.md"]})
        with self.assertRaisesRegex(ValueError, "Duplicate manifest entry: shared.md"):
            self.run_sync(lists=["core"])

    def test_nothing_is_copied_through_a_symlink(self):
        outside = self.root / "outside"
        outside.write_text("safe")
        (self.here / "shared.md").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlinked path"):
            self.run_sync(lists=["core"], settle="upstream")
        self.assertEqual(outside.read_text(), "safe")
        private = self.root / "private"
        private.mkdir()
        (private / "data.md").write_text("private")
        (self.upstream / "linked").symlink_to(private)
        self.manifest({"core": ["linked/data.md"]})
        with self.assertRaisesRegex(ValueError, "Symlinked path"):
            self.run_sync(lists=["core"])
        self.assertFalse((self.here / "linked").exists())

    def test_the_reference_checkout_is_the_one_with_the_lists(self):
        (self.upstream / tooling.MANIFEST).write_text(json.dumps({"files": ["shared.md"]}))
        with self.assertRaisesRegex(ValueError, "no \"lists\""):
            self.run_sync(lists=["core"])


if __name__ == "__main__":
    unittest.main()
