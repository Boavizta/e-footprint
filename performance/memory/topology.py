"""Synthetic model topology shared by deterministic gates and fresh-process profiles."""

from dataclasses import dataclass
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.edge.edge_computer import EdgeComputer
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.builders.usage.edge.recurrent_edge_process import RecurrentEdgeProcess
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_storage import EdgeStorage
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


@dataclass(frozen=True)
class TopologyConfig:
    """Dimensions of a deterministic mixed web/edge model."""

    modeled_hours: int = 168
    pattern_count: int = 2
    journeys_per_pattern: int = 3
    shared_children: bool = True

    def __post_init__(self):
        if self.modeled_hours < 1 or self.pattern_count < 1 or self.journeys_per_pattern < 1:
            raise ValueError("Topology dimensions must all be positive")


@dataclass(frozen=True)
class SyntheticTopology:
    """A generated system plus the objects needed by structural assertions."""

    system: System
    web_journeys: tuple[UsageJourney, ...]
    web_steps: tuple[UsageJourneyStep, ...]
    jobs: tuple[Job, ...]
    edge_journeys: tuple[EdgeUsageJourney, ...]
    edge_functions: tuple[EdgeFunction, ...]
    edge_processes: tuple[RecurrentEdgeProcess, ...]
    recurrent_server_needs: tuple[RecurrentServerNeed, ...]

    @property
    def recurrent_component_needs(self) -> tuple:
        return tuple(
            need
            for process in self.edge_processes
            for need in process.recurrent_edge_component_needs
        )


def _hourly_values(hours: int, volume: float):
    return create_source_hourly_values_from_list(
        [volume] * hours, start_date=datetime(2026, 1, 5))


def _web_child(index: int) -> tuple[Storage, Server, Job, UsageJourneyStep]:
    suffix = f" {index}"
    storage = Storage.from_defaults(f"memory lab web storage{suffix}")
    server = Server.from_defaults(
        f"memory lab web server{suffix}", server_type=ServerTypes.autoscaling(), storage=storage)
    job = Job.from_defaults(
        f"memory lab shared job{suffix}", server=server,
        data_transferred=SourceValue(2 * u.MB), data_stored=SourceValue(0.01 * u.MB_stored))
    step = UsageJourneyStep(
        f"memory lab shared step{suffix}", user_time_spent=SourceValue(5 * u.min), jobs=[job])
    return storage, server, job, step


def _edge_child(index: int, job: Job) -> tuple[EdgeFunction, RecurrentEdgeProcess, RecurrentServerNeed]:
    suffix = f" {index}"
    storage = EdgeStorage.from_defaults(f"memory lab edge storage{suffix}")
    computer = EdgeComputer.from_defaults(
        f"memory lab edge computer{suffix}", storage=storage,
        compute=SourceValue(1000 * u.cpu_core), ram=SourceValue(1000 * u.GB_ram))
    process = RecurrentEdgeProcess.from_defaults(
        f"memory lab shared edge process{suffix}", edge_device=computer)
    server_need = RecurrentServerNeed.from_defaults(
        f"memory lab shared server need{suffix}", edge_device=computer, jobs=[job])
    edge_function = EdgeFunction(
        f"memory lab shared edge function{suffix}",
        recurrent_edge_device_needs=[process], recurrent_server_needs=[server_need])
    return edge_function, process, server_need


def build_synthetic_topology(config: TopologyConfig = TopologyConfig()) -> SyntheticTopology:
    """Build a mixed model whose journeys are reusable while lower-level children can be shared or distinct."""
    country = Countries.FRANCE()
    web_children = (
        [_web_child(1)] * config.journeys_per_pattern
        if config.shared_children
        else [_web_child(index + 1) for index in range(config.journeys_per_pattern)]
    )
    web_journeys = tuple(
        UsageJourney(f"memory lab web journey {index + 1}", uj_steps=[child[3]])
        for index, child in enumerate(web_children)
    )

    web_patterns = []
    for pattern_index in range(config.pattern_count):
        weights = {journey: 1 + journey_index / 10 for journey_index, journey in enumerate(web_journeys)}
        web_patterns.append(UsagePattern(
            f"memory lab web pattern {pattern_index + 1}", usage_journeys=weights,
            devices=[Device.laptop(f"memory lab device {pattern_index + 1}")],
            network=Network.from_defaults(f"memory lab web network {pattern_index + 1}"),
            country=country,
            hourly_occurrences=_hourly_values(config.modeled_hours, 10 + pattern_index)))

    jobs = tuple(dict.fromkeys(child[2] for child in web_children))
    edge_children = (
        [_edge_child(1, jobs[0])] * config.journeys_per_pattern
        if config.shared_children
        else [_edge_child(index + 1, jobs[index]) for index in range(config.journeys_per_pattern)]
    )
    edge_journeys = tuple(
        EdgeUsageJourney(f"memory lab edge journey {index + 1}", edge_functions=[child[0]])
        for index, child in enumerate(edge_children)
    )

    edge_patterns = tuple(
        EdgeUsagePattern(
            f"memory lab edge pattern {pattern_index + 1}", edge_usage_journeys=list(edge_journeys),
            network=Network.from_defaults(f"memory lab edge network {pattern_index + 1}"),
            country=country,
            hourly_deployment_starts=_hourly_values(config.modeled_hours, 1 + pattern_index),
            usage_span=SourceValue(1 * u.hour))
        for pattern_index in range(config.pattern_count)
    )

    system = System("memory lab system", usage_patterns=web_patterns, edge_usage_patterns=list(edge_patterns))
    return SyntheticTopology(
        system=system,
        web_journeys=web_journeys,
        web_steps=tuple(dict.fromkeys(child[3] for child in web_children)),
        jobs=jobs,
        edge_journeys=edge_journeys,
        edge_functions=tuple(dict.fromkeys(child[0] for child in edge_children)),
        edge_processes=tuple(dict.fromkeys(child[1] for child in edge_children)),
        recurrent_server_needs=tuple(dict.fromkeys(child[2] for child in edge_children)),
    )
