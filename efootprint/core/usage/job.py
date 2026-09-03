import math
from abc import abstractmethod
from copy import copy
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_hourly_quantities import divide_or_fallback
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences
from efootprint.abstract_modeling_classes.reactive_core import (
    computed_attribute, computed_dict, computed_structure, ReverseCollection)

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.hardware.network import Network
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern


@dataclass(frozen=True, eq=False)
class JobAttributionCell:
    """One containment cell of a job — web: (step, up), edge: (rsn, ef, up) — carrying the two share kinds the
    attribution atom builders relay by: hourly_share (cell occurrences / job total occurrences, fallback 0 so the
    job's zero-occurrence hours carry no demand footprint) and flat_share (period-total occurrence share, a scalar,
    for the always-on streams). slot_multiplicity is the o(rsn, ef, up)/o(rsn, up) count ratio for edge cells
    (1 for web cells); it is already folded into both shares."""
    up: ModelingObject
    journey: ModelingObject
    hourly_share: object
    flat_share: object
    step: ModelingObject = None
    rsn: ModelingObject = None
    ef: ModelingObject = None
    slot_multiplicity: float = 1

    @property
    def location_label(self) -> str:
        """Human-readable containment location for atom labels — the step name web-side, the (rsn, ef) pair
        edge-side."""
        return self.step.name if self.step is not None else f"{self.rsn.name} via {self.ef.name}"

    @property
    def occurrence_coordinate(self) -> "JobOccurrenceCoordinate":
        if self.step is not None:
            return JobOccurrenceCoordinate(self.up, journey=self.journey, step=self.step)
        return JobOccurrenceCoordinate(self.up, recurrent_server_need=self.rsn)


@dataclass(frozen=True)
class JobOccurrenceCoordinate:
    """Stable key for one base occurrence calculation: a usage pattern and exactly one web or edge trigger."""

    usage_pattern: ModelingObject
    journey: ModelingObject = None
    step: ModelingObject = None
    recurrent_server_need: ModelingObject = None

    def __post_init__(self):
        if (self.step is None) == (self.recurrent_server_need is None):
            raise ValueError("A job occurrence coordinate requires exactly one step or recurrent server need")
        if self.step is not None and self.journey is None:
            raise ValueError("A web job occurrence coordinate requires a usage journey")
        if self.recurrent_server_need is not None and self.journey is not None:
            raise ValueError("An edge base occurrence coordinate must not include a journey")

    def __str__(self):
        trigger = self.step if self.step is not None else self.recurrent_server_need
        journey = f" / {self.journey.name}" if self.journey is not None else ""
        return f"{self.usage_pattern.name}{journey} / {trigger.name}"

    @property
    def id(self) -> str:
        trigger_kind = "step" if self.step is not None else "recurrent-server-need"
        trigger = self.step if self.step is not None else self.recurrent_server_need
        journey = f"/journey/{self.journey.id}" if self.journey is not None else ""
        return f"{self.usage_pattern.id}{journey}/{trigger_kind}/{trigger.id}"


