"""The three calls where no collector is installed, which is production: they do nothing, and their module
imports nothing but the standard library. Both are held on the reference; a project's copy is held to it."""
import json
import subprocess
import sys
import textwrap

from comprehension_harness.python.tests.conftest import REFERENCE_CALLS, ROOT


def run_python(script: str) -> subprocess.CompletedProcess:
    """A fresh interpreter at the repository root: this process has the collector installed, a server has not."""
    return subprocess.run([sys.executable, "-c", textwrap.dedent(script)], cwd=ROOT, capture_output=True, text=True)


def test_without_a_collector_a_call_returns_nothing_and_its_watch_is_never_called():
    done = run_python("""
        from comprehension_harness.python.narrate import event, narrate, planned, template_call

        def watch():
            raise AssertionError("the watch was called")

        assert narrate("A step.", watch) is None
        assert event("A cause.", watch) is None
        assert planned("gift-cards#deduct-the-card", "A change.", watch) is None
        assert planned.remove("gift-cards#deduct-the-card", "A function that goes.") is None
        assert planned.evidence("gift-cards#deduct-the-card", "A bug shows.", watch, expect={"due": 0}) is None
        assert planned("gift-cards#deduct-the-card", "A change.", watch, expect={"due": 0}) is None
        assert template_call("narrate", "pages/rows.html", 2, "A step.", watch) is None
        assert planned.evidence("gift-cards#deduct-the-card", "A bug shows.", watch, expect=watch) is None
        assert planned.evidence("gift-cards#deduct-the-card", "A bug shows.", watch, distinct="row") is None
        assert planned("gift-cards#deduct-the-card", "A change.", watch, distinct=("row", "of")) is None
    """)

    assert done.returncode == 0, done.stderr


def test_the_calls_import_the_standard_library_alone():
    done = run_python("""
        import sys

        before = set(sys.modules)
        import comprehension_harness.python.narrate
        loaded = set(sys.modules) - before

        print(sorted(name for name in loaded if name.split(".")[0] not in sys.stdlib_module_names))
    """)

    assert done.returncode == 0, done.stderr
    harness = ["comprehension_harness", "comprehension_harness.python", "comprehension_harness.python.narrate"]
    assert done.stdout.strip() == str(harness)


def test_the_calls_of_this_project_are_a_copy_of_the_reference():
    """What the two tests above hold of the reference holds of the file this project's code imports."""
    module = json.loads((ROOT / "comprehension.config.json").read_text())["stack"]["calls"]
    copy = ROOT / f"{module.replace('.', '/')}.py"

    reference, own = REFERENCE_CALLS.relative_to(ROOT), copy.relative_to(ROOT)
    assert copy.read_text() == REFERENCE_CALLS.read_text(), f"{own} is not the reference: cp {reference} {own}"
