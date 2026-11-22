"""The pytest plugin that writes what each test crossed (``comprehension_harness/stack.md`` § 1).

A project loads it for every run: ``pytest_plugins = ["comprehension_harness.python.collector"]`` in the
conftest of its tests. For the lifetime of a run it is the collector of the project's own calls, the module
``stack.calls`` of the configuration names, and of no other project's: a dependency's calls stay inert. Each
``narrate``, ``event`` or ``planned`` call a test crosses is a hit: its sentence, its watch's value, the frame of
the call and the repository's frames above it. A test's hits are its story; a test file's stories are one JSON
array at ``<cache>/stories/<the file, "/" written "__">.json``, deleted when the file's run starts and written
when it ends. A test that crosses no call has no story.

A hit carries no identity: the tools derive ``<file>#<function>#<ordinal>`` from the source index. A frame's
function is its ``__qualname__``, as the index names it; its line and column are where the call expression
starts, as ``ast`` has them.

Under pytest-xdist a file's tests run in several processes: each worker hands its stories to the controller,
which writes the files when the run ends.
"""
import dataclasses
import datetime
import importlib
import itertools
import json
import math
import os
import time
from pathlib import Path

import pytest

CONFIG_FILE = "comprehension.config.json"
# A site keeps its first hits of a test in full and counts the rest: a test that loops over a narrated line
# would otherwise pay a stack and a watch per pass.
MAX_HITS_PER_SITE = 50
KINDS = ("product", "mechanism")
WORKER_OUTPUT = "narrate_stories"


def find_root(start: Path) -> Path:
    """The nearest folder holding the configuration, from ``start`` upwards: the repository root."""
    for folder in (start, *start.parents):
        if (folder / CONFIG_FILE).is_file():
            return folder
    raise pytest.UsageError(f"narrate collector: no {CONFIG_FILE} in {start} or a folder above it")


def plain(value, depth: int = 0):
    """A watch's value as plain JSON."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if depth > 5:
        return "…"
    if isinstance(value, dict):
        return {str(key): plain(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item, depth + 1) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((plain(item, depth + 1) for item in value), key=repr)
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: plain(getattr(value, field.name), depth + 1) for field in dataclasses.fields(value)}
    return str(value)


def title_of(item) -> str:
    """The one title of a test: its ``@titled`` or ``@planned_test`` string, else its function's name, with
    pytest's ``[case]`` after it when the test is parametrized."""
    marker = item.get_closest_marker("titled") or item.get_closest_marker("planned_test")
    name = getattr(item, "originalname", None) or item.name
    return (marker.args[0] if marker else name) + item.name[len(name):]


