import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

script = Path(__file__).resolve().parents[2]/"scripts/sync_agent_tooling.py"
spec = importlib.util.spec_from_file_location("sync_agent_tooling", script)
sync_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_module)


class SyncTests(unittest.TestCase):
    def test_copy_check_conflict_and_local_file_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/"source", Path(folder)/"target"
            source.mkdir(); target.mkdir()
            (source/"shared.md").write_text("one")
            (source/sync_module.MANIFEST).write_text(json.dumps({"files":["shared.md"]}))
            (target/"local.md").write_text("keep")
            self.assertEqual(sync_module.sync(source,target),0)
            self.assertEqual(sync_module.sync(source,target,check=True),0)
            (source/"shared.md").write_text("two")
            self.assertEqual(sync_module.sync(source,target,check=True),1)
            self.assertEqual(sync_module.sync(source,target),0)
            (target/"shared.md").write_text("local change")
            (source/"shared.md").write_text("three")
            with self.assertRaises(ValueError): sync_module.sync(source,target)
            self.assertEqual((target/"shared.md").read_text(),"local change")
            self.assertEqual((target/"local.md").read_text(),"keep")

    def test_symlinks_and_local_config_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            source,target=Path(folder)/"source",Path(folder)/"target"
            source.mkdir();target.mkdir()
            (source/"shared.md").write_text("new")
            (source/sync_module.MANIFEST).write_text(json.dumps({"files":["shared.md"]}))
            other=Path(folder)/"other";other.write_text("safe")
            (target/"shared.md").symlink_to(other)
            with self.assertRaises(ValueError):sync_module.sync(source,target,accept_target=True)
            self.assertEqual(other.read_text(),"safe")
            for local in (".agents/repository.md", "ai-usage/config.json", "ai-usage/.local/ledger.sqlite3", "AGENTS.md", ".claude/settings.local.json"):
                (source/sync_module.MANIFEST).write_text(json.dumps({"files":[local]}))
                with self.assertRaises(ValueError):sync_module.sync(source,target)

    def test_source_parent_symlink_does_not_copy_unlisted_data(self):
        with tempfile.TemporaryDirectory() as folder:
            source,target=Path(folder)/"source",Path(folder)/"target"
            source.mkdir();target.mkdir()
            private=Path(folder)/"private";private.mkdir()
            (private/"data.md").write_text("private")
            (source/"linked").symlink_to(private)
            (source/sync_module.MANIFEST).write_text(json.dumps({"files":["linked/data.md"]}))
            with self.assertRaises(ValueError):sync_module.sync(source,target)
            self.assertFalse((target/"linked").exists())


if __name__ == "__main__":unittest.main()
