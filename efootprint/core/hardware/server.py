from typing import List

import numpy as np
import pandas as pd
import pint_pandas

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, \
    EmptyExplainableObject, ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.sources import Sources
from efootprint.core.hardware.hardware_base_classes import InfraHardware
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SOURCE_VALUE_DEFAULT_NAME, SourceObject
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


class Server(InfraHardware):
    @classmethod
    def default_values(cls):
        return {
            "server_type": ServerTypes.autoscaling(),
            "carbon_footprint_fabrication": SourceValue(600 * u.kg, Sources.BASE_ADEME_V19),
            "power": SourceValue(300 * u.W, Sources.HYPOTHESIS),
            "lifespan": SourceValue(6 * u.year, Sources.HYPOTHESIS),
            "idle_power": SourceValue(50 * u.W, Sources.HYPOTHESIS),
            "ram": SourceValue(128 * u.GB, Sources.HYPOTHESIS),
            "cpu_cores": SourceValue(24 * u.core, Sources.HYPOTHESIS),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless, Sources.HYPOTHESIS),
            "average_carbon_intensity": SourceValue(100 * u.g / u.kWh, Sources.HYPOTHESIS),
            "server_utilization_rate": SourceValue(0.9 * u.dimensionless, Sources.HYPOTHESIS),
            "base_ram_consumption": SourceValue(0 * u.GB, Sources.HYPOTHESIS),
            "base_cpu_consumption": SourceValue(0 * u.core, Sources.HYPOTHESIS)
        }

    @classmethod
    def list_values(cls):
        return {"server_type": [ServerTypes.autoscaling(), ServerTypes.on_premise(), ServerTypes.serverless()]}

    @classmethod
    def conditional_list_values(cls):
        return {"fixed_nb_of_instances": {"depends_on": "server_type", "conditional_list_values": {
            ServerTypes.autoscaling(): [EmptyExplainableObject()],
            ServerTypes.serverless(): [EmptyExplainableObject()]}
        }}

    def __init__(self, name: str, server_type: SourceObject, carbon_footprint_fabrication: SourceValue,
                 power: SourceValue, lifespan: SourceValue, idle_power: SourceValue, ram: SourceValue,
                 cpu_cores: SourceValue, power_usage_effectiveness: SourceValue, average_carbon_intensity: SourceValue,
                 server_utilization_rate: SourceValue, base_ram_consumption: SourceValue,
                 base_cpu_consumption: SourceValue, storage: Storage,
                 fixed_nb_of_instances: SourceValue | EmptyExplainableObject = None):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        self.hour_by_hour_cpu_need = EmptyExplainableObject()
        self.hour_by_hour_ram_need = EmptyExplainableObject()
        self.available_cpu_per_instance = EmptyExplainableObject()
        self.available_ram_per_instance = EmptyExplainableObject()
        self.server_utilization_rate = EmptyExplainableObject()
        self.raw_nb_of_instances = EmptyExplainableObject()
        self.nb_of_instances = EmptyExplainableObject()
        self.occupied_ram_per_instance = EmptyExplainableObject()
        self.occupied_cpu_per_instance = EmptyExplainableObject()
        self.server_type = server_type.set_label(f"Server type of {self.name}")
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.ram = ram.set_label(f"RAM of {self.name}")
        self.cpu_cores = cpu_cores.set_label(f"Nb cpus cores of {self.name}")
        if not power_usage_effectiveness.value.check("[]"):
            raise ValueError(
                "Value of variable 'power_usage_effectiveness' does not have appropriate [] dimensionality")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE of {self.name}")
        if not average_carbon_intensity.value.check("[time]**2 / [length]**2"):
            raise ValueError(
                "Variable 'average_carbon_intensity' does not have mass over energy "
                "('[time]**2 / [length]**2') dimensionality"
            )
        self.average_carbon_intensity = average_carbon_intensity
        if self.average_carbon_intensity.label == SOURCE_VALUE_DEFAULT_NAME:
            self.average_carbon_intensity.set_label(f"Average carbon intensity of {self.name} electricity")
        self.server_utilization_rate = server_utilization_rate.set_label(f"{self.name} utilization rate")
        if not base_ram_consumption.value.check("[]"):
            raise ValueError("variable 'base_ram_consumption' does not have byte dimensionality")
        if not base_cpu_consumption.value.check("[cpu]"):
            raise ValueError("variable 'base_cpu_consumption' does not have core dimensionality")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")
        self.base_cpu_consumption = base_cpu_consumption.set_label(f"Base CPU consumption of {self.name}")
        self.fixed_nb_of_instances = fixed_nb_of_instances or EmptyExplainableObject()
        if not isinstance(self.fixed_nb_of_instances, EmptyExplainableObject):
            assert self.server_type.value == ServerTypes.on_premise(), \
                "Fixed number of instances can only be defined for on-premise servers"
            if not fixed_nb_of_instances.value.check("[]"):
                raise ValueError("Variable 'fixed_nb_of_instances' shouldn’t have any dimensionality")
        self.fixed_nb_of_instances.set_label(
            f"User defined number of {self.name} instances").to(u.dimensionless)
        self.storage = ContextualModelingObjectAttribute(storage)

    @property
    def calculated_attributes(self):
        return ["hour_by_hour_ram_need", "hour_by_hour_cpu_need",
                "occupied_ram_per_instance", "occupied_cpu_per_instance",
                "available_ram_per_instance", "available_cpu_per_instance",
                "raw_nb_of_instances", "nb_of_instances",
                "instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    @property
    def resources_unit_dict(self):
        return {"ram": "GB", "cpu": "core"}

    @property
    def jobs(self) -> List[ModelingObject]:
        from efootprint.core.usage.job import Job

        return [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, Job)]

    @property
    def installed_services(self) -> List[ModelingObject]:
        from efootprint.builders.services.service_base_class import Service

        return [modeling_obj for modeling_obj in self.modeling_obj_containers if isinstance(modeling_obj, Service)]

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ContextualModelingObjectAttribute]:
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

    def update_hour_by_hour_cpu_need(self):
        self.hour_by_hour_cpu_need = self.compute_hour_by_hour_resource_need("cpu")

    def update_occupied_ram_per_instance(self):
        self.occupied_ram_per_instance = (self.base_ram_consumption + sum(
            [service.base_ram_consumption for service in self.installed_services])).set_label(
            f"Occupied RAM per {self.name} instance including services")

    def update_occupied_cpu_per_instance(self):
        self.occupied_cpu_per_instance = (self.base_cpu_consumption + sum(
            [service.base_cpu_consumption for service in self.installed_services])).set_label(
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

    def update_available_cpu_per_instance(self):
        available_cpu_per_instance = self.cpu_cores * self.server_utilization_rate
        available_cpu_per_instance -= self.occupied_cpu_per_instance
        if available_cpu_per_instance.value < 0:
            raise ValueError(
                f"server has available capacity of {(self.cpu_cores * self.server_utilization_rate).value} "
                f" but is asked {self.occupied_cpu_per_instance.value}")

        self.available_cpu_per_instance = available_cpu_per_instance.set_label(
            f"Available CPU per {self.name} instance")

    def update_raw_nb_of_instances(self):
        nb_of_servers_based_on_ram_alone = (
                self.hour_by_hour_ram_need / self.available_ram_per_instance).to(u.dimensionless).set_label(
            f"Raw nb of {self.name} instances based on RAM alone")
        nb_of_servers_based_on_cpu_alone = (
                self.hour_by_hour_cpu_need / self.available_cpu_per_instance).to(u.dimensionless).set_label(
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

            nb_of_instances_df = pd.DataFrame(
                {"value": pint_pandas.PintArray(
                        max_nb_of_instances.magnitude * np.ones(len(self.raw_nb_of_instances)), dtype=u.dimensionless)},
                index=self.raw_nb_of_instances.value.index
            )

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