class JobBase(ModelingObject):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    pitfalls = (
        "{param:Job.request_duration} drives concurrency. If the duration exceeds one hour the job is in flight "
        "across multiple modeling buckets at once and consumes a fraction of the server's resources in each.")

    param_descriptions = {
        "data_transferred": (
            "Total bytes uploaded plus downloaded over the network for one invocation of the job."),
        "data_stored": (
            "Net change in stored data per invocation. Positive values only. "
            "Data deletion is handled by {param:Storage.data_storage_duration}"),
        "request_duration": (
            "How long the job takes to process from start to finish on the server."),
        "compute_needed": (
            "Computational resource consumed by one invocation of the job, held for the request duration. "
            "Units depend on the server type."),
        "ram_needed": (
            "Memory held by one invocation of the job for its full duration."),
    }

    # All params except data_stored are None (and not stored) for subclasses that compute them from
    # other inputs (VideoStreamingJob, the EcoLogits jobs) — assigning a computed name raises.
    def __init__(self, name: str, data_transferred: ExplainableQuantity = None,
                 data_stored: ExplainableQuantity = None, request_duration: ExplainableQuantity = None,
                 compute_needed: ExplainableQuantity = None, ram_needed: ExplainableQuantity = None):
        super().__init__(name)
        if data_transferred is not None:
            self.data_transferred = data_transferred.set_label(
                f"Sum of all data uploads and downloads by request")
        self.data_stored = data_stored.set_label(f"Data stored by request")
        if request_duration is not None:
            self.request_duration = request_duration.set_label(f"Request duration")
        if ram_needed is not None:
            self.ram_needed = ram_needed.set_label(f"RAM needed during job processing").to(u.MB_ram)
        if compute_needed is not None:
            self.compute_needed = compute_needed.set_label(f"CPU needed during job processing")



    @property
    def duration_in_full_hours(self):
        # Use copy not to convert self.request_duration in place
        return ExplainableQuantity(
                math.ceil(copy(self.request_duration.value).to(u.hour).magnitude) * u.dimensionless,
                "Duration in full hours")

    # Job objects can be referenced by UsageJourneySteps or by RecurrentServerNeeds
    usage_journey_steps = ReverseCollection("UsageJourneyStep")
    recurrent_server_needs = ReverseCollection("RecurrentServerNeed")

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([rsn.edge_usage_patterns for rsn in self.recurrent_server_needs], start=[])))

    @property
    def edge_usage_journeys(self) -> List["EdgeUsageJourney"]:
        return list(dict.fromkeys(sum([rsn.edge_usage_journeys for rsn in self.recurrent_server_needs], start=[])))

    @property
    def usage_journeys(self) -> List["UsageJourney"]:
        return list(dict.fromkeys(sum([uj_step.usage_journeys for uj_step in self.usage_journey_steps], start=[])))

    @property
    def web_usage_patterns(self) -> List["UsagePattern"]:
        return list(dict.fromkeys(sum([uj_step.usage_patterns for uj_step in self.usage_journey_steps], start=[])))

    @property
    def usage_patterns(self) -> List["UsagePattern| EdgeUsagePattern"]:
        return self.web_usage_patterns + self.edge_usage_patterns

    @property
    def networks(self) -> List["Network"]:
        return list(dict.fromkeys(up.network for up in self.usage_patterns))

    @computed_dict(keys="usage_patterns")
    def hourly_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        """Hourly count of job invocations broken down by usage pattern, derived from when each usage pattern's journeys start and at what point in the journey this job is triggered."""
        from efootprint.core.usage.usage_pattern import UsagePattern
        if isinstance(usage_pattern, UsagePattern):
            job_occurrences = EmptyExplainableObject()
            for journey, journey_weight in usage_pattern.usage_journeys.items():
                delay_between_uj_start_and_job_evt = EmptyExplainableObject()
                for uj_step, step_times_per_journey in journey.uj_steps.items():
                    if self in uj_step.jobs:
                        job_occurrences += usage_pattern.utc_hourly_occurrences.return_shifted_hourly_quantities(
                            delay_between_uj_start_and_job_evt) * (
                            journey_weight * step_times_per_journey * uj_step.jobs[self])
                    delay_between_uj_start_and_job_evt += step_times_per_journey * uj_step.user_time_spent
        else:  # usage_pattern is an EdgeUsagePattern
            job_occurrences = EmptyExplainableObject()
            # Only server needs reachable through this pattern's selected edge usage journeys contribute. Repeated
            # containment paths are already folded into each need's per-pattern unitary volume.
            for recurrent_server_need in usage_pattern.recurrent_server_needs:
                if self not in recurrent_server_need.jobs:
                    continue
                job_occurrences += (
                        recurrent_server_need.unitary_hourly_volume_per_usage_pattern[usage_pattern]
                        * usage_pattern.nb_deployments_in_parallel
                        * recurrent_server_need.jobs[self])

        return job_occurrences.to(u.occurrence).set_label(
            f"Hourly occurrences in {usage_pattern.name}")

    @computed_dict(keys="usage_patterns")
    def hourly_avg_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        """Hourly count of job invocations averaged with respect to job duration, so a job that runs longer than an hour contributes a fractional occurrence to several modeling buckets."""
        hourly_avg_job_occurrences = compute_nb_avg_hourly_occurrences(
            self.hourly_occurrences_per_usage_pattern[usage_pattern], self.request_duration)

        return hourly_avg_job_occurrences.to(u.concurrent).set_label(
            f"Average hourly occurrences in {usage_pattern.name}")

    def _hourly_data_exchange_rate(self, data_exchange_type: str):
        data_exchange_type_no_underscore = data_exchange_type.replace("_", " ")
        return (getattr(self, data_exchange_type) * ExplainableQuantity(1 * u.hour, "one hour")
                / self.request_duration).set_label(f"{data_exchange_type_no_underscore} per hour by {self.name}")

    def compute_hourly_data_exchange_for_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern", data_exchange_type: str):
        hourly_data_exchange = (self.hourly_avg_occurrences_per_usage_pattern[usage_pattern]
                                * self._hourly_data_exchange_rate(data_exchange_type))
        target_unit = u.MB_stored if data_exchange_type == "data_stored" else u.MB

        return hourly_data_exchange.set_label(
                f"Hourly {data_exchange_type.replace('_', ' ')} in {usage_pattern.name}").to(target_unit)

    @computed_dict(keys="usage_patterns")
    def hourly_data_transferred_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        """Hourly volume of data transferred over the network by this job, broken down by usage pattern."""
        return self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_transferred")

    @computed_dict(keys="usage_patterns")
    def hourly_data_stored_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        """Hourly net change in storage volume caused by this job, broken down by usage pattern."""
        return self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_stored")

    def sum_calculated_attribute_across_usage_patterns(
            self, calculated_attribute_name: str, calculated_attribute_label: str):
        hourly_calc_attr_summed_across_ups = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            hourly_calc_attr_summed_across_ups += getattr(self, calculated_attribute_name)[usage_pattern]

        return hourly_calc_attr_summed_across_ups.set_label(
                f"Hourly {calculated_attribute_label} across usage patterns")

    @computed_attribute
    def hourly_avg_occurrences_across_usage_patterns(self):
        """Total hourly count of duration-averaged job invocations summed over every usage pattern."""
        return self.sum_calculated_attribute_across_usage_patterns(
            "hourly_avg_occurrences_per_usage_pattern", "average occurrences").to(u.concurrent)

    @computed_attribute
    def hourly_data_transferred_across_usage_patterns(self):
        """Total hourly volume of data transferred over the network by this job, summed over every usage pattern."""
        return self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_transferred_per_usage_pattern", "data transferred")

    @computed_attribute
    def hourly_data_stored_across_usage_patterns(self):
        """Total hourly net change in storage volume caused by this job, summed over every usage pattern."""
        return self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_stored_per_usage_pattern", "data stored")

    # --- Attribution-only occurrence / data primitives ---

    @property
    def occurrence_coordinates(self) -> tuple[JobOccurrenceCoordinate, ...]:
        web_coordinates = (
            JobOccurrenceCoordinate(up, journey=journey, step=step)
            for step in self.usage_journey_steps for journey in step.usage_journeys for up in journey.usage_patterns)
        edge_coordinates = (
            JobOccurrenceCoordinate(up, recurrent_server_need=rsn)
            for rsn in self.recurrent_server_needs for up in rsn.edge_usage_patterns)
        return tuple(web_coordinates) + tuple(edge_coordinates)

    @computed_dict(keys="occurrence_coordinates")
    def hourly_avg_occurrences_per_coordinate(self, coordinate: JobOccurrenceCoordinate):
        """Duration-averaged hourly occurrences for one web step or one recurrent server need within one usage
        pattern."""
        usage_pattern = coordinate.usage_pattern
        if coordinate.step is not None:
            step_occurrences = EmptyExplainableObject()
            delay_between_uj_start_and_step_start = EmptyExplainableObject()
            for journey_step, step_times_per_journey in coordinate.journey.uj_steps.items():
                if journey_step == coordinate.step and self in coordinate.step.jobs:
                    step_occurrences += (
                        usage_pattern.utc_hourly_occurrences.return_shifted_hourly_quantities(
                            delay_between_uj_start_and_step_start)
                        * (usage_pattern.usage_journeys[coordinate.journey]
                           * step_times_per_journey * coordinate.step.jobs[self]))
                delay_between_uj_start_and_step_start += step_times_per_journey * journey_step.user_time_spent
            raw_occurrences = step_occurrences
        else:
            recurrent_server_need = coordinate.recurrent_server_need
            raw_occurrences = (
                recurrent_server_need.unitary_hourly_volume_per_usage_pattern[usage_pattern]
                * usage_pattern.nb_deployments_in_parallel
                * recurrent_server_need.jobs[self])

        trigger = coordinate.step if coordinate.step is not None else coordinate.recurrent_server_need
        return compute_nb_avg_hourly_occurrences(raw_occurrences, self.request_duration).to(u.concurrent).set_label(
            f"Average hourly occurrences of {self.name} in {trigger.name} for {usage_pattern.name}")

    @computed_dict(keys="occurrence_coordinates")
    def hourly_data_transferred_per_coordinate(self, coordinate: JobOccurrenceCoordinate):
        """Hourly network data transferred for one web-step or recurrent-server-need occurrence coordinate."""
        trigger = coordinate.step if coordinate.step is not None else coordinate.recurrent_server_need
        return (self.hourly_avg_occurrences_per_coordinate[coordinate]
                * self._hourly_data_exchange_rate("data_transferred")).to(u.MB).set_label(
            f"Hourly data transferred by {self.name} in {trigger.name} for {coordinate.usage_pattern.name}")

    @computed_structure
    def attribution_cells(self):
        """Flat enumeration of the job's containment cells — one JobAttributionCell per (step, up) the job runs in
        web-side and per (rsn, ef, up) edge-side, each carrying its hourly and flat occurrence shares of the job's
        total occurrences. hourly_shares sum to 1 at every hour the job runs; flat_shares sum to 1 over the cells;
        the per-(rsn, up) slot multiplicities sum to 1 over the edge functions reaching the need. A job whose total
        occurrences are zero (zero-traffic model) still needs sum-to-1 flat shares for the always-on streams, so
        flat shares fall back to an equal share per cell; hourly shares stay zero (no hour carries demand)."""
        total_occurrences = self.hourly_avg_occurrences_across_usage_patterns
        cell_builds = []

        for uj_step in self.usage_journey_steps:
            for journey in uj_step.usage_journeys:
                for up in journey.usage_patterns:
                    coordinate = JobOccurrenceCoordinate(up, journey=journey, step=uj_step)
                    cell_builds.append((
                        dict(up=up, journey=journey, step=uj_step),
                        self.hourly_avg_occurrences_per_coordinate[coordinate],
                        f"{self.name} flat occurrence share in {journey.name} / {uj_step.name} for {up.name}"))

        for rsn in self.recurrent_server_needs:
            for edge_up in rsn.edge_usage_patterns:
                coordinate = JobOccurrenceCoordinate(edge_up, recurrent_server_need=rsn)
                rsn_occurrences = self.hourly_avg_occurrences_per_coordinate[coordinate]
                paths = [path for path in edge_up.containment_inventory.server_need_paths
                         if path.recurrent_server_need == rsn]
                total_path_occurrences = sum(path.nb_occurrences for path in paths)
                for path in paths:
                    slot_multiplicity = path.nb_occurrences / total_path_occurrences
                    cell_builds.append((
                        dict(up=edge_up, journey=path.journey, rsn=rsn, ef=path.edge_function,
                             slot_multiplicity=slot_multiplicity),
                        rsn_occurrences * ExplainableQuantity(
                            slot_multiplicity * u.dimensionless,
                            label=f"{rsn.name} slot multiplicity via {path.edge_function.name}"),
                        f"{self.name} flat occurrence share in {rsn.name} via {path.edge_function.name} "
                        f"for {edge_up.name}"))

        total_occurrences_sum = total_occurrences.sum()
        job_never_runs = total_occurrences_sum.magnitude == 0
        cells = []
        for cell_coordinates, cell_occurrences, flat_share_label in cell_builds:
            if job_never_runs:
                hourly_share = EmptyExplainableObject()
                flat_share = ExplainableQuantity(
                    1 / len(cell_builds) * u.dimensionless, label=flat_share_label)
            else:
                # Hourly shares stay unlabeled: labeled hourly series may not be dimensionless (aggregation rule).
                hourly_share = divide_or_fallback(cell_occurrences, total_occurrences, fallback=0)
                flat_share = (cell_occurrences.sum() / total_occurrences_sum).to(u.dimensionless).set_label(
                    flat_share_label)
            cells.append(JobAttributionCell(hourly_share=hourly_share, flat_share=flat_share, **cell_coordinates))

        return tuple(cells)


