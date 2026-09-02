"""Native calculation scenarios used by the memory profiler."""

from dataclasses import dataclass

from efootprint.constants.units import u
from efootprint.core.attribution import attributed_footprint
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System

SCENARIOS = (
    "hydrate",
    "total-footprint",
    "cold-attribution-matrix",
    "warm-attribution-matrix",
    "result-primed-attribution-matrix",
    "attributed-manufacturing",
    "attributed-usage",
    "retained-attributed-results",
)
EDGE_PATTERN_SCENARIOS = frozenset({"attributed-manufacturing", "attributed-usage", "retained-attributed-results"})


@dataclass(frozen=True)
class ScenarioResult:
    retained: tuple
    period_sum_kg: float | None


def prepare_scenario(system: System, scenario: str) -> None:
    """Materialize state that is intentionally warm before the measured operation."""
    if scenario == "warm-attribution-matrix":
        system.impact_repartition_matrix
    elif scenario == "result-primed-attribution-matrix":
        system.total_footprint


def run_scenario(system: System, scenario: str, retained_results: int = 5) -> ScenarioResult:
    """Run one benchmark operation and retain its public result."""
    edge_patterns = tuple(_underlying(pattern) for pattern in system.edge_usage_patterns)
    if scenario == "hydrate":
        return ScenarioResult((), None)
    if scenario == "total-footprint":
        result = system.total_footprint
        return ScenarioResult((result,), float(result.sum().to(u.kg).magnitude))
    if scenario in {"cold-attribution-matrix", "warm-attribution-matrix", "result-primed-attribution-matrix"}:
        result = system.impact_repartition_matrix
        return ScenarioResult((result,), sum(float(row["value"]) for row in result))
    if scenario == "attributed-manufacturing":
        result = attributed_footprint(edge_patterns[0], LifeCyclePhases.MANUFACTURING)
        return ScenarioResult((result,), float(result.sum().to(u.kg).magnitude))
    if scenario == "attributed-usage":
        result = attributed_footprint(edge_patterns[0], LifeCyclePhases.USAGE)
        return ScenarioResult((result,), float(result.sum().to(u.kg).magnitude))
    if scenario == "retained-attributed-results":
        results = tuple(
            attributed_footprint(edge_patterns[index % len(edge_patterns)], LifeCyclePhases.USAGE)
            for index in range(retained_results)
        )
        return ScenarioResult(results, sum(float(result.sum().to(u.kg).magnitude) for result in results))
    raise ValueError(f"Unknown scenario: {scenario}")


def _underlying(obj):
    return getattr(obj, "_value", obj)
