from collections import Counter
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from efootprint.core.country import Country
from efootprint.core.hardware.network import Network
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities)
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.reactive_core import computed_attribute, computed_structure
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences

if TYPE_CHECKING:
    from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
    from efootprint.core.usage.job import JobBase
    from efootprint.core.usage.edge.edge_function import EdgeFunction
    from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed


@dataclass(frozen=True)
class EdgeServerNeedPath:
    journey: EdgeUsageJourney
    edge_function: "EdgeFunction"
    recurrent_server_need: "RecurrentServerNeed"
    nb_occurrences: int


@dataclass(frozen=True)
class EdgeComponentNeedPath:
    journey: EdgeUsageJourney
    edge_function: "EdgeFunction"
    recurrent_edge_device_need: "RecurrentEdgeDeviceNeed"
    recurrent_edge_component_need: "RecurrentEdgeComponentNeed"
    nb_occurrences: int


@dataclass(frozen=True)
class EdgeContainmentInventory:
    server_need_paths: tuple[EdgeServerNeedPath, ...]
    component_need_paths: tuple[EdgeComponentNeedPath, ...]


class EdgeUsagePattern(ModelingObject):
    """One edge deployment cohort carrying a non-empty set of functionality bundles for a shared usage span."""

    disambiguation = (
        "Use {class:EdgeUsagePattern} for hardware deployed continuously in the field. Use {class:UsagePattern} "
        "for end-user devices that run a request-style {class:UsageJourney} in a web context. See {doc:web_vs_edge}.")

    param_descriptions = {
        "edge_usage_journeys": (
            "Non-empty, duplicate-free list of {class:EdgeUsageJourney} functionality bundles carried by every "
            "deployment in this pattern."),
        "usage_span": (
            "How long each physical deployment remains active. All selected functionality bundles share this span."),
        "network": (
            "{class:Network} used by the edge devices to communicate with servers (when applicable)."),
        "country": (
            "{class:Country} where the edge devices are deployed. Drives grid carbon intensity and the "
            "timezone of {param:EdgeUsagePattern.hourly_deployment_starts}."),
        "hourly_deployment_starts": (
            "Hourly timeseries giving how many deployment cohorts begin in each hour of the modeling period."),
    }

    default_values = {"usage_span": SourceValue(6 * u.year)}

    def __init__(self, name: str, edge_usage_journeys: List[EdgeUsageJourney], network: Network,
                 country: Country, hourly_deployment_starts: ExplainableHourlyQuantities,
                 usage_span: ExplainableQuantity | None = None):
        super().__init__(name)
        self.hourly_deployment_starts = hourly_deployment_starts.to(u.occurrence).set_label(
            "Hourly nb of deployment starts")
        self.edge_usage_journeys = edge_usage_journeys
        self._validate_edge_usage_journeys()
        self.usage_span = (usage_span if usage_span is not None else SourceValue(6 * u.year)).set_label("Usage span")
        self.network = network
        self.country = country

    def _validate_edge_usage_journeys(self):
        if not self.edge_usage_journeys:
            raise ValueError(f"EdgeUsagePattern '{self.name}' requires at least one edge usage journey")
        if len(set(self.edge_usage_journeys)) != len(self.edge_usage_journeys):
            raise ValueError(f"EdgeUsagePattern '{self.name}' cannot contain duplicate edge usage journeys")

    @computed_attribute(guard=True)
    def edge_usage_journeys_validation(self):
        """Validates that the pattern always contains unique functionality bundles."""
        self._validate_edge_usage_journeys()
        return EmptyExplainableObject()

    @property
    def recurrent_edge_device_needs(self) -> List["RecurrentEdgeDeviceNeed"]:
        return list(dict.fromkeys(
            need for journey in self.edge_usage_journeys for need in journey.recurrent_edge_device_needs))

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        return list(dict.fromkeys(need for journey in self.edge_usage_journeys for need in journey.recurrent_server_needs))

    @property
    def jobs(self) -> List["JobBase"]:
        return list(dict.fromkeys(job for journey in self.edge_usage_journeys for job in journey.jobs))

    @computed_structure
    def containment_inventory(self):
        """Actual functionality-bundle containment paths with nested-list multiplicities collapsed to counts."""
        server_paths = Counter()
        component_paths = Counter()
        for journey in self.edge_usage_journeys:
            for edge_function in journey.edge_functions:
                for server_need in edge_function.recurrent_server_needs:
                    server_paths[(journey, edge_function, server_need)] += 1
                for device_need in edge_function.recurrent_edge_device_needs:
                    for component_need in device_need.recurrent_edge_component_needs:
                        component_paths[(journey, edge_function, device_need, component_need)] += 1
        return EdgeContainmentInventory(
            server_need_paths=tuple(EdgeServerNeedPath(*path, count) for path, count in server_paths.items()),
            component_need_paths=tuple(EdgeComponentNeedPath(*path, count) for path, count in component_paths.items()),
        )

    @computed_attribute
    def utc_hourly_deployment_starts(self):
        """Hourly deployment starts converted from the country's local timezone to UTC."""
        return self.hourly_deployment_starts.convert_to_utc(local_timezone=self.country.timezone).set_label(
            "Hourly nb of deployment starts (UTC)")

    @computed_attribute
    def nb_deployments_in_parallel(self):
        """Hourly count of active physical deployments derived from deployment starts and usage span."""
        return compute_nb_avg_hourly_occurrences(self.utc_hourly_deployment_starts, self.usage_span).to(
            u.concurrent).set_label("Hourly nb of deployments in parallel")