class DirectServerJob(JobBase):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    param_descriptions = {
        "server": (
            "{class:ServerBase} that processes the job. The server's resource use and footprint follow from the "
            "jobs it hosts."),
        **JobBase.param_descriptions,
    }

    def __init__(self, name: str, server: ServerBase, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
        self.server = server
        self.ram_needed.set_label(f"RAM needed during job processing")
        self.compute_needed.set_label(
            f"{str(compute_needed.value.units).replace('_', ' ')}s needed on server {self.server.name} "
            f"during job processing")



class Job(DirectServerJob):
    """A unit of server-side processing triggered by a {class:UsageJourneyStep} or by a {class:RecurrentServerNeed}. Defines how much CPU, memory, network bandwidth, and storage are consumed per invocation."""

    disambiguation = (
        "Use {class:Job} for CPU jobs running on a {class:Server}. Use {class:GPUJob} for jobs whose compute "
        "requirement is in GPUs. For high-level abstractions over common workloads (video streaming, generative "
        "AI), prefer the corresponding service builder rather than wiring jobs by hand.")

    param_descriptions = {
        **DirectServerJob.param_descriptions,
        "server": (
            "{class:Server} that processes the job. The server's resource use and footprint follow from the "
            "jobs it hosts."),
        "compute_needed": (
            "CPU consumed by one invocation of the job, expressed in CPU cores held for the request duration."),
        "ram_needed": (
            "RAM held by one invocation of the job for its full duration."),
    }

    default_values =  {
            "data_transferred": SourceValue(150 * u.kB),
            "data_stored": SourceValue(100 * u.kB_stored),
            "request_duration": SourceValue(1 * u.s),
            "compute_needed": SourceValue(0.1 * u.cpu_core),
            "ram_needed": SourceValue(50 * u.MB_ram)
        }

    # __init__ method is copied to change server type.
    def __init__(self, name: str, server: Server, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, server, data_transferred, data_stored, request_duration, compute_needed, ram_needed)


class GPUJob(DirectServerJob):
    """A {class:Job} whose compute requirement is expressed in GPUs and which therefore must run on a {class:GPUServer}."""

    param_descriptions = {
        **DirectServerJob.param_descriptions,
        "server": (
            "{class:GPUServer} that processes the job."),
        "compute_needed": (
            "GPU consumed by one invocation of the job, expressed in GPUs held for the request duration."),
        "ram_needed": (
            "GPU memory held by one invocation of the job for its full duration."),
    }

    default_values =  {
            "data_transferred": SourceValue(150 * u.kB),
            "data_stored": SourceValue(100 * u.kB_stored),
            "request_duration": SourceValue(1 * u.s),
            "compute_needed": SourceValue(1 * u.gpu),
            "ram_needed": SourceValue(50 * u.MB_ram)
        }

    def __init__(self, name: str, server: GPUServer, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, server, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
