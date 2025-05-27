from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.server_base import ServerTypes, ServerBase
from efootprint.core.hardware.storage import Storage


class BoaviztaServerFromConfig(ServerBase):
    @classmethod
    def default_values(cls):
        return {
            "server_type": ServerTypes.on_premise(),
            "nb_of_cpu_units": SourceValue(1 * u.dimensionless),
            "nb_of_cores_per_cpu_unit": SourceValue(1 * u.dimensionless),
            "nb_of_ram_units": SourceValue(1 * u.dimensionless),
            "ram_quantity_per_unit": SourceValue(1 * u.GB),
            "average_carbon_intensity": SourceValue(233 * u.g / u.kWh),
            "lifespan": SourceValue(6 * u.year),
            "idle_power": SourceValue(0 * u.W),
            "power_usage_effectiveness": SourceValue(1.4 * u.dimensionless),
            "server_utilization_rate": SourceValue(0.7 * u.dimensionless),
            "base_ram_consumption": SourceValue(0 * u.GB),
            "base_compute_consumption": SourceValue(0 * u.cpu_core),
            "storage": Storage.ssd(storage_capacity=SourceValue(32 * u.GB)),
            "fixed_nb_of_instances": EmptyExplainableObject()
        }
    
    def __init__(self, name: str, server_type: ExplainableObject, nb_of_cpu_units: ExplainableQuantity,
                 nb_of_cores_per_cpu_unit: ExplainableQuantity,
                 nb_of_ram_units: ExplainableQuantity, ram_quantity_per_unit: ExplainableQuantity,
                 average_carbon_intensity: ExplainableQuantity, lifespan: ExplainableQuantity,
                 idle_power: ExplainableQuantity, power_usage_effectiveness: ExplainableQuantity,
                 server_utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
                 base_compute_consumption: ExplainableQuantity, storage: Storage,
                 fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject | None = None):
        super().__init__(
            name, server_type=server_type, carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(0 * u.kg), lifespan=lifespan, idle_power=idle_power, ram=SourceValue(0 * u.GB),
            compute=SourceValue(0 * u.cpu_core), power_usage_effectiveness=power_usage_effectiveness,
            average_carbon_intensity=average_carbon_intensity,
            server_utilization_rate=server_utilization_rate, base_ram_consumption=base_ram_consumption,
            base_compute_consumption=base_compute_consumption, fixed_nb_of_instances=fixed_nb_of_instances,
            storage=storage)
        self.nb_of_cpu_units = nb_of_cpu_units
        self.nb_of_cores_per_cpu_unit = nb_of_cores_per_cpu_unit
        self.nb_of_ram_units = nb_of_ram_units
        self.ram_quantity_per_unit = ram_quantity_per_unit
        self.impact_url = "https://api.boavizta.org/v1/server/"
        # TODO: allow for archetype setting
        self.params = {"verbose": "true", "archetype": "platform_compute_medium", "criteria": ["gwp"]}
        self.impact_source = Source(
            name="Boavizta API servers",
            link=f"{self.impact_url}?{'&'.join([key + '=' + str(self.params[key]) for key in self.params])}")
        self.cpu_config = EmptyExplainableObject()
        self.ram_config = EmptyExplainableObject()
        self.api_call_response = EmptyExplainableObject()
        
    @property
    def calculated_attributes(self):
        return (["cpu_config", "ram_config", "api_call_response", "carbon_footprint_fabrication", "power", "ram", 
                 "compute"] + super().calculated_attributes)

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["impact_url", "params", "impact_source"]

    # TODO: Introduce a notion of compatible storages

    def after_init(self):
        super().after_init()
        # TODO: uncomment line after fixing the API call structure
        # self.compute_calculated_attributes()
    
    def update_cpu_config(self):
        cpu_config_dict = {"units": self.nb_of_cpu_units.to(u.dimensionless).magnitude,
                           "core_units": self.nb_of_cores_per_cpu_unit.to(u.dimensionless).magnitude}

        self.cpu_config = ExplainableObject(
            cpu_config_dict, label=f"{self.name} cpu config", left_parent=self.nb_of_cpu_units,
            right_parent=self.nb_of_cores_per_cpu_unit, operator="combined in Boavizta API with",
            source=Sources.USER_DATA)

    def update_ram_config(self):
        ram_config_dict = {"units": self.nb_of_ram_units.to(u.dimensionless).magnitude,
                           "capacity": self.ram_quantity_per_unit.to(u.GB).magnitude}

        self.ram_config = ExplainableObject(
            ram_config_dict, label=f"{self.name} ram config", left_parent=self.nb_of_ram_units,
            right_parent=self.ram_quantity_per_unit, operator="combined in Boavizta API with",
            source=Sources.USER_DATA)

    def update_api_call_response(self):
        # TODO: fix api call structure
        api_call_data = {
            "model": {"type": "rack"},
            "configuration": {"cpu": self.cpu_config.value, "ram": self.ram_config.value}
        }
        self.api_call_response = ExplainableDict(
            call_boaviztapi(url=self.impact_url, params=self.params, json=api_call_data, method="POST"),
            label=f"{self.name} api call data", left_parent=self.cpu_config, right_parent=self.ram_config,
            operator="combined in Boavizta API data with", source=Sources.USER_DATA)

    def update_carbon_footprint_fabrication(self):
        total_fabrication_footprint_storage_included = ExplainableQuantity(
            self.api_call_response.value["impacts"]["gwp"]["embedded"]["value"] * u.kg,
            f"Total {self.name} fabrication footprint storage included", 
            left_parent=self.api_call_response, operator="data extraction from",
            source=self.impact_source)

        storage_spec = self.api_call_response.value["verbose"].get("SSD-1", self.api_call_response.value["verbose"].get("HDD-1", None))
        if storage_spec is None:
            raise ValueError("Both SSD and HDD storage found in the server impact data. This is not implemented yet")
        
        full_storage_carbon_footprint_fabrication = ExplainableQuantity(
            storage_spec["impacts"]["gwp"]["embedded"]["value"] * u.kg, f"Total {self.name} fabrication footprint",
            left_parent=self.api_call_response, operator="data extraction from",
            source=self.impact_source)
        
        total_fabrication_footprint_storage_excluded = (
                total_fabrication_footprint_storage_included - full_storage_carbon_footprint_fabrication)
        
        self.carbon_footprint_fabrication = total_fabrication_footprint_storage_excluded.set_label(
            f"Fabrication footprint of {self.name}")
        
    def update_power(self):
        average_power_value = self.api_call_response.value["verbose"]["avg_power"]["value"]
        average_power_unit = self.api_call_response.value["verbose"]["avg_power"]["unit"]
        use_time_ratio = self.api_call_response.value["verbose"]["use_time_ratio"]["value"]

        assert average_power_unit == "W", f"Unexpected power unit {average_power_unit}"
        assert float(use_time_ratio) == 1, f"Unexpected use time ratio {use_time_ratio}"
        
        self.power = ExplainableQuantity(
            average_power_value * u.W, f"{self.name} power", left_parent=self.api_call_response,
            operator="data extraction from", source=self.impact_source)
        
    def update_ram(self):
        ram_spec = self.api_call_response.value["verbose"]["RAM-1"]

        self.ram = ExplainableQuantity(
            ram_spec["units"]["value"] * ram_spec["capacity"]["value"] * u.GB, f"{self.name} ram",
            left_parent=self.api_call_response, operator="data extraction from", source=self.impact_source)
        
    def update_compute(self):
        cpu_spec = self.api_call_response.value["verbose"]["CPU-1"]

        self.compute = ExplainableQuantity(
            cpu_spec["units"]["value"] * cpu_spec["core_units"]["value"] * u.cpu_core, f"{self.name} compute",
            left_parent=self.api_call_response, operator="data extraction from", source=self.impact_source)
        

