import math
from abc import abstractmethod
from copy import copy
from dataclasses import dataclass
from functools import cached_property
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

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep
    from efootprint.core.hardware.network import Network
    from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed


@dataclass(frozen=True, eq=False)
class JobAttributionCell:
    """One containment cell of a job — web: (step, up), edge: (rsn, ef, up) — carrying the two share kinds the
    attribution atom builders relay by: hourly_share (cell occurrences / job total occurrences, fallback 0 so the
    job's zero-occurrence hours carry no demand footprint) and flat_share (period-total occurrence share, a scalar,
    for the always-on streams). slot_multiplicity is the o(rsn, ef, up)/o(rsn, up) count ratio for edge cells
    (1 for web cells); it is already folded into both shares."""
    up: ModelingObject
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

    def __init__(self, name: str, data_transferred: ExplainableQuantity, data_stored: ExplainableQuantity,
                 request_duration: ExplainableQuantity, compute_needed: ExplainableQuantity,
                 ram_needed: ExplainableQuantity):
        super().__init__(name)
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_transferred_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        self.hourly_avg_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_transferred_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_stored_across_usage_patterns = EmptyExplainableObject()
        self.data_transferred = data_transferred.set_label(
            f"Sum of all data uploads and downloads by request")
        self.data_stored = data_stored.set_label(f"Data stored by request")
        self.request_duration = request_duration.set_label(f"Request duration")
        self.ram_needed = ram_needed.set_label(f"RAM needed during job processing").to(u.MB_ram)
        self.compute_needed = compute_needed.set_label(f"CPU needed during job processing")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return self.networks

    calculated_attributes: List[str] = [
        "hourly_occurrences_per_usage_pattern", "hourly_avg_occurrences_per_usage_pattern",
        "hourly_data_transferred_per_usage_pattern", "hourly_data_stored_per_usage_pattern",
        "hourly_avg_occurrences_across_usage_patterns", "hourly_data_transferred_across_usage_patterns",
        "hourly_data_stored_across_usage_patterns"] + ModelingObject.calculated_attributes

    @property
    def duration_in_full_hours(self):
        # Use copy not to convert self.request_duration in place
        return ExplainableQuantity(
                math.ceil(copy(self.request_duration.value).to(u.hour).magnitude) * u.dimensionless,
                "Duration in full hours")

    # Job objects can be referenced by UsageJourneySteps or by RecurrentServerNeeds
    @property
    def usage_journey_steps(self) -> List["UsageJourneyStep"]:
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep
        return [obj for obj in self.modeling_obj_containers if isinstance(obj, UsageJourneyStep)]

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
        return [obj for obj in self.modeling_obj_containers if isinstance(obj, RecurrentServerNeed)]

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

    def update_dict_element_in_hourly_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        from efootprint.core.usage.usage_pattern import UsagePattern
        if isinstance(usage_pattern, UsagePattern):
            job_occurrences = EmptyExplainableObject()
            delay_between_uj_start_and_job_evt = EmptyExplainableObject()
            for uj_step in usage_pattern.usage_journey.uj_steps:
                nb_of_occurrences_of_self_within_step = uj_step.jobs.count(self)
                if nb_of_occurrences_of_self_within_step:
                    job_occurrences += usage_pattern.utc_hourly_usage_journey_starts.return_shifted_hourly_quantities(
                        delay_between_uj_start_and_job_evt) * ExplainableQuantity(
                        nb_of_occurrences_of_self_within_step * u.dimensionless, label="Executions per step")

                delay_between_uj_start_and_job_evt += uj_step.user_time_spent
        else:  # usage_pattern is an EdgeUsagePattern
            job_occurrences = EmptyExplainableObject()
            for recurrent_server_need in self.recurrent_server_needs:
                nb_of_occurrences_of_self_within_server_need = recurrent_server_need.jobs.count(self)
                if nb_of_occurrences_of_self_within_server_need == 0:
                    continue
                job_occurrences += (
                        recurrent_server_need.unitary_hourly_volume_per_usage_pattern[usage_pattern]
                        * usage_pattern.edge_usage_journey.
                        nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]
                        * ExplainableQuantity(
                            nb_of_occurrences_of_self_within_server_need * u.dimensionless,
                            label=f"Occurrences within {recurrent_server_need.name}"))

        self.hourly_occurrences_per_usage_pattern[usage_pattern] = job_occurrences.to(u.occurrence).set_label(
            f"Hourly occurrences in {usage_pattern.name}")

    def update_hourly_occurrences_per_usage_pattern(self):
        """Hourly count of job invocations broken down by usage pattern, derived from when each usage pattern's journeys start and at what point in the journey this job is triggered."""
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_occurrences_per_usage_pattern(up)

    def update_dict_element_in_hourly_avg_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        hourly_avg_job_occurrences = compute_nb_avg_hourly_occurrences(
            self.hourly_occurrences_per_usage_pattern[usage_pattern], self.request_duration)

        self.hourly_avg_occurrences_per_usage_pattern[usage_pattern] = hourly_avg_job_occurrences.to(u.concurrent).set_label(
            f"Average hourly occurrences in {usage_pattern.name}")

    def update_hourly_avg_occurrences_per_usage_pattern(self):
        """Hourly count of job invocations averaged with respect to job duration, so a job that runs longer than an hour contributes a fractional occurrence to several modeling buckets."""
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_avg_occurrences_per_usage_pattern(up)

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

    def update_dict_element_in_hourly_data_transferred_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        self.hourly_data_transferred_per_usage_pattern[usage_pattern] = \
            self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_transferred")

    def update_hourly_data_transferred_per_usage_pattern(self):
        """Hourly volume of data transferred over the network by this job, broken down by usage pattern."""
        self.hourly_data_transferred_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_data_transferred_per_usage_pattern(up)

    def update_dict_element_in_hourly_data_stored_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        self.hourly_data_stored_per_usage_pattern[usage_pattern] = \
            self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_stored")

    def update_hourly_data_stored_per_usage_pattern(self):
        """Hourly net change in storage volume caused by this job, broken down by usage pattern."""
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_data_stored_per_usage_pattern(up)

    def sum_calculated_attribute_across_usage_patterns(
            self, calculated_attribute_name: str, calculated_attribute_label: str):
        hourly_calc_attr_summed_across_ups = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            hourly_calc_attr_summed_across_ups += getattr(self, calculated_attribute_name)[usage_pattern]

        return hourly_calc_attr_summed_across_ups.set_label(
                f"Hourly {calculated_attribute_label} across usage patterns")

    def update_hourly_avg_occurrences_across_usage_patterns(self):
        """Total hourly count of duration-averaged job invocations summed over every usage pattern."""
        self.hourly_avg_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_avg_occurrences_per_usage_pattern", "average occurrences").to(u.concurrent)

    def update_hourly_data_transferred_across_usage_patterns(self):
        """Total hourly volume of data transferred over the network by this job, summed over every usage pattern."""
        self.hourly_data_transferred_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_transferred_per_usage_pattern", "data transferred")

    def update_hourly_data_stored_across_usage_patterns(self):
        """Total hourly net change in storage volume caused by this job, summed over every usage pattern."""
        self.hourly_data_stored_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_stored_per_usage_pattern", "data stored")

    # --- Attribution-only occurrence / data primitives (consumed by the attribution atom builders, never by the
    # eager calculated-attribute graph; get_*/compute_* are plain methods, the rest lazy cached properties) ---

    def get_hourly_avg_occurrences_per_usage_pattern_per_step(
            self, usage_pattern: "UsagePattern", uj_step: "UsageJourneyStep"):
        """Request_duration-averaged, count-weighted hourly occurrences of this job in (usage_pattern, uj_step):
        one contribution per position of the step in the pattern's journey, each shifted by its cumulative delay
        and weighted by the job's executions within the step. Summing over a journey's steps recovers
        hourly_avg_occurrences_per_usage_pattern[usage_pattern]."""
        nb_of_occurrences_of_self_within_step = uj_step.jobs.count(self)
        step_occurrences = EmptyExplainableObject()
        delay_between_uj_start_and_step_start = EmptyExplainableObject()
        for journey_step in usage_pattern.usage_journey.uj_steps:
            if journey_step == uj_step and nb_of_occurrences_of_self_within_step:
                step_occurrences += (
                    usage_pattern.utc_hourly_usage_journey_starts.return_shifted_hourly_quantities(
                        delay_between_uj_start_and_step_start)
                    * ExplainableQuantity(
                        nb_of_occurrences_of_self_within_step * u.dimensionless, label="Executions per step"))
            delay_between_uj_start_and_step_start += journey_step.user_time_spent

        return compute_nb_avg_hourly_occurrences(step_occurrences, self.request_duration).to(u.concurrent).set_label(
            f"Average hourly occurrences of {self.name} in {uj_step.name} for {usage_pattern.name}")

    def get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(
            self, edge_usage_pattern: "EdgeUsagePattern", recurrent_server_need: "RecurrentServerNeed"):
        """Request_duration-averaged, count-weighted hourly occurrences of this job triggered by
        recurrent_server_need in edge_usage_pattern — the edge analogue of
        get_hourly_avg_occurrences_per_usage_pattern_per_step. Summing over the job's recurrent server needs
        recovers hourly_avg_occurrences_per_usage_pattern[edge_usage_pattern]."""
        raw_occurrences = (
            recurrent_server_need.unitary_hourly_volume_per_usage_pattern[edge_usage_pattern]
            * edge_usage_pattern.edge_usage_journey.nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[
                edge_usage_pattern]
            * ExplainableQuantity(
                recurrent_server_need.jobs.count(self) * u.dimensionless,
                label=f"Occurrences within {recurrent_server_need.name}"))

        return compute_nb_avg_hourly_occurrences(raw_occurrences, self.request_duration).to(u.concurrent).set_label(
            f"Average hourly occurrences of {self.name} in {recurrent_server_need.name} "
            f"for {edge_usage_pattern.name}")

    def compute_hourly_data_transferred_per_usage_pattern_per_step(
            self, usage_pattern: "UsagePattern", uj_step: "UsageJourneyStep"):
        """Hourly volume of data this job transfers over the network in (usage_pattern, uj_step) — the per-cell
        data volume the Network converts to impact."""
        return (self.get_hourly_avg_occurrences_per_usage_pattern_per_step(usage_pattern, uj_step)
                * self._hourly_data_exchange_rate("data_transferred")).to(u.MB).set_label(
            f"Hourly data transferred by {self.name} in {uj_step.name} for {usage_pattern.name}")

    def compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need(
            self, edge_usage_pattern: "EdgeUsagePattern", recurrent_server_need: "RecurrentServerNeed"):
        """Hourly volume of data this job transfers over the network in (edge_usage_pattern, recurrent_server_need)
        — the edge analogue of compute_hourly_data_transferred_per_usage_pattern_per_step."""
        return (self.get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(
            edge_usage_pattern, recurrent_server_need)
                * self._hourly_data_exchange_rate("data_transferred")).to(u.MB).set_label(
            f"Hourly data transferred by {self.name} in {recurrent_server_need.name} for {edge_usage_pattern.name}")

    @cached_property
    def hourly_avg_occurrences_per_usage_journey_step(self):
        """Hourly occurrences of this job keyed by the steps triggering it, each summed over the step's usage
        patterns. Together with hourly_avg_occurrences_per_recurrent_server_need it partitions
        hourly_avg_occurrences_across_usage_patterns."""
        return {
            uj_step: sum(
                (self.get_hourly_avg_occurrences_per_usage_pattern_per_step(up, uj_step)
                 for up in uj_step.usage_patterns), start=EmptyExplainableObject()
            ).set_label(f"Average hourly occurrences of {self.name} in {uj_step.name}")
            for uj_step in self.usage_journey_steps}

    @cached_property
    def hourly_avg_occurrences_per_usage_journey(self):
        """Hourly occurrences of this job keyed by its usage journeys — the by-journey regroup of
        hourly_avg_occurrences_per_usage_pattern over the job's web usage patterns."""
        return {
            usage_journey: sum(
                (self.hourly_avg_occurrences_per_usage_pattern[up] for up in self.web_usage_patterns
                 if up.usage_journey == usage_journey), start=EmptyExplainableObject()
            ).set_label(f"Average hourly occurrences of {self.name} in {usage_journey.name}")
            for usage_journey in self.usage_journeys}

    @cached_property
    def hourly_avg_occurrences_per_recurrent_server_need(self):
        """Hourly occurrences of this job keyed by the recurrent server needs triggering it, each summed over the
        need's edge usage patterns — the edge analogue of hourly_avg_occurrences_per_usage_journey_step."""
        return {
            rsn: sum(
                (self.get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(edge_up, rsn)
                 for edge_up in rsn.edge_usage_patterns), start=EmptyExplainableObject()
            ).set_label(f"Average hourly occurrences of {self.name} in {rsn.name}")
            for rsn in self.recurrent_server_needs}

    @cached_property
    def hourly_avg_occurrences_per_edge_usage_journey(self):
        """Hourly occurrences of this job keyed by its edge usage journeys — the by-edge-journey regroup of
        hourly_avg_occurrences_per_usage_pattern over the job's edge usage patterns."""
        return {
            edge_usage_journey: sum(
                (self.hourly_avg_occurrences_per_usage_pattern[edge_up] for edge_up in self.edge_usage_patterns
                 if edge_up.edge_usage_journey == edge_usage_journey), start=EmptyExplainableObject()
            ).set_label(f"Average hourly occurrences of {self.name} in {edge_usage_journey.name}")
            for edge_usage_journey in self.edge_usage_journeys}

    @cached_property
    def hourly_data_stored_per_step(self):
        """Hourly net change in storage volume caused by this job keyed by the steps triggering it. Together with
        hourly_data_stored_per_recurrent_server_need it partitions hourly_data_stored_across_usage_patterns."""
        data_stored_per_hour = self._hourly_data_exchange_rate("data_stored")
        return {
            uj_step: (occurrences * data_stored_per_hour).to(u.MB_stored).set_label(
                f"Hourly data stored by {self.name} in {uj_step.name}")
            for uj_step, occurrences in self.hourly_avg_occurrences_per_usage_journey_step.items()}

    @cached_property
    def hourly_data_stored_per_recurrent_server_need(self):
        """Hourly net change in storage volume caused by this job keyed by the recurrent server needs triggering it
        — the edge analogue of hourly_data_stored_per_step."""
        data_stored_per_hour = self._hourly_data_exchange_rate("data_stored")
        return {
            rsn: (occurrences * data_stored_per_hour).to(u.MB_stored).set_label(
                f"Hourly data stored by {self.name} in {rsn.name}")
            for rsn, occurrences in self.hourly_avg_occurrences_per_recurrent_server_need.items()}

    @cached_property
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
            for up in uj_step.usage_patterns:
                cell_builds.append((
                    dict(up=up, step=uj_step),
                    self.get_hourly_avg_occurrences_per_usage_pattern_per_step(up, uj_step),
                    f"{self.name} flat occurrence share in {uj_step.name} for {up.name}"))

        for rsn in self.recurrent_server_needs:
            for edge_up in rsn.edge_usage_patterns:
                rsn_occurrences = self.get_hourly_avg_occurrences_per_usage_pattern_per_recurrent_server_need(
                    edge_up, rsn)
                journey_edge_functions = edge_up.edge_usage_journey.edge_functions
                rsn_occurrences_in_journey = sum(
                    ef.recurrent_server_needs.count(rsn) for ef in journey_edge_functions)
                for ef in rsn.edge_functions:
                    nb_journey_uses_of_ef = journey_edge_functions.count(ef)
                    if nb_journey_uses_of_ef == 0:
                        continue
                    slot_multiplicity = (nb_journey_uses_of_ef * ef.recurrent_server_needs.count(rsn)
                                         / rsn_occurrences_in_journey)
                    cell_builds.append((
                        dict(up=edge_up, rsn=rsn, ef=ef, slot_multiplicity=slot_multiplicity),
                        rsn_occurrences * ExplainableQuantity(
                            slot_multiplicity * u.dimensionless, label=f"{rsn.name} slot multiplicity via {ef.name}"),
                        f"{self.name} flat occurrence share in {rsn.name} via {ef.name} for {edge_up.name}"))

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

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.server] + super().modeling_objects_whose_attributes_depend_directly_on_me


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
