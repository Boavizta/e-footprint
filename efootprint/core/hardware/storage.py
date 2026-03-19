import math
from copy import copy
from typing import List, TYPE_CHECKING, Optional

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
        "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB),
        "lifespan": SourceValue(6 * u.years),
        "storage_capacity": SourceValue(1 * u.TB),
        "data_replication_factor": SourceValue(3 * u.dimensionless),
        "base_storage_need": SourceValue(0 * u.TB),
        "data_storage_duration": SourceValue(5 * u.year)
    }

    @classmethod
    def ssd(cls, name="Default SSD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                160 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless),
            "base_storage_need": SourceValue(0 * u.TB),
            "data_storage_duration": SourceValue(5 * u.year)
        }
        output_args.update(kwargs)
        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless),
            "base_storage_need": SourceValue(0 * u.TB),
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
            .set_label(f"Fabrication carbon footprint of {self.name} per storage capacity"))
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity of {self.name}")
        self.data_replication_factor = data_replication_factor.set_label(f"Data replication factor of {self.name}")
        self.data_storage_duration = data_storage_duration.set_label(f"Data storage duration of {self.name}")
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")
        self.fixed_nb_of_instances = (fixed_nb_of_instances or EmptyExplainableObject()).set_label(
            f"User defined number of {self.name} instances").to(u.concurrent)
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
        return [
            "carbon_footprint_fabrication", "full_cumulative_storage_need_per_job", "full_cumulative_storage_need",
            "raw_nb_of_instances", "nb_of_instances", "instances_fabrication_footprint",
            "instances_energy", "energy_footprint",
        ] + [
            attr
            for attr in super().calculated_attributes
            if attr not in {"fabrication_impact_repartition_weights", "usage_impact_repartition_weights"}
        ]

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
            f"Carbon footprint of {self.name}")

    def update_dict_element_in_full_cumulative_storage_need_per_job(self, job: "JobBase"):
        job_storage_rate = (job.hourly_data_stored_across_usage_patterns * self.data_replication_factor).to(u.TB)
        if isinstance(job_storage_rate, EmptyExplainableObject):
            self.full_cumulative_storage_need_per_job[job] = EmptyExplainableObject(
                left_parent=job_storage_rate, label=f"Cumulative storage for {job.name} in {self.name}")
            return
        rate_array = np.copy(job_storage_rate.value.magnitude)
        rate_units = job_storage_rate.value.units
        storage_duration_in_hours = math.ceil(copy(self.data_storage_duration.to(u.hour)).magnitude)
        auto_dumps_array = -np.pad(
            job_storage_rate.value, (storage_duration_in_hours, 0), constant_values=np.float32(0)
        )[:len(rate_array)]
        delta_array = rate_array + auto_dumps_array.magnitude
        cumulative_quantity = Quantity(np.cumsum(delta_array, dtype=np.float32), rate_units)
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
                f"Full cumulative storage need for {self.name}")

    def update_raw_nb_of_instances(self):
        raw_nb_of_instances = (self.full_cumulative_storage_need / self.storage_capacity).to(u.concurrent)
        self.raw_nb_of_instances = raw_nb_of_instances.set_label(f"Hourly raw number of instances for {self.name}")

    def update_nb_of_instances(self):
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            self.nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
            return
        ceiled_nb_of_instances = self.raw_nb_of_instances.ceil()
        if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
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
            self.nb_of_instances = fixed_nb_of_instances.set_label(f"Hourly fixed number of instances for {self.name}")
        else:
            nb_of_instances = ceiled_nb_of_instances.generate_explainable_object_with_logical_dependency(
                self.fixed_nb_of_instances)
            self.nb_of_instances = nb_of_instances.set_label(f"Hourly number of instances for {self.name}")

    def update_instances_energy(self):
        self.instances_energy = EmptyExplainableObject()

    @property
    def fabrication_impact_repartition_weights(self):
        return self.full_cumulative_storage_need_per_job

    @property
    def usage_impact_repartition_weights(self):
        return self.full_cumulative_storage_need_per_job