class BoaviztaStorageFromConfig(Storage):
    @classmethod
    def default_values(cls):
        return {
            "idle_power": SourceValue(0 * u.W),
            "data_replication_factor": SourceValue(1 * u.dimensionless),
            "data_storage_duration": SourceValue(1 * u.year),
            "base_storage_need": SourceValue(0 * u.GB)
        }
    # TODO: create StorageBase class and introduce compatible_storages in servers

    def __init__(self, name: str, idle_power: ExplainableQuantity, data_replication_factor: ExplainableQuantity,
                 data_storage_duration: ExplainableQuantity, base_storage_need: ExplainableQuantity):
        super().__init__(
            name, carbon_footprint_fabrication_per_storage_capacity=SourceValue(0 * u.kg / u.TB),
            power_per_storage_capacity=SourceValue(0 * u.W / u.TB),
            lifespan=SourceValue(0 * u.year), idle_power=idle_power, storage_capacity=SourceValue(0 * u.TB), 
            data_replication_factor=data_replication_factor, data_storage_duration=data_storage_duration, 
            base_storage_need=base_storage_need)
        
        self.storage_type = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return (["storage_type", "storage_capacity", "fixed_nb_of_instances",
                 "carbon_footprint_fabrication_per_storage_capacity",
                 "power_per_storage_capacity", "lifespan"] + super().calculated_attributes)

    def update_storage_type(self):
        storage_type = None
        if ("SSD-1" in self.server.api_call_response.value["verbose"]
                and "HDD-1" in self.server.api_call_response.value["verbose"]):
            raise ValueError("Both SSD and HDD storage found in the server impact data. This is not implemented yet")
        elif "SSD-1" in self.server.api_call_response.value["verbose"]:
            storage_type = "SSD"
        elif "HDD-1" in self.server.api_call_response.value["verbose"]:
            storage_type = "HDD"

        self.storage_type = ExplainableObject(
            storage_type, label=f"{self.name} storage type", left_parent=self.server.api_call_response.value,
            operator="data extraction from", source=self.server.impact_source)

    def update_storage_capacity(self):
        storage_spec = self.server.api_call_response.value["verbose"][f"{self.storage_type.value}-1"]
        storage_unit = getattr(u, storage_spec["capacity"]["unit"])
        
        self.storage_capacity = ExplainableQuantity(
            storage_spec["capacity"]["value"] * storage_unit, f"{self.name} storage capacity", 
            left_parent=self.server.api_call_response, operator="data extraction", source=self.server.impact_source)

    def update_fixed_nb_of_instances(self):
        storage_spec = self.server.api_call_response.value["verbose"][f"{self.storage_type.value}-1"]
        nb_units = ExplainableQuantity(
            storage_spec["units"]["value"] * u.dimensionless, label=f"Number of {self.name} storage instances",
            left_parent=self.server.api_call_response, operator="data extraction",
            source=self.server.impact_source)

        self.fixed_nb_of_instances = nb_units.set_label(f"Fixed number of {self.name} storage instances")

    def update_carbon_footprint_fabrication_per_storage_capacity(self):
        storage_spec = self.server.api_call_response.value["verbose"][f"{self.storage_type.value}-1"]
        full_storage_carbon_footprint_fabrication = ExplainableQuantity(
            storage_spec["impacts"]["gwp"]["embedded"]["value"] * u.kg, left_parent=self.storage_type,
            source=self.server.impact_source,
            label=f"Total {self.name} fabrication footprint")
        
        self.carbon_footprint_fabrication_per_storage_capacity = (
                full_storage_carbon_footprint_fabrication / (self.fixed_nb_of_instances * self.storage_capacity)
        ).set_label(f"Fabrication footprint of one {self.name} storage instance")

    def update_power_per_storage_capacity(self):
        power_per_storage_capacity = None
        if self.storage_type.value == "SSD":
            power_per_storage_capacity = SourceValue(1.3 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY)
        elif self.storage_type.value == "HDD":
            power_per_storage_capacity = SourceValue(4.2 * u.W / u.TB, Sources.STORAGE_EMBODIED_CARBON_STUDY)

        self.power_per_storage_capacity = (
            power_per_storage_capacity.generate_explainable_object_with_logical_dependency(
                self.storage_type).set_label(f"{self.name} power per storage capacity"))

    def update_lifespan(self):
        lifespan = None
        if self.storage_type.value == "SSD":
            lifespan = SourceValue(6 * u.year)
        elif self.storage_type.value == "HDD":
            lifespan = SourceValue(4 * u.year)

        self.lifespan = lifespan.generate_explainable_object_with_logical_dependency(self.storage_type).set_label(
            f"{self.name} lifespan")
