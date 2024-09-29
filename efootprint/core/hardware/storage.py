import math

from efootprint.builders.time_builders import create_hourly_usage_df_from_list
from efootprint.core.hardware.hardware_base_classes import InfraHardware
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, ExplainableHourlyQuantities, \
    EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u


class Storage(InfraHardware):
    def __init__(self, name: str, carbon_footprint_fabrication: SourceValue, power: SourceValue,
                 lifespan: SourceValue, idle_power: SourceValue, storage_capacity: SourceValue,
                 power_usage_effectiveness: SourceValue, average_carbon_intensity: SourceValue,
                 data_replication_factor: SourceValue, data_storage_duration: SourceValue,
                 base_storage_need: SourceValue):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan, average_carbon_intensity)
        self.storage_delta = EmptyExplainableObject()
        self.full_cumulative_storage_need = EmptyExplainableObject()
        self.long_term_storage_required = EmptyExplainableObject()
        self.nb_of_active_instances = EmptyExplainableObject()
        self.instances_power = EmptyExplainableObject()
        if not idle_power.value.check("[power]"):
            raise ValueError("Value of variable 'idle_power' does not have appropriate power dimensionality")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        if not storage_capacity.value.check("[]"):
            raise ValueError("Value of variable 'storage_capacity' does not have appropriate [] dimensionality")
        self.storage_capacity = storage_capacity.set_label(f"Storage capacity of {self.name}")
        if not power_usage_effectiveness.value.check("[]"):
            raise ValueError(
                "Value of variable 'power_usage_effectiveness' does not have appropriate [] dimensionality")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE of {self.name}")
        if not data_replication_factor.value.check("[]"):
            raise ValueError("Value of variable 'data_replication_factor' does not have appropriate [] dimensionality")
        self.data_replication_factor = data_replication_factor.set_label(f"Data replication factor of {self.name}")
        if not data_storage_duration.value.check("[time]"):
            raise ValueError("Value of variable 'data_storage_duration' does not have appropriate time dimensionality")
        self.data_storage_duration = data_storage_duration.set_label(f"Data storage duration of {self.name}")
        if not base_storage_need.value.check("[]"):
            raise ValueError(
                "Value of variable 'storage_need_from_previous_year' does not have the appropriate"
                " '[]' dimensionality")
        self.base_storage_need = base_storage_need.set_label(f"{self.name} initial storage need")

    @property
    def calculated_attributes(self):
        return (
            ["storage_delta", "full_cumulative_storage_need", "raw_nb_of_instances", "nb_of_instances",
             "nb_of_active_instances","instances_fabrication_footprint", "instances_energy","energy_footprint"])


    @property
    def jobs(self):
        return self.modeling_obj_containers

    # If storage_needed, storage_freed and automatic_storage_dumps_after_storage_duration had their update function
    # and were attributes of the storage class then the update of the data_stored attribute of a job from positive to
    # negative or negative to positive would cause problem with the re-computation of modeling attributes.
    # For example if the data_stored attribute of a job went from negative to positive then the storage_freed would be
    # recomputed but not the storage_needed nor the automatic_storage_dumps_after_storage_duration.
    # By turning these three attributes into properties, we make all of them dependencies of the calculation of
    # storage_delta and solve the problem.
    @property
    def storage_needed(self):
        storage_needed = EmptyExplainableObject()

        for job in self.jobs:
            if job.data_stored.magnitude >= 0:
                storage_needed += job.hourly_data_stored_across_usage_patterns

        storage_needed *= self.data_replication_factor

        return storage_needed.to(u.TB).set_label(f"Hourly {self.name} storage need")

    @property
    def storage_freed(self):
        storage_freed = EmptyExplainableObject()

        for job in self.jobs:
            if job.data_stored.magnitude < 0:
                storage_freed += job.hourly_data_stored_across_usage_patterns

        storage_freed *= self.data_replication_factor

        return storage_freed.to(u.TB).set_label(f"Hourly {self.name} storage freed")

    @property
    def automatic_storage_dumps_after_storage_duration(self):
        if isinstance(self.storage_needed, EmptyExplainableObject):
            return EmptyExplainableObject()
        else:
            storage_duration_in_hours = math.ceil(self.data_storage_duration.to(u.hour).magnitude)
            automatic_storage_dumps_after_storage_duration_df = - self.storage_needed.value.copy().shift(
                periods=storage_duration_in_hours, freq='h')
            automatic_storage_dumps_after_storage_duration_df = automatic_storage_dumps_after_storage_duration_df[
                automatic_storage_dumps_after_storage_duration_df.index <= self.storage_needed.value.index.max()]

            if len(automatic_storage_dumps_after_storage_duration_df) == 0:
                storage_needs_start_date = self.storage_needed.value.index.min().to_timestamp()
                storage_needs_end_date = self.storage_needed.value.index.max().to_timestamp()
                storage_needs_nb_of_hours = int((storage_needs_end_date - storage_needs_start_date).seconds / 3600)
                automatic_storage_dumps_after_storage_duration_df = create_hourly_usage_df_from_list(
                    [0] * (storage_needs_nb_of_hours + 1), start_date=storage_needs_start_date)

            return ExplainableHourlyQuantities(
                automatic_storage_dumps_after_storage_duration_df, label=f"Storage dumps for {self.name}",
                left_parent=self.storage_needed,
                right_parent=self.data_storage_duration, operator="shift by storage duration and negate")

    def update_storage_delta(self):
        storage_delta = (self.storage_needed + self.storage_freed
                         + self.automatic_storage_dumps_after_storage_duration)

        self.storage_delta = storage_delta.set_label(f"Hourly storage delta for {self.name}")

    def update_full_cumulative_storage_need(self):
        if isinstance(self.storage_delta, EmptyExplainableObject):
            self.full_cumulative_storage_need = EmptyExplainableObject()
        else:
            storage_delta_df = self.storage_delta.value.copy()
            storage_delta_df.iat[0, 0] += self.base_storage_need.value
            full_cumulative_storage_need = storage_delta_df.cumsum()

            if full_cumulative_storage_need.value.min().magnitude < 0:
                jobs_in_errors = [
                    f"name: {job.name} - value: {job.data_stored}"
                    for job in self.jobs if job.data_stored.magnitude < 0]
                raise ValueError(
                    f"In Storage object {self.name}, negative cumulative storage need detected: "
                    f"{full_cumulative_storage_need.min().value}."
                    f"Please verify your jobs that delete data: {jobs_in_errors}"
                    f" or increase the base_storage_need value, currently set to {self.base_storage_need.value}"
                )

            self.full_cumulative_storage_need = ExplainableHourlyQuantities(
                full_cumulative_storage_need, label=f"Full cumulative storage need for {self.name}",
                left_parent=self.storage_delta, right_parent=self.base_storage_need,
                operator="cumulative sum of storage delta with initial storage need")

    def update_raw_nb_of_instances(self):
        raw_nb_of_instances = (self.full_cumulative_storage_need / self.storage_capacity).to(u.dimensionless)

        self.raw_nb_of_instances = raw_nb_of_instances.set_label(f"Hourly raw number of instances for {self.name}")

    def update_nb_of_instances(self):
        nb_of_instances = self.raw_nb_of_instances.ceil()

        self.nb_of_instances = nb_of_instances.set_label(f"Hourly number of instances for {self.name}")

    def update_nb_of_active_instances(self):
        tmp_nb_of_active_instances = (
                (self.storage_needed.abs().np_compared_with(self.storage_freed.abs(), "max")
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

        self.instances_energy = storage_energy.set_label(f"Storage energy for {self.name}")