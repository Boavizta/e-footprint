import math
from copy import copy
from typing import List, TYPE_CHECKING, Optional

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u

if TYPE_CHECKING:
    from efootprint.core.usage.job import JobBase
    from efootprint.core.hardware.server_base import ServerBase


class Storage(InfraHardware):
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

    @property
    def calculated_attributes(self):
        return ([
            "carbon_footprint_fabrication", "full_cumulative_storage_need_per_job", "full_cumulative_storage_need"]
        + InfraHardware.calculated_attributes.fget(self)
        + [attr for attr in ModelingObject.calculated_attributes.fget(self)
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
        self.carbon_footprint_fabrication = (
            self.carbon_footprint_fabrication_per_storage_capacity * self.storage_capacity).set_label(
            f"Carbon footprint")

    def update_dict_element_in_full_cumulative_storage_need_per_job(self, job: "JobBase"):
        job_storage_rate = (
            job.hourly_data_stored_across_usage_patterns * self.data_replication_factor).to(u.TB_stored)
        if isinstance(job_storage_rate, EmptyExplainableObject):
            self.full_cumulative_storage_need_per_job[job] = EmptyExplainableObject(
                left_parent=job_storage_rate, label=f"Cumulative storage for {job.name} in {self.name}")
            return
        rate_array = np.copy(job_storage_rate.value.magnitude)
        storage_duration_in_hours = math.ceil(copy(self.data_storage_duration.to(u.hour)).magnitude)
        auto_dumps_array = -np.pad(
            job_storage_rate.value, (storage_duration_in_hours, 0), constant_values=np.float32(0)
        )[:len(rate_array)]
        delta_array = rate_array + auto_dumps_array.magnitude
        cumulative_quantity = Quantity(np.cumsum(delta_array, dtype=np.float32), u.TB_stored)
        self.full_cumulative_storage_need_per_job[job] = ExplainableHourlyQuantities(
            cumulative_quantity, start_date=job_storage_rate.start_date,
            label=f"Cumulative storage for {job.name} in {self.name}",
            left_parent=job_storage_rate, right_parent=self.data_storage_duration,
            operator="cumulative sum with automatic dumps")

    def update_full_cumulative_storage_need_per_job(self):
        self.full_cumulative_storage_need_per_job = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_full_cumulative_storage_need_per_job(job)

    def update_full_cumulative_storage_need(self):
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
        raw_nb_of_instances = (self.full_cumulative_storage_need / self.storage_capacity).to(u.concurrent)
        self.raw_nb_of_instances = raw_nb_of_instances.set_label(f"Hourly raw number of instances")

    def update_nb_of_instances(self):
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
        self.instances_energy = EmptyExplainableObject()

    def update_dict_element_in_fabrication_impact_repartition_weights(self, job: "JobBase"):
        unused_storage = (self.nb_of_instances * self.storage_capacity - self.full_cumulative_storage_need).to(u.GB_stored)
        shared_storage_per_job = (
            (unused_storage + self.base_storage_need)
            / ExplainableQuantity(len(self.jobs) * u.dimensionless, "Number of jobs")
        ).to(u.GB_stored)
        self.fabrication_impact_repartition_weights[job] = (
            self.full_cumulative_storage_need_per_job[job] + shared_storage_per_job
        ).set_label(f"{job.name} fabrication weight in {self.name} impact repartition")

    def update_fabrication_impact_repartition_weights(self):
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