class StoryRecorder:
    def __init__(self, config):
        self.root = find_root(Path(config.rootpath).resolve())
        settings = json.loads((self.root / CONFIG_FILE).read_text())
        if not isinstance(settings.get("cache"), str):
            raise pytest.UsageError(f'narrate collector: {CONFIG_FILE} — "cache" is not a string')
        self.stories_dir = self.root / settings["cache"] / "stories"
        stack = settings.get("stack")
        if not isinstance(stack, dict) or not isinstance(stack.get("calls"), str):
            raise pytest.UsageError(f'narrate collector: {CONFIG_FILE} — "stack.calls" names the module this '
                                    f'project imports narrate, event and planned from')
        self.calls = importlib.import_module(stack["calls"])
        self.is_worker = hasattr(config, "workerinput")
        self.config = config
        self.own_files = {os.path.realpath(self.calls.__file__), os.path.realpath(__file__)}
        self.relative_paths: dict[str, str | None] = {}
        self.positions: dict[tuple, tuple[int, int]] = {}
        self.order: dict[str, int] = {}
        # The stories of a run, by test file, until they are written.
        self.pending: dict[str, list[dict]] = {}
        self.started: set[str] = set()
        self.current: dict | None = None

    # ── Frames ──────────────────────────────────────────────────────────────────────────────────────

    def relative(self, filename: str) -> str | None:
        """A file of the repository as a path from its root; None for any other, and for this stack's own."""
        if filename not in self.relative_paths:
            path = os.path.realpath(filename)
            # `<frozen runpy>`, `<string>`: code that is no file.
            is_file = not filename.startswith("<")
            inside = is_file and path.startswith(f"{self.root}{os.sep}") and path not in self.own_files
            parts = Path(path).relative_to(self.root).parts if inside else ()
            foreign = any(part.startswith(".") or part in ("node_modules", "site-packages") for part in parts)
            self.relative_paths[filename] = "/".join(parts) if inside and not foreign else None
        return self.relative_paths[filename]

    def position(self, frame) -> tuple[int, int]:
        """Where the expression a frame is running starts: the call, for the frame of a call."""
        key = (frame.f_code, frame.f_lasti)
        if key not in self.positions:
            line, _, column, _ = next(itertools.islice(frame.f_code.co_positions(), frame.f_lasti // 2, None))
            # A code object compiled without positions has the line alone.
            self.positions[key] = (frame.f_lineno, 1) if line is None or column is None else (line, column + 1)
        return self.positions[key]

    def frame(self, frame, file: str) -> dict:
        line, column = self.position(frame)
        code = frame.f_code
        return {"file": file, "line": line, "column": column,
                "fn": None if code.co_name.startswith("<") else code.co_qualname}

    # ── Hits ────────────────────────────────────────────────────────────────────────────────────────

    def collect(self, kind, sentence, watch, frame, planned_as) -> None:
        test = self.current
        if test is None:
            return  # Outside a test (an import, a fixture of the session): nobody's story.
        file = self.relative(frame.f_code.co_filename)
        if file is None:
            raise RuntimeError(f"{kind} call at {frame.f_code.co_filename}:{frame.f_lineno} is outside the "
                               f"repository {self.root}: a site is a file of it")
        site = self.frame(frame, file)
        counted = {"file": file, "line": site["line"], "kept": 0, "omitted": 0}
        tally = test["tallies"].setdefault((file, site["line"]), counted)
        if tally["kept"] >= MAX_HITS_PER_SITE:
            tally["omitted"] += 1
            return
        tally["kept"] += 1
        stack = []
        above = frame.f_back
        while above is not None:
            own = self.relative(above.f_code.co_filename)
            if own is not None:
                stack.append(self.frame(above, own))
            above = above.f_back
        value = None
        if watch is not None:
            try:
                value = plain(watch())
            except Exception as error:  # A watch documents a run and never fails it.
                value = {"error": f"{type(error).__name__}: {error}"}
        hit = {"kind": kind, "sentence": sentence, "watch": value, "site": site, "stack": stack,
               "atMs": round((time.perf_counter() - test["started"]) * 1000, 1)}
        if planned_as is not None:
            hit["planned"] = dict(zip(("feature", "slug", "change"), planned_as))
        test["hits"].append(hit)

    # ── Tests ───────────────────────────────────────────────────────────────────────────────────────

    def test_file(self, item) -> str | None:
        path = os.path.realpath(str(item.path))
        return Path(path).relative_to(self.root).as_posix() if path.startswith(f"{self.root}{os.sep}") else None

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items):
        for index, item in enumerate(items):
            self.order[item.nodeid] = index + 1
            where = f"{item.location[0]}:{(item.location[1] or 0) + 1}"
            for node, mark in item.iter_markers_with_node("narrative"):
                if not isinstance(node, pytest.Class):
                    raise pytest.UsageError(f"{where} — a narrative is declared on a test class: "
                                            f"@narrative(\"…\") above `class Test…`")
                if len(mark.args) != 1 or not isinstance(mark.args[0], str) or mark.kwargs.get("kind") not in KINDS:
                    raise pytest.UsageError(f"{where} — a narrative is declared with declare.py: "
                                            f"@narrative(\"<title>\") or @narrative.mechanism(\"<title>\")")
            if item.get_closest_marker("canonical") and not item.get_closest_marker("narrative"):
                raise pytest.UsageError(f"{where} — @canonical marks the reference case of a narrative, "
                                        f"and this test is in none")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        file = self.test_file(item)
        if file is None:
            yield
            return
        if file not in self.started:
            # A file's run rewrites its stories from nothing: a run that dies leaves none to be read as fresh.
            self.started.add(file)
            self.story_file(file).unlink(missing_ok=True)
        self.current = {"hits": [], "tallies": {}, "started": time.perf_counter(), "reports": []}
        try:
            yield
        finally:
            test, self.current = self.current, None
        if test["hits"]:
            self.pending.setdefault(file, []).append(self.story(item, file, test))
        if not self.is_worker and (nextitem is None or self.test_file(nextitem) != file):
            self.write(file)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        if self.current is not None:
            self.current["reports"].append(outcome.get_result())

    def story(self, item, file: str, test: dict) -> dict:
        reports = test["reports"]
        state = next((r.outcome for r in reports if r.outcome != "passed"), "passed" if reports else None)
        call = next((r for r in reports if r.when == "call"), None)
        narrative = item.get_closest_marker("narrative")
        story = {
            "file": file,
            "test": title_of(item),
            "narrative": {"title": narrative.args[0], "kind": narrative.kwargs["kind"]} if narrative else None,
            "canonical": item.get_closest_marker("canonical") is not None,
            "order": self.order.get(item.nodeid, len(self.order) + 1),
            "state": state,
            "durationMs": None if call is None else round(call.duration * 1000, 1),
            "hits": test["hits"],
        }
        capped = [tally for tally in test["tallies"].values() if tally["omitted"]]
        if capped:
            story["capped"] = capped
        return story

    # ── Story files ─────────────────────────────────────────────────────────────────────────────────

    def story_file(self, file: str) -> Path:
        return self.stories_dir / f"{file.replace('/', '__')}.json"

    def write(self, file: str) -> None:
        stories = self.pending.pop(file, [])
        if not stories:
            return
        target = self.story_file(file)
        # Tests of one file that ran in two stretches of a run are one file's stories.
        earlier = json.loads(target.read_text()) if target.exists() else []
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        merged = sorted(earlier + stories, key=lambda story: story["order"])
        target.write_text(json.dumps(merged, indent=2, ensure_ascii=False))

    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(self, node, error):
        for file, stories in json.loads(getattr(node, "workeroutput", {}).get(WORKER_OUTPUT, "{}")).items():
            self.pending.setdefault(file, []).extend(stories)

    def pytest_sessionfinish(self, session):
        if self.is_worker:
            self.config.workeroutput[WORKER_OUTPUT] = json.dumps(self.pending)
            return
        for file in list(self.pending):
            self.write(file)

    def pytest_unconfigure(self, config):
        self.calls.install_collector(None)


def pytest_configure(config):
    config.addinivalue_line("markers", "narrative(title, kind): the test class tells a narrative (declare.py)")
    config.addinivalue_line("markers", "canonical: the reference case of its narrative (declare.py)")
    config.addinivalue_line("markers", "titled(title): the test's title, when its name cannot hold it (declare.py)")
    config.addinivalue_line("markers", "planned_test(title): a test to write, with an empty body (declare.py)")
    recorder = StoryRecorder(config)
    config.pluginmanager.register(recorder, "narrate-collector")
    recorder.calls.install_collector(recorder.collect)
