import math
from copy import copy
from functools import cached_property
from typing import List, TYPE_CHECKING, Optional

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.core.attribution import Atom
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities, divide_or_fallback)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases

if TYPE_CHECKING:
    from efootprint.core.usage.job import JobBase
    from efootprint.core.hardware.server_base import ServerBase


def cumulative_storage_need_with_dumps(replicated_storage_rate, data_storage_duration: ExplainableQuantity):
    """Cumulative sum with automatic dumps: data written at hour h is dumped at h + data_storage_duration,
    so the cumulative tracks the volume currently held. Linear in the rate — per-cell cumulatives sum exactly
    to per-job cumulatives, which is what makes the retention attribution weights conserve."""
    if isinstance(replicated_storage_rate, EmptyExplainableObject):
        return EmptyExplainableObject(left_parent=replicated_storage_rate)
    storage_rate = replicated_storage_rate.to(u.TB_stored)
    rate_array = np.copy(storage_rate.value.magnitude)
    storage_duration_in_hours = math.ceil(copy(data_storage_duration.to(u.hour)).magnitude)
    auto_dumps_array = -np.pad(
        storage_rate.value, (storage_duration_in_hours, 0), constant_values=np.float32(0)
    )[:len(rate_array)]
    delta_array = rate_array + auto_dumps_array.magnitude
    cumulative_quantity = Quantity(np.cumsum(delta_array, dtype=np.float32), u.TB_stored)

    return ExplainableHourlyQuantities(
        cumulative_quantity, start_date=storage_rate.start_date,
        left_parent=replicated_storage_rate, right_parent=data_storage_duration,
        operator="cumulative sum with automatic dumps")


