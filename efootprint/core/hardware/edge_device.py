from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.constants.sources import Sources
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.storage import Storage
from efootprint.core.hardware.infra_hardware import InfraHardware


class EdgeDevice(InfraHardware):
    default_values = {
        "carbon_footprint_fabrication": SourceValue(60 * u.kg, Sources.HYPOTHESIS),
        "power": SourceValue(30 * u.W, Sources.HYPOTHESIS),
        "lifespan": SourceValue(4 * u.year, Sources.HYPOTHESIS),
        "idle_power": SourceValue(5 * u.W, Sources.HYPOTHESIS),
        "ram": SourceValue(8 * u.GB, Sources.HYPOTHESIS),
        "compute": SourceValue(4 * u.cpu_core, Sources.HYPOTHESIS),
        "power_usage_effectiveness": SourceValue(1.0 * u.dimensionless, Sources.HYPOTHESIS),
        "server_utilization_rate": SourceValue(0.8 * u.dimensionless, Sources.HYPOTHESIS),
        "base_ram_consumption": SourceValue(1 * u.GB, Sources.HYPOTHESIS),
        "base_compute_consumption": SourceValue(0.1 * u.cpu_core, Sources.HYPOTHESIS),
    }

    def __init__(self, name: str, carbon_footprint_fabrication: ExplainableQuantity,
                 power: ExplainableQuantity, lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
                 ram: ExplainableQuantity, compute: ExplainableQuantity,
                 power_usage_effectiveness: ExplainableQuantity,
                 server_utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage):
        super().__init__(name, carbon_footprint_fabrication, power, lifespan)
        
        # Edge device specific attributes
        self.hour_by_hour_compute_need = EmptyExplainableObject()
        self.hour_by_hour_ram_need = EmptyExplainableObject()
        self.available_compute_per_instance = EmptyExplainableObject()
        self.available_ram_per_instance = EmptyExplainableObject()
        self.occupied_ram_per_instance = EmptyExplainableObject()
        self.occupied_compute_per_instance = EmptyExplainableObject()
        
        # Parameters
        self.idle_power = idle_power.set_label(f"Idle power of {self.name}")
        self.ram = ram.set_label(f"RAM of {self.name}")
        self.compute = compute.set_label(f"Compute of {self.name}")
        self.power_usage_effectiveness = power_usage_effectiveness.set_label(f"PUE of {self.name}")
        self.server_utilization_rate = server_utilization_rate.set_label(f"{self.name} utilization rate")
        self.base_ram_consumption = base_ram_consumption.set_label(f"Base RAM consumption of {self.name}")
        self.base_compute_consumption = base_compute_consumption.set_label(f"Base compute consumption of {self.name}")
        self.storage = storage
        
        # These will be set dynamically by EdgeUsagePattern
        self.average_carbon_intensity = EmptyExplainableObject()
        self.fixed_nb_of_instances = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return super().calculated_attributes + [
            "hour_by_hour_ram_need", "hour_by_hour_compute_need",
            "occupied_ram_per_instance", "occupied_compute_per_instance",
            "available_ram_per_instance", "available_compute_per_instance"
        ]

    @property
    def edge_usage_journey(self):
        if self.modeling_obj_containers:
            if len(self.modeling_obj_containers) > 1:
                raise PermissionError(
                    f"EdgeDevice object can only be associated with one EdgeUsageJourney object but {self.name} is associated "
                    f"with {[mod_obj.name for mod_obj in self.modeling_obj_containers]}")
            return self.modeling_obj_containers[0]
        else:
            return None

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return [self.storage]

    @property
    def edge_processes(self) -> List:
        return self.edge_usage_journey.edge_processes

    def update_hour_by_hour_ram_need(self):
        hour_by_hour_ram_needs = EmptyExplainableObject()
        for edge_process in self.edge_processes:
            # EdgeProcess will have recurrent_ram_compute that defines weekly hourly consumption
            hour_by_hour_ram_needs += edge_process.hourly_ram_consumption
        
        self.hour_by_hour_ram_need = hour_by_hour_ram_needs.to(u.GB).set_label(f"{self.name} hour by hour RAM need")

    def update_hour_by_hour_compute_need(self):
        hour_by_hour_compute_needs = EmptyExplainableObject()
        for edge_process in self.edge_processes:
            # EdgeProcess will have recurrent_cpu_compute that defines weekly hourly consumption
            hour_by_hour_compute_needs += edge_process.hourly_compute_consumption
        
        self.hour_by_hour_compute_need = hour_by_hour_compute_needs.to(u.cpu_core).set_label(f"{self.name} hour by hour compute need")

    def validate_resource_consumption(self):
        """
        Validate that the total resource consumption of all edge processes
        doesn't exceed the edge device capacity.
        """
        # Check each hour of the week
        for hour in range(168):  # 168 hours in a week
            total_cpu = sum(process.recurrent_cpu_compute[hour] for process in self.edge_processes)
            total_ram = sum(process.recurrent_ram_compute[hour] for process in self.edge_processes)

            # Check against available capacity (considering utilization rate and base consumption)
            available_cpu = (
                        self.edge_device.compute.value.magnitude * self.edge_device.server_utilization_rate.value.magnitude
                        - self.edge_device.base_compute_consumption.value.magnitude)
            available_ram = (self.edge_device.ram.value.to(
                u.GB).magnitude * self.edge_device.server_utilization_rate.value.magnitude
                             - self.edge_device.base_ram_consumption.value.to(u.GB).magnitude)

            if total_cpu > available_cpu:
                raise ValueError(
                    f"Hour {hour}: Total CPU consumption ({total_cpu}) exceeds available capacity ({available_cpu}) "
                    f"on {self.edge_device.name}")

            if total_ram > available_ram:
                raise ValueError(
                    f"Hour {hour}: Total RAM consumption ({total_ram} GB) exceeds available capacity ({available_ram} GB) "
                    f"on {self.edge_device.name}")

    def update_occupied_ram_per_instance(self):
        self.occupied_ram_per_instance = self.base_ram_consumption.set_label(f"Occupied RAM per {self.name} instance")

    def update_occupied_compute_per_instance(self):
        self.occupied_compute_per_instance = self.base_compute_consumption.set_label(f"Occupied compute per {self.name} instance")

    def update_available_ram_per_instance(self):
        available_ram_per_instance = (self.ram * self.server_utilization_rate - self.occupied_ram_per_instance)
        
        from efootprint.core.hardware.infra_hardware import InsufficientCapacityError
        if available_ram_per_instance.value < 0 * u.B:
            raise InsufficientCapacityError(
                self, "RAM", self.ram * self.server_utilization_rate, self.occupied_ram_per_instance)

        self.available_ram_per_instance = available_ram_per_instance.set_label(f"Available RAM per {self.name} instance")

    def update_available_compute_per_instance(self):
        available_compute_per_instance = (self.compute * self.server_utilization_rate - self.occupied_compute_per_instance)
        
        from efootprint.core.hardware.infra_hardware import InsufficientCapacityError
        if available_compute_per_instance.value < 0:
            raise InsufficientCapacityError(
                self, "compute", self.compute * self.server_utilization_rate, self.occupied_compute_per_instance)

        self.available_compute_per_instance = available_compute_per_instance.set_label(f"Available compute per {self.name} instance")

    def update_raw_nb_of_instances(self):
        # EdgeDevice instances are fixed by the EdgeUsagePattern volume, so raw = fixed
        self.raw_nb_of_instances = self.fixed_nb_of_instances.copy().set_label(f"Raw nb of {self.name} instances")

    def update_nb_of_instances(self):
        # For edge devices, nb_of_instances = fixed_nb_of_instances (from volume)
        self.nb_of_instances = self.fixed_nb_of_instances.copy().set_label(f"Number of {self.name} instances")

    def update_instances_energy(self):
        energy_spent_by_one_idle_instance_over_one_hour = (
            self.idle_power * self.power_usage_effectiveness * ExplainableQuantity(1 * u.hour, "one hour"))
        extra_energy_spent_by_one_fully_active_instance_over_one_hour = (
            (self.power - self.idle_power) * self.power_usage_effectiveness
            * ExplainableQuantity(1 * u.hour, "one hour"))

        device_power = (
            energy_spent_by_one_idle_instance_over_one_hour * self.nb_of_instances
            + extra_energy_spent_by_one_fully_active_instance_over_one_hour * self.nb_of_instances)

        self.instances_energy = device_power.to(u.kWh).set_label(f"Hourly energy consumed by {self.name} instances")