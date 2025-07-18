import math
from typing import List, Type

import numpy as np
from pint import Quantity

from efootprint.constants.sources import Sources
from efootprint.core.hardware.infra_hardware import InfraHardware, InsufficientCapacityError
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class NegativeCumulativeStorageNeedError(Exception):
    def __init__(self, storage_obj: Type["Storage"], cumulative_quantity: Quantity):
        self.storage_obj = storage_obj
        self.cumulative_quantity = cumulative_quantity
        self.jobs_that_delete_data = [job for job in self.storage_obj.jobs if job.data_stored.magnitude < 0]

        job_msg_part = [f"name: {job.name} - value: {job.data_stored}" for job in self.jobs_that_delete_data]

        message = (
            f"In Storage object {self.storage_obj.name}, negative cumulative storage need detected: "
            f"{np.min(cumulative_quantity):~P}. Please verify your jobs that delete data: {job_msg_part} "
            f"or increase the base_storage_need value, currently set to {self.storage_obj.base_storage_need.value}")
        super().__init__(message)


class Storage(InfraHardware):
    default_values =  {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(160 * u.kg / u.TB),
            "power_per_storage_capacity": SourceValue(1.3 * u.W / u.TB),
            "lifespan": SourceValue(6 * u.years),
            "idle_power": SourceValue(0 * u.W),
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
            "power_per_storage_capacity": SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(6 * u.years, Sources.HYPOTHESIS),
            "idle_power": SourceValue(0 * u.W, Sources.HYPOTHESIS),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            "base_storage_need": SourceValue(0 * u.TB, Sources.HYPOTHESIS),
            "data_storage_duration": SourceValue(5 * u.year, Sources.HYPOTHESIS)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def hdd(cls, name="Default HDD storage", **kwargs):
        output_args = {
            "carbon_footprint_fabrication_per_storage_capacity": SourceValue(
                20 * u.kg / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "power_per_storage_capacity": SourceValue(4.2 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "lifespan": SourceValue(4 * u.years, Sources.HYPOTHESIS),
            "idle_power": SourceValue(0 * u.W, Sources.HYPOTHESIS),
            "storage_capacity": SourceValue(1 * u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY),
            "data_replication_factor": SourceValue(3 * u.dimensionless, Sources.HYPOTHESIS),
            "base_storage_need": SourceValue(0 * u.TB, Sources.HYPOTHESIS),
            "data_storage_duration": SourceValue(5 * u.year, Sources.HYPOTHESIS)
        }

        output_args.update(kwargs)

        return cls(name, **output_args)

    @classmethod
    def archetypes(cls):
        return [cls.ssd, cls.hdd]

    def __init__(self, name: str, storage_capacity: ExplainableQuantity,
                 carbon_footprint_fabrication_per_storage_capacity: ExplainableQuantity,
                 power_per_storage_capacity: ExplainableQuantity, idle_power: ExplainableQuantity,
                 data_replication_factor: ExplainableQuantity, data_storage_duration: ExplainableQuantity,
                 base_storage_need: ExplainableQuantity, lifespan: ExplainableQuantity,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(
            name, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W), lifespan=lifespan)
        self.carbon_footprint_fabrication_per_storage_capacity = (carbon_footprint_fabrication_per_storage_capacity
        .set_label(f"Fabrication carbon footprint of {self.name} per storage capacity"))
        self.power_per_storage_capacity = power_per_storage_capacity.set_label(
            f"Power of {self.name} per storage capacity")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity of {self.name}")
        self.data_replication_factor = data_replication_factor.set_label(f"Data replication factor of {self.name}")
        self.data_storage_duration = data_storage_duration.set_label(f"Data storage duration of {self.name}")
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")
        self.fixed_nb_of_instances = (fixed_nb_of_instances or EmptyExplainableObject()).set_label(
            f"User defined number of {self.name} instances").to(u.dimensionless)
        self.storage_delta = EmptyExplainableObject()
        self.full_cumulative_storage_need = EmptyExplainableObject()
        self.nb_of_active_instances = EmptyExplainableObject()
        self.storage_needed = EmptyExplainableObject()
        self.storage_freed = EmptyExplainableObject()
        self.automatic_storage_dumps_after_storage_duration = EmptyExplainableObject()

    @property
    def server(self) -> Type["Server"]:
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
        return (
            ["carbon_footprint_fabrication", "power", "storage_needed", "storage_freed",
             "automatic_storage_dumps_after_storage_duration", "storage_delta", "full_cumulative_storage_need",
             "raw_nb_of_instances", "nb_of_instances", "nb_of_active_instances", "instances_fabrication_footprint",
             "instances_energy", "energy_footprint"])

    @property
    def jobs(self) -> List[Type["Job"]]:
        return list(set(
            job for serv in self.modeling_obj_containers for job in serv.jobs
        ))

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

    def update_power(self):
        self.power = (self.power_per_storage_capacity * self.storage_capacity).set_label(f"Power of {self.name}")

    def update_storage_needed(self):
        storage_needed = EmptyExplainableObject()

        for job in self.jobs:
            if job.data_stored.magnitude >= 0:
                storage_needed += job.hourly_data_stored_across_usage_patterns
            else:
                # Necessary to keep relationship in calculation graph.
                # For example if the data_stored attribute of a job went from negative to positive then the
                # storage_needed needs to be recomputed but wouldn’t have been initially logically linked to the job
                # with the above if condition.
                storage_needed = storage_needed.generate_explainable_object_with_logical_dependency(
                    job.hourly_data_stored_across_usage_patterns)

        storage_needed *= self.data_replication_factor

        self.storage_needed = storage_needed.to(u.TB).set_label(f"Hourly {self.name} storage need")

    def update_storage_freed(self):
        storage_freed = EmptyExplainableObject()

        for job in self.jobs:
            if job.data_stored.magnitude < 0:
                storage_freed += job.hourly_data_stored_across_usage_patterns
            else:
                storage_freed = storage_freed.generate_explainable_object_with_logical_dependency(
                    job.hourly_data_stored_across_usage_patterns)

        storage_freed *= self.data_replication_factor

        self.storage_freed = storage_freed.to(u.TB).set_label(f"Hourly {self.name} storage freed")

    def update_automatic_storage_dumps_after_storage_duration(self):
        if isinstance(self.storage_needed, EmptyExplainableObject):
            automatic_storage_dumps_after_storage_duration = EmptyExplainableObject(left_parent=self.storage_needed)
        else:
            storage_needs_nb_of_hours = len(self.storage_needed.value)
            if storage_needs_nb_of_hours == 0:
                automatic_storage_dumps_after_storage_duration_np = Quantity(
                    np.zeros(storage_needs_nb_of_hours + 1, dtype=np.float32),
                    self.storage_needed.units)
            else:
                storage_duration_in_hours = math.ceil(self.data_storage_duration.to(u.hour).magnitude)
                automatic_storage_dumps_after_storage_duration_np = - np.pad(
                    self.storage_needed.value, (storage_duration_in_hours, 0), constant_values=np.float32(0)
                )[:storage_needs_nb_of_hours]

            automatic_storage_dumps_after_storage_duration = ExplainableHourlyQuantities(
                automatic_storage_dumps_after_storage_duration_np, self.storage_needed.start_date,
                label=f"Storage dumps for {self.name}",
                left_parent=self.storage_needed,
                right_parent=self.data_storage_duration, operator="shift by storage duration and negate")

        self.automatic_storage_dumps_after_storage_duration = automatic_storage_dumps_after_storage_duration

    def update_storage_delta(self):
        storage_delta = (self.storage_needed + self.storage_freed
                         + self.automatic_storage_dumps_after_storage_duration)

        self.storage_delta = storage_delta.set_label(f"Hourly storage delta for {self.name}")

    def update_full_cumulative_storage_need(self):
        if isinstance(self.storage_delta, EmptyExplainableObject):
            self.full_cumulative_storage_need = EmptyExplainableObject(left_parent=self.storage_delta)
        else:
            delta_array = np.copy(self.storage_delta.value.magnitude)
            delta_unit = self.storage_delta.value.units

            # Add base storage need to first hour
            delta_array[0] += self.base_storage_need.value.to(delta_unit).magnitude

            # Compute cumulative storage
            cumulative_array = np.cumsum(delta_array, dtype=np.float32)
            cumulative_quantity = Quantity(cumulative_array, delta_unit)

            if np.min(cumulative_quantity.magnitude) < 0:
                raise NegativeCumulativeStorageNeedError(self, cumulative_quantity)

            self.full_cumulative_storage_need = ExplainableHourlyQuantities(
                cumulative_quantity,
                start_date=self.storage_delta.start_date,
                label=f"Full cumulative storage need for {self.name}",
                left_parent=self.storage_delta,
                right_parent=self.base_storage_need,
                operator="cumulative sum of storage delta with initial storage need"
            )

    def update_raw_nb_of_instances(self):
        raw_nb_of_instances = (self.full_cumulative_storage_need / self.storage_capacity).to(u.dimensionless)

        self.raw_nb_of_instances = raw_nb_of_instances.set_label(f"Hourly raw number of instances for {self.name}")

    def update_nb_of_instances(self):
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            self.nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
        else:
            nb_of_instances = self.raw_nb_of_instances.ceil()

            if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
                max_nb_of_instances = nb_of_instances.max()
                if max_nb_of_instances > self.fixed_nb_of_instances:
                    raise InsufficientCapacityError(
                        self, "number of instances", self.fixed_nb_of_instances, max_nb_of_instances)
                else:
                    fixed_nb_of_instances_quantity = Quantity(
                        np.full(
                            len(self.raw_nb_of_instances),
                            np.float32(self.fixed_nb_of_instances.to(u.dimensionless).magnitude)
                        ),
                        u.dimensionless)
                    fixed_nb_of_instances = ExplainableHourlyQuantities(
                        fixed_nb_of_instances_quantity, self.raw_nb_of_instances.start_date,"Nb of instances",
                        left_parent=self.raw_nb_of_instances, right_parent=self.fixed_nb_of_instances)
                self.nb_of_instances = fixed_nb_of_instances.set_label(
                    f"Hourly fixed number of instances for {self.name}")
            else:
                nb_of_instances = ExplainableHourlyQuantities(
                    nb_of_instances.value, self.raw_nb_of_instances.start_date, left_parent=nb_of_instances,
                    right_parent=self.fixed_nb_of_instances, operator="depending on being empty")
                self.nb_of_instances = nb_of_instances.set_label(f"Hourly number of instances for {self.name}")

    def update_nb_of_active_instances(self):
        storage_needed = self.storage_needed
        tmp_nb_of_active_instances = (
                (storage_needed.abs().np_compared_with(self.storage_freed.abs(), "max")
                 + self.automatic_storage_dumps_after_storage_duration.abs())
                / self.storage_capacity
        ).to(u.dimensionless)
        nb_of_active_instances = tmp_nb_of_active_instances.np_compared_with(self.nb_of_instances.abs(), "min")
        self.nb_of_active_instances = nb_of_active_instances.set_label(
            f"Hourly number of active instances for {self.name}")

    def update_instances_energy(self):
        nb_of_idle_instances = (self.nb_of_instances - self.nb_of_active_instances).set_label(
            f"Hourly number of idle instances for {self.name}")
        active_storage_energy = (
                self.nb_of_active_instances * self.power * ExplainableQuantity(
            1 * u.hour, "one hour") * self.power_usage_effectiveness
        ).set_label(f"Hourly active instances energy for {self.name}")
        idle_storage_energy = (
                nb_of_idle_instances * self.idle_power * ExplainableQuantity(
            1 * u.hour, "one hour") * self.power_usage_effectiveness
        ).set_label(f"Hourly idle instances energy for {self.name}")

        storage_energy = (active_storage_energy + idle_storage_energy)

        self.instances_energy = storage_energy.to(u.kWh).set_label(f"Storage energy for {self.name}")
