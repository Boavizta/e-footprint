from functools import cached_property
from typing import List, TYPE_CHECKING
from abc import abstractmethod

import numpy as np
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import (
    ExplainableHourlyQuantities, align_temporally_quantity_arrays, divide_or_fallback)
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.attribution import Atom
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.abstract_modeling_classes.source_objects import SOURCE_VALUE_DEFAULT_NAME, SourceObject
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage

if TYPE_CHECKING:
    from efootprint.core.usage.job import JobBase, DirectServerJob
    from efootprint.builders.services.service_base_class import Service


class ServerTypes:
    @classmethod
    def autoscaling(cls):
        return SourceObject("autoscaling")

    @classmethod
    def on_premise(cls):
        return SourceObject("on-premise")

    @classmethod
    def serverless(cls):
        return SourceObject("serverless")

    @classmethod
    def all(cls):
        return [cls.autoscaling(), cls.on_premise(), cls.serverless()]


def on_premise_provisioned_tier_shares(
        demand_per_job: dict, raw_nb_of_instances: np.ndarray, nb_of_tiers: int) -> dict:
    """Flat per-job weights for the on-premise provisioned stream (each instance is paid for by the jobs that
    need it, in the hours they need it). Instance tier k (k = 1..nb_of_tiers) is needed in the hours
    {h: raw[h] > k - 1}; within those hours, jobs split the tier's equal 1/nb_of_tiers slice of the provisioned
    footprint by their share of the binding demand summed over the tier's hours — so a job present only off-peak
    still pays the lower tiers it requires. A tier no hour needs (fixed_nb_of_instances above peak) falls back
    to the period-total demand shares; at zero total demand, shares are equal per job. ``demand_per_job`` values
    are plain numpy arrays aligned with ``raw_nb_of_instances``; the returned per-job floats sum to 1."""
    period_total_per_job = {job: demand.sum() for job, demand in demand_per_job.items()}
    period_total = sum(period_total_per_job.values())
    if period_total == 0:
        period_share_per_job = {job: 1 / len(demand_per_job) for job in demand_per_job}
    else:
        period_share_per_job = {job: total / period_total for job, total in period_total_per_job.items()}

    shares = {job: 0.0 for job in demand_per_job}
    for tier in range(1, nb_of_tiers + 1):
        tier_hours = raw_nb_of_instances > tier - 1
        tier_demand_per_job = {job: demand[tier_hours].sum() for job, demand in demand_per_job.items()}
        tier_demand = sum(tier_demand_per_job.values())
        for job in shares:
            tier_share = (tier_demand_per_job[job] / tier_demand if tier_demand > 0
                          else period_share_per_job[job])
            shares[job] += tier_share / nb_of_tiers

    return shares


