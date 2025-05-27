from abc import abstractmethod
from typing import List

import numpy as np
import pandas as pd
import pint_pandas

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.infra_hardware import InfraHardware
from efootprint.abstract_modeling_classes.source_objects import SOURCE_VALUE_DEFAULT_NAME, SourceObject
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage


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


class ServerBase(InfraHardware):
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    @classmethod
    def list_values(cls):
        return {"server_type": ServerTypes.all()}

    @classmethod
    def conditional_list_values(cls):
        return {
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
        from efootprint.core.all_classes_in_order import SERVICE_CLASSES
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
                 server_utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject = None):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self.hour_by_hour_compute_need = EmptyExplainableObject()
        self.hour_by_hour_ram_need = EmptyExplainableObject()
        self.available_compute_per_instance = EmptyExplainableObject()
        self.available_ram_per_instance = EmptyExplainableObject()
        self.raw_nb_of_instances = EmptyExplainableObject()
        self.nb_of_instances = EmptyExplainableObject()
        self.occupied_ram_per_instance = EmptyExplainableObject()
        self.occupied_compute_per_instance = EmptyExplainableObject()
        self.server_type = server_type.set_label(f"Server type of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.ram = ram.set_label(f"RAM of {self.name}")
        self.compute = compute.set_label("tmp label")
        self.compute.set_label(f"Nb {self.compute_type.replace("_", " ")}s of {self.name}")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE of {self.name}")
        self.average_carbon_intensity = average_carbon_intensity
        if SOURCE_VALUE_DEFAULT_NAME in self.average_carbon_intensity.label:
            self.average_carbon_intensity.set_label(f"Average carbon intensity of {self.name} electricity")
        self.server_utilization_rate = server_utilization_rate.set_label(f"{self.name} utilization rate")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")
        self.base_compute_consumption = base_compute_consumption.set_label(
            f"Base {self.compute_type.replace("_", " ")} consumption of {self.name}")
        self.fixed_nb_of_instances = (fixed_nb_of_instances or EmptyExplainableObject()).set_label(
            f"User defined number of {self.name} instances").to(u.dimensionless)
        self.storage = storage
        
    @property
    def compute_type(self) -> str:
        return str(self.compute.value.units)

    @property
    def calculated_attributes(self):
        return ["hour_by_hour_ram_need", "hour_by_hour_compute_need",
                "occupied_ram_per_instance", "occupied_compute_per_instance",
                "available_ram_per_instance", "available_compute_per_instance",
                "raw_nb_of_instances", "nb_of_instances",
                "instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    @property
    def resources_unit_dict(self):
        return {"ram": "GB", "compute": self.compute_type}

    @property
    def jobs(self) -> List[ModelingObject]:
        from efootprint.core.usage.job import JobBase

        return (
            [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, JobBase)]
            + sum([service.jobs for service in self.installed_services], [])
            )


    @property
    def installed_services(self) -> List[ModelingObject]:
        from efootprint.builders.services.service_base_class import Service

        return [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, Service)]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return [self.storage]

    def compute_hour_by_hour_resource_need(self, resource):
        resource_unit = u(self.resources_unit_dict[resource])
        hour_by_hour_resource_needs = EmptyExplainableObject()
        for job in self.jobs:
            hour_by_hour_resource_needs += (
                    job.hourly_avg_occurrences_across_usage_patterns * getattr(job, f"{resource}_needed"))

        return hour_by_hour_resource_needs.to(resource_unit).set_label(f"{self.name} hour by hour {resource} need")

    def update_hour_by_hour_ram_need(self):
        self.hour_by_hour_ram_need = self.compute_hour_by_hour_resource_need("ram")

    def update_hour_by_hour_compute_need(self):
        self.hour_by_hour_compute_need = self.compute_hour_by_hour_resource_need("compute")

    def update_occupied_ram_per_instance(self):
        self.occupied_ram_per_instance = (self.base_ram_consumption + sum(
            [service.base_ram_consumption for service in self.installed_services])).set_label(
            f"Occupied RAM per {self.name} instance including services")

    def update_occupied_compute_per_instance(self):
        self.occupied_compute_per_instance = (self.base_compute_consumption + sum(
            [service.base_compute_consumption for service in self.installed_services])).set_label(
            f"Occupied CPU per {self.name} instance including services")

    def update_available_ram_per_instance(self):
        available_ram_per_instance = self.ram * self.server_utilization_rate
        available_ram_per_instance -= self.occupied_ram_per_instance
        if available_ram_per_instance.value < 0 * u.B:
            raise ValueError(
                f"{self.name} has available capacity of {(self.ram * self.server_utilization_rate).value} "
                f" but is asked {self.occupied_ram_per_instance.value}")

        self.available_ram_per_instance = available_ram_per_instance.set_label(
            f"Available RAM per {self.name} instance")

    def update_available_compute_per_instance(self):
        available_compute_per_instance = self.compute * self.server_utilization_rate
        available_compute_per_instance -= self.occupied_compute_per_instance
        if available_compute_per_instance.value < 0:
            raise ValueError(
                f"server has available capacity of {(self.compute * self.server_utilization_rate).value} "
                f" but is asked {self.occupied_compute_per_instance.value}")

        self.available_compute_per_instance = available_compute_per_instance.set_label(
            f"Available CPU per {self.name} instance")

    def update_raw_nb_of_instances(self):
        nb_of_servers_based_on_ram_alone = (
                self.hour_by_hour_ram_need / self.available_ram_per_instance).to(u.dimensionless).set_label(
            f"Raw nb of {self.name} instances based on RAM alone")
        nb_of_servers_based_on_cpu_alone = (
                self.hour_by_hour_compute_need / self.available_compute_per_instance).to(u.dimensionless).set_label(
            f"Raw nb of {self.name} instances based on CPU alone")

        nb_of_servers_raw = nb_of_servers_based_on_ram_alone.np_compared_with(nb_of_servers_based_on_cpu_alone, "max")

        hour_by_hour_raw_nb_of_instances = nb_of_servers_raw.set_label(
            f"Hourly raw number of {self.name} instances")

        self.raw_nb_of_instances = hour_by_hour_raw_nb_of_instances

    def update_instances_energy(self):
        energy_spent_by_one_idle_instance_over_one_hour = (
                self.idle_power * self.power_usage_effectiveness * ExplainableQuantity(1 * u.hour, "one hour"))
        extra_energy_spent_by_one_fully_active_instance_over_one_hour = (
                (self.power - self.idle_power) * self.power_usage_effectiveness
                * ExplainableQuantity(1 * u.hour, "one hour"))

        server_power = (
                energy_spent_by_one_idle_instance_over_one_hour * self.nb_of_instances
                + extra_energy_spent_by_one_fully_active_instance_over_one_hour * self.raw_nb_of_instances)

        self.instances_energy = server_power.to(u.kWh).set_label(
            f"Hourly energy consumed by {self.name} instances")

    def autoscaling_update_nb_of_instances(self):
        hour_by_hour_nb_of_instances = self.raw_nb_of_instances.ceil()

        self.nb_of_instances = hour_by_hour_nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of {self.name} instances")

    def serverless_update_nb_of_instances(self):
        hour_by_hour_nb_of_instances = self.raw_nb_of_instances.copy()

        self.nb_of_instances = hour_by_hour_nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of {self.name} instances")

    def on_premise_update_nb_of_instances(self):
        if isinstance(self.raw_nb_of_instances, EmptyExplainableObject):
            nb_of_instances = EmptyExplainableObject(left_parent=self.raw_nb_of_instances)
        else:
            max_nb_of_instances = self.raw_nb_of_instances.max().ceil().to(u.dimensionless)

            if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
                if max_nb_of_instances > self.fixed_nb_of_instances:
                    raise ValueError(
                        f"The number of {self.name} instances computed from its resources need is superior to the "
                        f"number of instances specified by the user "
                        f"({max_nb_of_instances.value} > {self.fixed_nb_of_instances})")
                else:
                    fixed_nb_of_instances_df = pd.DataFrame(
                        {"value": pint_pandas.PintArray(
                            np.full(len(self.raw_nb_of_instances), self.fixed_nb_of_instances.value),
                            dtype=u.dimensionless
                        )},
                        index=self.raw_nb_of_instances.value.index
                    )
                    nb_of_instances = ExplainableHourlyQuantities(
                        fixed_nb_of_instances_df,
                        "Nb of instances",
                        left_parent=self.raw_nb_of_instances,
                        right_parent=self.fixed_nb_of_instances
                    )
            else:
                nb_of_instances_df = pd.DataFrame(
                    {"value": pint_pandas.PintArray(
                        max_nb_of_instances.magnitude * np.ones(len(self.raw_nb_of_instances)), dtype=u.dimensionless)},
                    index=self.raw_nb_of_instances.value.index
                )

                nb_of_instances = ExplainableHourlyQuantities(
                    nb_of_instances_df,
                    f"Hourly number of {self.name} instances",
                    left_parent=self.raw_nb_of_instances,
                    right_parent=self.fixed_nb_of_instances,
                    operator="depending on not being empty"
                )

        self.nb_of_instances = nb_of_instances.generate_explainable_object_with_logical_dependency(
            self.server_type).set_label(f"Hourly number of {self.name} instances")

    def update_nb_of_instances(self):
        logic_mapping = {
            ServerTypes.autoscaling(): self.autoscaling_update_nb_of_instances,
            ServerTypes.on_premise(): self.on_premise_update_nb_of_instances,
            ServerTypes.serverless(): self.serverless_update_nb_of_instances
        }
        logic_mapping[self.server_type]()