class Storage(InfraHardware):
    """Persistent storage backing a {class:Server} (typically SSD or HDD). Capacity is sized to the cumulative volume of data jobs write, plus an optional baseline."""

    disambiguation = (
        "Storage is allocated per-server through {param:Server.storage}. Use the archetype helpers "
        "(`Storage.ssd()`, `Storage.hdd()`) for sensible defaults, then override fields as needed.")

    pitfalls = (
        "{param:Storage.data_storage_duration} controls how long data lives before it is automatically dumped. "
        "Setting it longer than the modeling period means the storage need only ever grows, which can sharply "
        "inflate the number of instances required. "
        "{param:Storage.base_storage_need} is the physical storage required at t=0 (replicas already included) "
        "and is not multiplied by {param:Storage.data_replication_factor} — that factor only applies to "
        "job-driven growth.")

    param_descriptions = {
        "storage_capacity": (
            "Capacity of one storage instance. Used as the divisor when sizing the number of instances "
            "required to hold the cumulative storage need."),
        "carbon_footprint_fabrication_per_storage_capacity": (
            "Embodied carbon emitted to manufacture one unit of storage capacity. Multiplied by capacity to "
            "obtain the per-instance fabrication footprint."),
        "data_replication_factor": (
            "Multiplier accounting for redundant copies stored on top of the live data, such as a value of 3 "
            "for a triplicated cluster."),
        "data_storage_duration": (
            "How long stored data is retained before being automatically dumped. Drives how cumulative storage "
            "grows over time."),
        "base_storage_need": (
            "Physical storage required at t=0, before any job has written data — replicas included if the "
            "baseline data is replicated in reality. Added on top of the cumulative job-driven storage need; "
            "unlike that one, it is not multiplied by {param:Storage.data_replication_factor}."),
        "lifespan": (
            "Expected time before a storage instance is replaced. Embodied carbon is amortised over this duration."),
        "fixed_nb_of_instances": (
            "Number of physical storage units deployed when capacity is provisioned ahead of time. Leave empty "
            "to let e-footprint size capacity from the cumulative storage need."),
    }

    default_values = {
        "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB_stored),
        "lifespan": SourceValue(6 * u.years),
        "storage_capacity": SourceValue(1 * u.TB_stored),
        "data_replication_factor": SourceValue(3 * u.dimensionless),
        "base_storage_need": SourceValue(0 * u.TB_stored),
        "data_storage_duration": SourceValue(5 * u.year)
    }

    @classmethod
    def ssd(cls, name="Default SSD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                160 * u.kg / u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years),
            "storage_capacity": SourceValue(1 * u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless),
            "base_storage_need": SourceValue(0 * u.TB_stored),
            "data_storage_duration": SourceValue(5 * u.year)
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years),
            "storage_capacity": SourceValue(1 * u.TB_stored, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless),
            "base_storage_need": SourceValue(0 * u.TB_stored),
            "data_storage_duration": SourceValue(5 * u.year)
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.ssd, cls.hdd]

    def __init__(self, name: str, storage_capacity: ExplainableQuantity,
                 carbon_footprint_fabrication_per_storage_capacity: ExplainableQuantity,
                 data_replication_factor: ExplainableQuantity, data_storage_duration: ExplainableQuantity,
                 base_storage_need: ExplainableQuantity, lifespan: ExplainableQuantity,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W), lifespan=lifespan)
        self.carbon_footprint_fabrication_per_storage_capacity = (carbon_footprint_fabrication_per_storage_capacity
            .set_label(f"Fabrication carbon footprint per storage capacity"))
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity")
        self.data_replication_factor = data_replication_factor.set_label(f"Data replication factor")
        self.data_storage_duration = data_storage_duration.set_label(f"Data storage duration")
        self.base_storage_need = base_storage_need.set_label("Initial storage need")
        self.fixed_nb_of_instances = (fixed_nb_of_instances or EmptyExplainableObject()).set_label(
            f"User defined number of instances").to(u.concurrent)
        self.full_cumulative_storage_need = EmptyExplainableObject()
        self.full_cumulative_storage_need_per_job = ExplainableObjectDict()
        self.shared_storage_per_job = EmptyExplainableObject()

    @property
    def server(self) -> Optional["ServerBase"]:
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"Storage object can only be associated with one server object but {self.name} is associated "
                    f"with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    calculated_attributes = (
        ["carbon_footprint_fabrication", "full_cumulative_storage_need_per_job", "full_cumulative_storage_need"]
        + InfraHardware.calculated_attributes
        + ["shared_storage_per_job"]
        + [attr for attr in ModelingObject.calculated_attributes
           if attr not in {"usage_impact_repartition_weights"}])

    @property
    def jobs(self) -> List["JobBase"]:
        server = self.server
        if server is not None:
            return server.jobs
        return []

    @property
    def power_usage_effectiveness(self):
        if self.server is not None:
            return self.server.power_usage_effectiveness
        else:
            return EmptyExplainableObject()

    @property
    def average_carbon_intensity(self):
        if self.server is not None:
            return self.server.average_carbon_intensity
        else:
            return EmptyExplainableObject()

    def update_carbon_footprint_fabrication(self):
        """Embodied carbon of one storage instance, equal to the per-capacity fabrication footprint times the instance's capacity."""
        self.carbon_footprint_fabrication = (
            self.carbon_footprint_fabrication_per_storage_capacity * self.storage_capacity).set_label(
            f"Carbon footprint")

    def update_dict_element_in_full_cumulative_storage_need_per_job(self, job: "JobBase"):
        job_storage_rate = job.hourly_data_stored_across_usage_patterns * self.data_replication_factor
        self.full_cumulative_storage_need_per_job[job] = cumulative_storage_need_with_dumps(
            job_storage_rate, self.data_storage_duration).set_label(f"Cumulative storage need for {job.name}")

    def update_full_cumulative_storage_need_per_job(self):
        """Per-job cumulative volume of stored data over time, applying the replication factor and dropping data older than {param:Storage.data_storage_duration}."""
        self.full_cumulative_storage_need_per_job = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_full_cumulative_storage_need_per_job(job)

    def update_full_cumulative_storage_need(self):
        """Total cumulative storage volume held by this storage at each hour, summing per-job cumulative needs and adding the base storage need."""
        all_cumulatives = sum([val for val in self.full_cumulative_storage_need_per_job.values()],
                              start=EmptyExplainableObject())
        if isinstance(all_cumulatives, EmptyExplainableObject):
            # This means that the storage isn’t used by any job linked to a usage pattern, so it doesn’ make sense to
            # compute its impact at all. Adding the base storage need would turn the full_cumulative_storage_need into
            # an ExplainableQuantity, which would cause bugs down the line, for computations that don’t make sense
            # anyways (we don’t even know how long the Storage object will be used for).
            self.full_cumulative_storage_need = all_cumulatives
        else:
            all_cumulatives += self.base_storage_need
            self.full_cumulative_storage_need = all_cumulatives.set_label(
                f"Full cumulative storage need")

    def update_raw_nb_of_instances(self):
        """Hourly storage instances strictly required to hold the cumulative storage need, before rounding."""
        raw_nb_of_instances = (self.full_cumulative_storage_need / self.storage_capacity).to(u.concurrent)
        self.raw_nb_of_instances = raw_nb_of_instances.set_label(f"Hourly raw number of instances")

    def update_nb_of_instances(self):
        """Hourly storage instances actually attributed: fractional for serverless backends (only used capacity is billed), held to the user-fixed count if set, otherwise ceiled to whole instances."""
        from efootprint.core.hardware.server_base import ServerTypes
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
        elif self.server is not None and self.server.server_type == ServerTypes.serverless():
            nb_of_instances = self.raw_nb_of_instances.copy()
        elif not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
            ceiled_nb_of_instances = self.raw_nb_of_instances.ceil()
            max_nb_of_instances = ceiled_nb_of_instances.max()
            if max_nb_of_instances > self.fixed_nb_of_instances:
                raise InsufficientCapacityError(
                    self, "number of instances", self.fixed_nb_of_instances, max_nb_of_instances)
            else:
                fixed_nb_of_instances_quantity = Quantity(
                    np.full(
                        len(self.raw_nb_of_instances),
                        np.float32(self.fixed_nb_of_instances.to(u.concurrent).magnitude)
                    ), u.concurrent)
                fixed_nb_of_instances = ExplainableHourlyQuantities(
                    fixed_nb_of_instances_quantity, self.raw_nb_of_instances.start_date, "Nb of instances",
                    left_parent=self.raw_nb_of_instances, right_parent=self.fixed_nb_of_instances)
            nb_of_instances = fixed_nb_of_instances
        else:
            ceiled_nb_of_instances = self.raw_nb_of_instances.ceil()
            nb_of_instances = ceiled_nb_of_instances
        nb_of_instances = (nb_of_instances
                           .generate_explainable_object_with_logical_dependency(self.fixed_nb_of_instances)
                           .set_label(f"Hourly number of instances"))
        if self.server is not None:
            nb_of_instances = nb_of_instances.generate_explainable_object_with_logical_dependency(
                self.server.server_type)
        self.nb_of_instances = nb_of_instances

    def update_instances_energy(self):
        """Hourly energy consumed by storage instances. Currently always empty: storage operating energy is folded into the hosting server's energy footprint rather than tracked separately."""
        self.instances_energy = EmptyExplainableObject()

    def update_shared_storage_per_job(self):
        """Per-job share of capacity not driven by job-specific cumulative needs (unused capacity + base storage need), divided evenly across jobs. Used as the shared term when attributing storage fabrication footprint to jobs."""
        if not self.jobs:
            self.shared_storage_per_job = EmptyExplainableObject()
            return
        unused_storage = (self.nb_of_instances * self.storage_capacity - self.full_cumulative_storage_need).to(u.GB_stored)
        self.shared_storage_per_job = (
            (unused_storage + self.base_storage_need)
            / ExplainableQuantity(len(self.jobs) * u.dimensionless, "Number of jobs")
        ).to(u.GB_stored).set_label("Shared storage per job")

    def update_dict_element_in_fabrication_impact_repartition_weights(self, job: "JobBase"):
        self.fabrication_impact_repartition_weights[job] = (
            self.full_cumulative_storage_need_per_job[job] + self.shared_storage_per_job
        ).set_label(f"{job.name} fabrication weight in impact repartition")

    def update_fabrication_impact_repartition_weights(self):
        """Per-job weights used to attribute storage fabrication footprint to jobs, equal to each job's cumulative storage plus an even share of the unused capacity and base storage need."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_fabrication_impact_repartition_weights(job)

    @property
    def usage_impact_repartition_weights(self):
        if isinstance(self.energy_footprint, EmptyExplainableObject):
            return ExplainableObjectDict()
        raise NotImplementedError(
            f"Usage impact repartition is not implemented for {self.name} when Storage has a non-empty energy footprint."
        )

    # --- Attribution-only stream split and atom builder (lazy cached properties, consumed only by the
    # attribution layer, never by the eager calculated-attribute graph) ---

    @cached_property
    def job_written_cumulative_storage_need(self):
        """N — the job-written cumulative storage volume held over time, excluding base_storage_need: the sum
        of full_cumulative_storage_need_per_job over the storage's jobs. The retention stream's driver and the
        denominator of its per-cell attribution weights."""
        return sum(
            self.full_cumulative_storage_need_per_job.values(), start=EmptyExplainableObject()
        ).set_label(f"Job-written cumulative storage need of {self.name}")

    @cached_property
    def storage_retention_fabrication_footprint(self):
        """Retention stream — the share of the fabrication footprint driven by job-written data:
        F × N / provisioned_capacity, with provisioned_capacity = nb_of_instances × storage_capacity.
        divide_or_fallback(fallback=0) is exact: zero provisioned capacity at an hour implies N == 0 there."""
        if (isinstance(self.nb_of_instances, EmptyExplainableObject)
                or isinstance(self.job_written_cumulative_storage_need, EmptyExplainableObject)):
            return EmptyExplainableObject(left_parent=self.instances_fabrication_footprint).set_label(
                f"{self.name} retention fabrication footprint")
        provisioned_capacity = (self.nb_of_instances * self.storage_capacity).to(u.TB_stored)
        retention_share = divide_or_fallback(
            self.job_written_cumulative_storage_need, provisioned_capacity, fallback=0)

        return (self.instances_fabrication_footprint * retention_share).to(u.kg).set_label(
            f"{self.name} retention fabrication footprint")

    @cached_property
    def storage_baseline_fabrication_footprint(self):
        """Baseline stream — the rest of the fabrication footprint: F × (unused_storage + base_storage_need)
        / provisioned_capacity. Since provisioned_capacity = N + unused + base, the two streams sum to F
        exactly (nb_of_instances cancels in each)."""
        if (isinstance(self.nb_of_instances, EmptyExplainableObject)
                or isinstance(self.full_cumulative_storage_need, EmptyExplainableObject)):
            return EmptyExplainableObject(left_parent=self.instances_fabrication_footprint).set_label(
                f"{self.name} baseline fabrication footprint")
        provisioned_capacity = (self.nb_of_instances * self.storage_capacity).to(u.TB_stored)
        unused_storage = provisioned_capacity - self.full_cumulative_storage_need
        baseline_share = divide_or_fallback(
            (unused_storage + self.base_storage_need).to(u.TB_stored), provisioned_capacity, fallback=0)

        return (self.instances_fabrication_footprint * baseline_share).to(u.kg).set_label(
            f"{self.name} baseline fabrication footprint")

    @cached_property
    def retention_cumulative_per_cell(self) -> dict:
        """Per-cell cumulative storage volume held, over every attribution cell of the storage's jobs — the
        hourly numerators of the retention weights. A cell's replicated data-stored rate is its hourly
        occurrence share × the job's replicated rate (exact: the cell's occurrences are zero wherever the
        job's total is), pushed through the same cumsum-with-dumps as full_cumulative_storage_need_per_job,
        whose linearity makes the per-cell cumulatives sum exactly to the per-job cumulative and, across
        jobs, to N."""
        cumulatives = {}
        for job in self.jobs:
            replicated_job_rate = job.hourly_data_stored_across_usage_patterns * self.data_replication_factor
            for cell in job.attribution_cells:
                cumulatives[cell] = cumulative_storage_need_with_dumps(
                    cell.hourly_share * replicated_job_rate, self.data_storage_duration).set_label(
                    f"Cumulative storage need of {job.name} in {cell.location_label} ({cell.up.name})")

        return cumulatives

    @cached_property
    def baseline_flat_share_per_job(self) -> dict:
        """Flat period-total occurrence share of each job in the storage's total job occurrences — the
        always-on baseline stream's job weights (flat shares carry footprint at idle hours, where hourly
        ratios are 0/0: fallback 0 drops that footprint and fallback 1 books it once per cell — the bug the
        flat kind fixes). Falls back to an equal share per job when total occurrences are zero, so the
        weights still sum to 1 on a zero-traffic model (every job reaches a Storage through a usage
        pattern, so each holds at least one attribution cell)."""
        period_occurrences_per_job = {
            job: job.hourly_avg_occurrences_across_usage_patterns.sum() for job in self.jobs}
        total_occurrences = sum(period_occurrences_per_job.values(), start=EmptyExplainableObject())
        if isinstance(total_occurrences, EmptyExplainableObject) or total_occurrences.magnitude == 0:
            return {
                job: ExplainableQuantity(
                    1 / len(self.jobs) * u.dimensionless,
                    f"{job.name} flat occurrence share of {self.name} jobs")
                for job in self.jobs}

        return {
            job: (occurrences / total_occurrences).to(u.dimensionless).set_label(
                f"{job.name} flat occurrence share of {self.name} jobs")
            for job, occurrences in period_occurrences_per_job.items()}

    def attribution_atoms(self, phase: LifeCyclePhases):
        """One atom per (stream, job, containment cell) of the fabrication phase — storage operating energy
        is folded into the hosting server, so the usage phase carries no atoms. The retention stream relays
        by hourly per-cell cumulative / N weights (a demand stream: zero held data ⇒ zero footprint); the
        baseline stream relays by flat period-total occurrence shares (always-on: the instances hold their
        unused + base capacity at idle hours). Cells span web steps and edge recurrent server needs, so a
        storage written from both sides splits across both."""
        if phase == LifeCyclePhases.USAGE or isinstance(self.instances_fabrication_footprint,
                                                        EmptyExplainableObject):
            return
        retention_footprint = self.storage_retention_fabrication_footprint
        baseline_footprint = self.storage_baseline_fabrication_footprint
        job_written_need = self.job_written_cumulative_storage_need
        for job in self.jobs:
            job_baseline_share = self.baseline_flat_share_per_job[job]
            for cell in job.attribution_cells:
                cell_cumulative = self.retention_cumulative_per_cell[cell]
                if isinstance(cell_cumulative, EmptyExplainableObject):
                    retention_value = EmptyExplainableObject(
                        left_parent=retention_footprint, right_parent=cell_cumulative)
                else:
                    retention_value = (
                        retention_footprint * divide_or_fallback(cell_cumulative, job_written_need, fallback=0)
                    ).to(u.kg)
                yield Atom(
                    source=self, stream="retention", job=job, up=cell.up, step=cell.step, rsn=cell.rsn,
                    ef=cell.ef,
                    value=retention_value.set_label(
                        f"{self.name} retention fabrication footprint via {job.name} "
                        f"in {cell.location_label} ({cell.up.name})"))
                yield Atom(
                    source=self, stream="baseline", job=job, up=cell.up, step=cell.step, rsn=cell.rsn,
                    ef=cell.ef,
                    value=(baseline_footprint * job_baseline_share * cell.flat_share).to(u.kg).set_label(
                        f"{self.name} baseline fabrication footprint via {job.name} "
                        f"in {cell.location_label} ({cell.up.name})"))