class ServerBase(InfraHardware):
    """Abstract base for the infrastructure hardware that runs {class:Job}s as part of a digital service. Concrete subclasses model on-premise servers ({class:Server}), GPU servers ({class:GPUServer}), and cloud servers with provider-supplied hardware profiles ({class:BoaviztaCloudServer}); each rolls hourly job demand into energy and fabrication footprints according to its {param:ServerBase.server_type}."""

    @abstractmethod
    def _abc_marker(self):  # private abstract method so that this class is considered abstract
        pass

    default_values = {}

    pitfalls = (
        "{param:ServerBase.fixed_nb_of_instances} only applies when {param:ServerBase.server_type} is on-premise. "
        "Setting it on an autoscaling or serverless server has no effect; setting it too low on an on-premise "
        "server raises an error when peak demand exceeds capacity.")

    interactions = (
        "Construct the server with all required quantities, then attach jobs by passing the server to each job's "
        "constructor. The server is wired into the system through the jobs that reference it.")

    param_descriptions = {
        **InfraHardware.param_descriptions,
        "server_type": (
            "Provisioning model of the server, which decides how many instances are attributed in each hour. "
            "Autoscaling rounds the hourly demand up to a whole number of instances, so an instance is billed "
            "even when it is only partially loaded. Serverless attributes only the fractional instance-hours "
            "actually used. On-premise holds a fixed number of physical instances over the whole modeling "
            "period (capacity sized to peak demand, or to {param:ServerBase.fixed_nb_of_instances} if set)."),
        "lifespan": (
            "Expected time before the server is replaced. Embodied carbon is amortised over this duration."),
        "idle_power": (
            "Electrical power drawn by one instance that is on but not running any jobs."),
        "ram": (
            "Total memory available on one instance. Combined with {param:ServerBase.utilization_rate} to "
            "obtain the memory usable by jobs."),
        "compute": (
            "Total compute capacity available on one instance."),
        "power_usage_effectiveness": (
            "Datacenter overhead multiplier applied to instance power to account for cooling, lighting, and "
            "other site-wide energy use."),
        "average_carbon_intensity": (
            "Average grid carbon intensity at the location where the server runs, used to convert energy "
            "consumption into carbon emissions."),
        "utilization_rate": (
            "Fraction of an instance's resources that is considered usable by jobs after operating-system "
            "and headroom overhead."),
        "base_ram_consumption": (
            "Memory consumed per instance independently of jobs, for the operating system, agents, and idle "
            "services."),
        "base_compute_consumption": (
            "Compute consumed per instance independently of jobs."),
        "storage": (
            "Backing {class:Storage} attached to the server. Storage emissions are reported separately from "
            "the server's own footprint."),
        "fixed_nb_of_instances": (
            "On-premise only: number of physical machines deployed. Used to detect when traffic exceeds "
            "capacity. Leave empty for autoscaling and serverless server types."),
    }

    list_values =  {"server_type": ServerTypes.all()}

    conditional_list_values =  {
            "fixed_nb_of_instances": {
                "depends_on": "server_type",
                "conditional_list_values": {
                    ServerTypes.autoscaling(): [EmptyExplainableObject()],
                    ServerTypes.serverless(): [EmptyExplainableObject()]
                }
            }
        }

    @classmethod
    def installable_services(cls) -> List:
        from efootprint.all_classes_in_order import SERVICE_CLASSES
        installable_services = []
        for service_class in SERVICE_CLASSES:
            for installable_on_class in service_class.installable_on():
                if issubclass(cls, installable_on_class):
                    installable_services.append(service_class)
                    break

        return installable_services


    def __init__(self, name: str, server_type: ExplainableObject, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity, average_carbon_intensity: ExplainableQuantity,
                 utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self.server_type = server_type.set_label(f"Server type")
        self.idle_power = idle_power.set_label(f"Idle power")
        self.ram = ram.set_label(f"RAM").to(u.GB_ram)
        self.compute = compute.set_label("tmp label")
        self.compute.set_label(f"Nb {self.compute_type.replace("_", " ")}s")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE")
        self.average_carbon_intensity = average_carbon_intensity
        if SOURCE_VALUE_DEFAULT_NAME in self.average_carbon_intensity.label:
            self.average_carbon_intensity.set_label(f"Average carbon intensity of electricity")
        self.utilization_rate = utilization_rate.set_label("Utilization rate")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption")
        self.base_compute_consumption = base_compute_consumption.set_label(
            f"Base {self.compute_type.replace("_", " ")} consumption")
        self.fixed_nb_of_instances = (fixed_nb_of_instances or EmptyExplainableObject()).set_label(
            f"User defined number of instances").to(u.concurrent)
        self.storage = storage

        self.hour_by_hour_compute_need = EmptyExplainableObject()
        self.hour_by_hour_ram_need = EmptyExplainableObject()
        self.available_compute_per_instance = EmptyExplainableObject()
        self.available_ram_per_instance = EmptyExplainableObject()
        self.raw_nb_of_instances = EmptyExplainableObject()
        self.nb_of_instances = EmptyExplainableObject()
        self.occupied_ram_per_instance = EmptyExplainableObject()
        self.occupied_compute_per_instance = EmptyExplainableObject()
        self.idle_energy_footprint = EmptyExplainableObject()
        self.load_energy_footprint = EmptyExplainableObject()
        self.job_repartition_weights = ExplainableObjectDict()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return [self.storage]

    @property
    def compute_type(self) -> str:
        return str(self.compute.value.units)

    calculated_attributes: List[str] = [
        "hour_by_hour_ram_need",
        "hour_by_hour_compute_need",
        "occupied_ram_per_instance",
        "occupied_compute_per_instance",
        "available_ram_per_instance",
        "available_compute_per_instance",
    ] + [
        attr for attr in InfraHardware.calculated_attributes if attr != "energy_footprint"
    ] + [
        "idle_energy_footprint",
        "load_energy_footprint",
        "energy_footprint",
        "job_repartition_weights",
    ] + [
        attr
        for attr in ModelingObject.calculated_attributes
        if attr not in {"fabrication_impact_repartition_weights", "usage_impact_repartition_weights"}
    ]

    @property
    def resources_unit_dict(self):
        return {"ram": "GB_ram", "compute": self.compute_type}

    @property
    def jobs(self) -> List["JobBase"]:
        from efootprint.core.usage.job import DirectServerJob

        return (
            [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, DirectServerJob)]
            + sum([service.jobs for service in self.installed_services], [])
            )


    @property
    def installed_services(self) -> List["Service"]:
        from efootprint.builders.services.service_base_class import Service

        return [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, Service)]

    def compute_hour_by_hour_resource_need(self, resource):
        resource_unit = u(self.resources_unit_dict[resource])
        hour_by_hour_resource_needs = EmptyExplainableObject()
        for job in self.jobs:
            hour_by_hour_resource_needs += (
                    job.hourly_avg_occurrences_across_usage_patterns * getattr(job, f"{resource}_needed"))

        return hour_by_hour_resource_needs.to(resource_unit).set_label(f"Hour by hour {resource} need")

    def update_hour_by_hour_ram_need(self):
        """Hourly RAM demand placed on the server by all of its jobs combined."""
        self.hour_by_hour_ram_need = self.compute_hour_by_hour_resource_need("ram")

    def update_hour_by_hour_compute_need(self):
        """Hourly compute demand placed on the server by all of its jobs combined."""
        self.hour_by_hour_compute_need = self.compute_hour_by_hour_resource_need("compute")

    def update_occupied_ram_per_instance(self):
        """RAM that is permanently occupied on each instance, summing the server's own base consumption with the base consumption of every installed service."""
        self.occupied_ram_per_instance = (self.base_ram_consumption + sum(
            [service.base_ram_consumption for service in self.installed_services])).to(u.GB_ram).set_label(
            f"Occupied RAM per instance including services")

    def update_occupied_compute_per_instance(self):
        """Compute that is permanently occupied on each instance, summing the server's own base consumption with the base consumption of every installed service."""
        self.occupied_compute_per_instance = (self.base_compute_consumption + sum(
            [service.base_compute_consumption for service in self.installed_services])).set_label(
            f"Occupied CPU per instance including services")

    def update_available_ram_per_instance(self):
        """RAM each instance has left for jobs after applying the utilization rate and subtracting RAM occupied by installed services."""
        available_ram_per_instance_before_services_installation = (self.ram * self.utilization_rate).to(u.GB_ram)
        available_ram_per_instance = (
                available_ram_per_instance_before_services_installation - self.occupied_ram_per_instance)
        if available_ram_per_instance.value <= 0 * u.B_ram:
            raise InsufficientCapacityError(
                self, "RAM", available_ram_per_instance_before_services_installation, self.occupied_ram_per_instance)

        self.available_ram_per_instance = available_ram_per_instance.set_label(
            f"Available RAM per instance")

    def update_available_compute_per_instance(self):
        """Compute each instance has left for jobs after applying the utilization rate and subtracting compute occupied by installed services."""
        available_compute_per_instance_before_services_installation = self.compute * self.utilization_rate
        available_compute_per_instance = (
                available_compute_per_instance_before_services_installation - self.occupied_compute_per_instance)
        if available_compute_per_instance.value <= 0:
            raise InsufficientCapacityError(
                self, "compute", available_compute_per_instance_before_services_installation,
                self.occupied_compute_per_instance)

        self.available_compute_per_instance = available_compute_per_instance.set_label(
            f"Available CPU per instance")

    def update_raw_nb_of_instances(self):
        """Hourly number of instances strictly required to serve hourly demand, taking the maximum across the RAM and compute dimensions, before rounding to whole instances."""
        nb_of_servers_based_on_ram_alone = (
                self.hour_by_hour_ram_need / self.available_ram_per_instance).to(u.concurrent).set_label(
            f"Raw nb of instances based on RAM alone")
        nb_of_servers_based_on_cpu_alone = (
                self.hour_by_hour_compute_need / self.available_compute_per_instance).to(u.concurrent).set_label(
            f"Raw nb of instances based on CPU alone")

        nb_of_servers_raw = nb_of_servers_based_on_ram_alone.np_compared_with(nb_of_servers_based_on_cpu_alone, "max")

        hour_by_hour_raw_nb_of_instances = nb_of_servers_raw.set_label(
            f"Hourly raw number of instances")

        self.raw_nb_of_instances = hour_by_hour_raw_nb_of_instances

    @property
    def energy_spent_by_one_idle_instance_over_one_hour(self):
        return self.idle_power * self.power_usage_effectiveness * ExplainableQuantity(1 * u.hour, "one hour")

    @property
    def extra_energy_spent_by_one_fully_active_instance_over_one_hour(self):
        return ((self.power - self.idle_power) * self.power_usage_effectiveness
                * ExplainableQuantity(1 * u.hour, "one hour"))

    def update_instances_energy(self):
        """Hourly energy consumed by all running instances, decomposed into idle baseline energy plus the extra energy drawn while serving load, with PUE applied."""
        server_energy = (
                self.energy_spent_by_one_idle_instance_over_one_hour * self.nb_of_instances
                + self.extra_energy_spent_by_one_fully_active_instance_over_one_hour * self.raw_nb_of_instances)

        self.instances_energy = server_energy.to(u.kWh).set_label(f"Hourly energy consumed by instances")

    def update_idle_energy_footprint(self):
        """Hourly carbon emissions of the idle baseline energy drawn by all provisioned instances (idle power times PUE times number of instances times grid carbon intensity) — the usage-phase component that rides the provisioned attribution stream."""
        idle_energy_footprint = (
                self.energy_spent_by_one_idle_instance_over_one_hour * self.nb_of_instances
                * self.average_carbon_intensity)

        self.idle_energy_footprint = idle_energy_footprint.to(u.kg).set_label(f"Hourly idle energy footprint")

    def update_load_energy_footprint(self):
        """Hourly carbon emissions of the extra energy drawn while serving load (power above idle times PUE times raw number of instances times grid carbon intensity) — the usage-phase component that rides the dynamic attribution stream."""
        load_energy_footprint = (
                self.extra_energy_spent_by_one_fully_active_instance_over_one_hour * self.raw_nb_of_instances
                * self.average_carbon_intensity)

        self.load_energy_footprint = load_energy_footprint.to(u.kg).set_label(f"Hourly load energy footprint")

    def update_energy_footprint(self):
        """Hourly carbon emissions caused by the electricity consumed by the server, equal to the sum of its idle and load energy footprints."""
        self.energy_footprint = (self.idle_energy_footprint + self.load_energy_footprint).to(u.kg).set_label(
            f"Hourly energy footprint")

    def autoscaling_update_nb_of_instances(self):
        hour_by_hour_nb_of_instances = self.raw_nb_of_instances.ceil()

        self.nb_of_instances = hour_by_hour_nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of instances")

    def serverless_update_nb_of_instances(self):
        hour_by_hour_nb_of_instances = self.raw_nb_of_instances.copy()

        self.nb_of_instances = hour_by_hour_nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of instances")

    def on_premise_update_nb_of_instances(self):
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
        else:
            max_nb_of_instances = self.raw_nb_of_instances.max().ceil().to(u.concurrent)

            if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
                if max_nb_of_instances > self.fixed_nb_of_instances:
                    raise InsufficientCapacityError(
                        self, "number of instances", self.fixed_nb_of_instances, max_nb_of_instances)
                else:
                    fixed_nb_of_instances_np = Quantity(
                        np.full(len(self.raw_nb_of_instances), np.float32(self.fixed_nb_of_instances.magnitude)),
                        u.concurrent)
                    nb_of_instances = ExplainableHourlyQuantities(
                        fixed_nb_of_instances_np, self.raw_nb_of_instances.start_date, "Nb of instances",
                        left_parent=self.raw_nb_of_instances, right_parent=self.fixed_nb_of_instances)
            else:
                nb_of_instances_np = Quantity(
                    np.float32(max_nb_of_instances.magnitude) * np.ones(len(self.raw_nb_of_instances), dtype=np.float32),
                    u.concurrent)

                nb_of_instances = ExplainableHourlyQuantities(
                    nb_of_instances_np, self.raw_nb_of_instances.start_date,f"Hourly number of instances",
                    left_parent=self.raw_nb_of_instances, right_parent=self.fixed_nb_of_instances,
                    operator="depending on not being empty")

        self.nb_of_instances = nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of instances")

    def update_nb_of_instances(self):
        """Hourly number of instances actually billed, computed differently per server type: ceiled to whole instances for autoscaling, mirrored from raw demand for serverless, and held flat at peak (or the user-fixed count) for on-premise."""
        logic_mapping = {
            ServerTypes.autoscaling(): self.autoscaling_update_nb_of_instances,
            ServerTypes.on_premise(): self.on_premise_update_nb_of_instances,
            ServerTypes.serverless(): self.serverless_update_nb_of_instances
        }
        logic_mapping[self.server_type]()

    @cached_property
    def service_total_job_volumes(self) -> dict:
        """Total hourly volume of jobs going through each installed service, used to attribute each service's
        standing base consumption to its own jobs proportionally to their volumes (attribution-only, lazy)."""
        return {
            service: sum(
                (job.hourly_avg_occurrences_across_usage_patterns for job in service.jobs),
                start=EmptyExplainableObject()
            ).set_label(f"Total job volume for {service.name}")
            for service in self.installed_services}

    def update_dict_element_in_job_repartition_weights(self, job: "JobBase"):
        from efootprint.core.usage.job import DirectServerJob
        if isinstance(job, DirectServerJob):
            weight = (
                    ((job.compute_needed / job.server.compute) + (job.ram_needed / job.server.ram))
                    * job.hourly_avg_occurrences_across_usage_patterns)
        else:
            from efootprint.builders.services.service_job_base_class import ServiceJob
            assert isinstance(job, ServiceJob)
            if isinstance(job.hourly_avg_occurrences_across_usage_patterns, EmptyExplainableObject):
                weight = job.hourly_avg_occurrences_across_usage_patterns.copy()
            else:
                service = job.service
                service_base_weight = (
                    ((service.base_compute_consumption / self.compute) + (service.base_ram_consumption / self.ram))
                    * self.nb_of_instances)
                # Summed inline (not via the lazy service_total_job_volumes cached property): this eager update
                # runs before the ModelingUpdate flush, so a cached value materialized by a prior attribution
                # query would be stale. Zero service-total at a given hour means no jobs run on the service then;
                # the base load attributed to this job is therefore 0 at those hours.
                service_total_job_volume = sum(
                    (service_job.hourly_avg_occurrences_across_usage_patterns for service_job in service.jobs),
                    start=EmptyExplainableObject())
                job_volume_share = divide_or_fallback(
                    job.hourly_avg_occurrences_across_usage_patterns, service_total_job_volume, fallback=0)
                weight = (
                    service_base_weight * job_volume_share
                    + ((job.compute_needed / self.compute) + (job.ram_needed / self.ram))
                    * job.hourly_avg_occurrences_across_usage_patterns)

        self.job_repartition_weights[job] = weight.to(u.concurrent).set_label(
            f"{job.name} weight in impact repartition"
        )

    def update_job_repartition_weights(self):
        """Per-job weight used to attribute the server's fabrication and energy footprint back to its jobs, proportional to each job's share of compute and RAM consumption over the modeling period."""
        self.job_repartition_weights = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_job_repartition_weights(job)

    @property
    def fabrication_impact_repartition_weights(self):
        return self.job_repartition_weights

    @property
    def usage_impact_repartition_weights(self):
        return self.job_repartition_weights

    # --- Attribution-only binding-resource physics and atom builder (lazy cached properties, consumed only by
    # the attribution layer, never by the eager calculated-attribute graph) ---

    @property
    def is_on_premise(self) -> bool:
        return self.server_type == ServerTypes.on_premise()

    @cached_property
    def binding_demand_per_job(self) -> dict:
        """Each job's hourly demand on the server's binding resource, the resource picked per hour by
        raw[h] = max(compute_need[h] / available_compute_per_instance, ram_need[h] / available_ram_per_instance)
        — the same denominators as update_raw_nb_of_instances, so attribution charges the resource that actually
        drives the instance count. A ServiceJob additionally carries its volume share of its service's standing
        base consumption (a service's reservation is paid by that service's own jobs)."""
        from efootprint.builders.services.service_job_base_class import ServiceJob

        compute_pressure = self.hour_by_hour_compute_need / self.available_compute_per_instance
        ram_pressure = self.hour_by_hour_ram_need / self.available_ram_per_instance
        if isinstance(compute_pressure, EmptyExplainableObject) or isinstance(ram_pressure, EmptyExplainableObject):
            return {job: EmptyExplainableObject() for job in self.jobs}

        compute_binds_np = (
                compute_pressure.to(u.concurrent).magnitude >= ram_pressure.to(u.concurrent).magnitude
        ).astype(np.float32)
        compute_binds = ExplainableHourlyQuantities(
            Quantity(compute_binds_np, u.dimensionless), compute_pressure.start_date,
            left_parent=compute_pressure, right_parent=ram_pressure, operator="binding-resource selection between")
        ram_binds = ExplainableHourlyQuantities(
            Quantity(1 - compute_binds_np, u.dimensionless), compute_pressure.start_date,
            left_parent=compute_pressure, right_parent=ram_pressure, operator="binding-resource selection between")

        binding_demand_per_job = {}
        for job in self.jobs:
            occurrences = job.hourly_avg_occurrences_across_usage_patterns
            demand = (
                (job.compute_needed / self.available_compute_per_instance).to(u.dimensionless) * compute_binds
                + (job.ram_needed / self.available_ram_per_instance).to(u.dimensionless) * ram_binds
            ) * occurrences
            if isinstance(job, ServiceJob) and not isinstance(occurrences, EmptyExplainableObject):
                service = job.service
                service_base_pressure = (
                    (service.base_compute_consumption / self.available_compute_per_instance).to(u.dimensionless)
                    * compute_binds
                    + (service.base_ram_consumption / self.available_ram_per_instance).to(u.dimensionless)
                    * ram_binds)
                job_volume_share = divide_or_fallback(
                    occurrences, self.service_total_job_volumes[service], fallback=0)
                demand = demand + service_base_pressure * self.nb_of_instances * job_volume_share
            binding_demand_per_job[job] = demand.to(u.concurrent).set_label(
                f"{job.name} binding-resource demand on {self.name}")

        return binding_demand_per_job

    @cached_property
    def dynamic_share_per_job(self) -> dict:
        """Each job's hourly share of the total binding-resource demand, divide_or_fallback(fallback=0) —
        exact for the demand streams: zero demand at an hour means zero dynamic footprint at that hour."""
        total_demand = sum(self.binding_demand_per_job.values(), start=EmptyExplainableObject())
        return {
            job: (EmptyExplainableObject()
                  if isinstance(demand, EmptyExplainableObject) or isinstance(total_demand, EmptyExplainableObject)
                  else divide_or_fallback(demand, total_demand, fallback=0))
            for job, demand in self.binding_demand_per_job.items()}

    @cached_property
    def provisioned_share_per_job(self) -> dict:
        """Per-job weights for the provisioned stream (fabrication + idle energy, both proportional to
        nb_of_instances). On-premise provisions once for the whole period, so the weights are flat scalars from
        the per-tier helper on_premise_provisioned_tier_shares; autoscaling and serverless re-provision hourly,
        so the weights collapse to dynamic_share_per_job."""
        if not self.is_on_premise or isinstance(self.nb_of_instances, EmptyExplainableObject):
            return self.dynamic_share_per_job
        nb_of_tiers = int(round(self.nb_of_instances.max().magnitude))
        if nb_of_tiers == 0 or not self.jobs:
            return self.dynamic_share_per_job

        raw_nb_of_instances_np = self.raw_nb_of_instances.magnitude
        demand_per_job_np = {}
        for job, demand in self.binding_demand_per_job.items():
            if isinstance(demand, EmptyExplainableObject):
                demand_per_job_np[job] = np.zeros_like(raw_nb_of_instances_np)
            else:
                aligned_demand, _, _ = align_temporally_quantity_arrays(
                    demand.value, demand.start_date,
                    self.raw_nb_of_instances.value, self.raw_nb_of_instances.start_date)
                demand_per_job_np[job] = aligned_demand
        tier_shares = on_premise_provisioned_tier_shares(demand_per_job_np, raw_nb_of_instances_np, nb_of_tiers)

        return {
            job: ExplainableQuantity(
                share * u.dimensionless, f"{job.name} flat share of {self.name} provisioned footprint",
                left_parent=self.raw_nb_of_instances, operator="per-tier provisioned weight derived from")
            for job, share in tier_shares.items()}

    def attribution_atoms(self, phase: LifeCyclePhases):
        """One atom per (stream, job, containment cell): the fabrication phase carries the provisioned stream
        over instances_fabrication_footprint; the usage phase carries the provisioned stream over
        idle_energy_footprint plus the dynamic stream over load_energy_footprint. The job weight is the
        stream's share (provisioned_share_per_job / dynamic_share_per_job) and the cell share is flat for the
        on-premise provisioned stream (always-on: it carries footprint at idle hours) and hourly otherwise."""
        if phase == LifeCyclePhases.MANUFACTURING:
            streams = [("provisioned", self.instances_fabrication_footprint)]
        else:
            streams = [("provisioned", self.idle_energy_footprint), ("dynamic", self.load_energy_footprint)]

        for stream, stream_footprint in streams:
            job_weights = self.provisioned_share_per_job if stream == "provisioned" else self.dynamic_share_per_job
            for job in self.jobs:
                job_weight = job_weights[job]
                for cell in job.attribution_cells:
                    cell_share = (cell.flat_share if stream == "provisioned" and self.is_on_premise
                                  else cell.hourly_share)
                    location = cell.step.name if cell.step is not None else f"{cell.rsn.name} via {cell.ef.name}"
                    yield Atom(
                        source=self, stream=stream, job=job, up=cell.up, step=cell.step, rsn=cell.rsn, ef=cell.ef,
                        value=(stream_footprint * job_weight * cell_share).to(u.kg).set_label(
                            f"{self.name} {stream} {phase.value.lower()} footprint via {job.name} "
                            f"in {location} ({cell.up.name})"))
