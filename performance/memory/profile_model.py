"""Run one model-engine scenario in a fresh process and emit a machine-readable result."""

import argparse
import gc
import json
import os
from pathlib import Path
import threading
import time

import psutil

from efootprint.abstract_modeling_classes.reactive_core import observe_computations
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.system import System
from performance.memory.inspection import materialized_state
from performance.memory.scenarios import EDGE_PATTERN_SCENARIOS, SCENARIOS, prepare_scenario, run_scenario
from performance.memory.topology import TopologyConfig, build_synthetic_topology


class MemorySampler:
    """Sample process memory and Linux cgroup memory when each surface is available."""

    def __init__(self, interval_seconds: float = 0.005):
        self.process = psutil.Process()
        self.interval_seconds = interval_seconds
        self.stage = "startup"
        self.stage_peaks = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join()

    def begin(self, stage: str):
        with self._lock:
            self.stage = stage
        self.sample()

    def sample(self) -> dict[str, float | None]:
        with self._lock:
            try:
                info = self.process.memory_full_info()
            except (psutil.AccessDenied, PermissionError):
                info = self.process.memory_info()
            values = {
                "rss_mb": info.rss / 2**20,
                "pss_mb": getattr(info, "pss", None),
                "uss_mb": getattr(info, "uss", None),
                "cgroup_current_mb": _read_cgroup_mb("memory.current"),
                "cgroup_peak_mb": _read_cgroup_mb("memory.peak"),
            }
            for name in ("pss_mb", "uss_mb"):
                if values[name] is not None:
                    values[name] /= 2**20
            peak = self.stage_peaks.setdefault(self.stage, {})
            for name, value in values.items():
                if value is not None:
                    peak[name] = max(value, peak.get(name, value))
        return values

    def _run(self):
        while not self._stop.wait(self.interval_seconds):
            try:
                self.sample()
            except (psutil.Error, OSError):
                continue


def _read_cgroup_mb(filename: str) -> float | None:
    for root in (Path("/sys/fs/cgroup"), Path("/sys/fs/cgroup/memory")):
        path = root / filename
        if path.exists():
            value = path.read_text().strip()
            if value != "max":
                return int(value) / 2**20
    return None


def _load_payload(args) -> tuple[dict, dict]:
    if args.model is not None:
        return json.loads(args.model.read_text()), {"source": str(args.model)}
    config = TopologyConfig(
        modeled_hours=args.modeled_hours,
        pattern_count=args.pattern_count,
        journeys_per_pattern=args.journeys_per_pattern,
        shared_children=args.shared_children == "shared",
    )
    topology = build_synthetic_topology(config)
    payload = system_to_json(topology.system, save_computed_state=False)
    dimensions = {
        "source": "synthetic",
        "modeled_hours": config.modeled_hours,
        "web_pattern_count": config.pattern_count,
        "edge_pattern_count": config.pattern_count,
        "journeys_per_pattern": config.journeys_per_pattern,
        "shared_children": config.shared_children,
    }
    del topology
    gc.collect()
    return payload, dimensions


def _hydrate(payload: dict) -> System:
    class_objects, _, _ = json_to_system(payload)
    return next(iter(class_objects["System"].values()))


def _system_dimensions(system: System) -> dict:
    web_patterns = tuple(system.usage_patterns)
    edge_patterns = tuple(system.edge_usage_patterns)
    hourly_inputs = [pattern.hourly_occurrences for pattern in web_patterns]
    hourly_inputs += [pattern.hourly_deployment_starts for pattern in edge_patterns]
    return {
        "modeled_hours": max((len(values) for values in hourly_inputs), default=0),
        "web_pattern_count": len(web_patterns),
        "edge_pattern_count": len(edge_patterns),
        "web_journeys_per_pattern": [len(pattern.usage_journeys) for pattern in web_patterns],
        "edge_journeys_per_pattern": [len(pattern.edge_usage_journeys) for pattern in edge_patterns],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--modeled-hours", type=int, default=168)
    parser.add_argument("--pattern-count", type=int, default=2)
    parser.add_argument("--journeys-per-pattern", type=int, default=3)
    parser.add_argument("--shared-children", choices=("shared", "distinct"), default="shared")
    parser.add_argument("--retained-results", type=int, default=5)
    args = parser.parse_args()

    sampler = MemorySampler()
    sampler.start()
    payload, dimensions = _load_payload(args)
    sampler.begin("hydration")
    hydration_started_at = time.perf_counter()
    hydration_callbacks = 0

    def count_hydration(_slot):
        nonlocal hydration_callbacks
        hydration_callbacks += 1

    with observe_computations(count_hydration):
        system = _hydrate(payload)
    hydration_seconds = time.perf_counter() - hydration_started_at
    dimensions.update(_system_dimensions(system))
    if args.scenario in EDGE_PATTERN_SCENARIOS and not system.edge_usage_patterns:
        parser.error(
            f"scenario '{args.scenario}' requires a model with at least one edge usage pattern; "
            "direct attribution targets the first edge usage pattern"
        )

    sampler.begin("priming")
    prepare_scenario(system, args.scenario)
    sampler.begin("calculation")
    calculation_started_at = time.perf_counter()
    calculation_callbacks = 0

    def count_calculation(_slot):
        nonlocal calculation_callbacks
        calculation_callbacks += 1

    with observe_computations(count_calculation):
        scenario_result = run_scenario(system, args.scenario, args.retained_results)
    calculation_seconds = time.perf_counter() - calculation_started_at
    retained_result_count = len(scenario_result.retained)
    period_sum_kg = scenario_result.period_sum_kg
    retained = sampler.sample()
    cache_state = materialized_state(system)
    gc.collect()
    post_gc_retained = sampler.sample()
    sampler.begin("release")
    del scenario_result, system, payload
    gc.collect()
    post_release = sampler.sample()
    sampler.stop()

    result = {
        "scenario": args.scenario,
        "dimensions": dimensions,
        "pid": os.getpid(),
        "hydration_seconds": hydration_seconds,
        "calculation_seconds": calculation_seconds,
        "hydration_callback_count": hydration_callbacks,
        "calculation_callback_count": calculation_callbacks,
        "retained_result_count": retained_result_count,
        "period_sum_kg": period_sum_kg,
        "cache_state": cache_state,
        "retained_memory": retained,
        "post_gc_retained_memory": post_gc_retained,
        "post_release_memory": post_release,
        "stage_peaks": sampler.stage_peaks,
    }
    print("RESULT " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
