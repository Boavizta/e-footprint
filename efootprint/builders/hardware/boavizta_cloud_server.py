from time import time

from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict

start = time()
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue

from efootprint.builders.hardware.boaviztapi_utils import call_boaviztapi
from efootprint.constants.units import u
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.logger import logger

boavizta_cloud_providers_request_result = call_boaviztapi(
        "https://api.boavizta.org/v1/cloud/instance/all_providers")
all_boavizta_cloud_providers = []
for cloud_provider in boavizta_cloud_providers_request_result:
    all_boavizta_cloud_providers.append(SourceObject(cloud_provider))
instance_types_conditional_list_values_dict = {"depends_on": "provider", "conditional_list_values": {}}
for cloud_provider in boavizta_cloud_providers_request_result:
    provider_instance_types = call_boaviztapi(
            f"https://api.boavizta.org/v1/cloud/instance/all_instances",
            params={"provider": cloud_provider}
    )
    instance_types_conditional_list_values_dict["conditional_list_values"][SourceObject(cloud_provider)] = [
        SourceObject(instance_type) for instance_type in provider_instance_types]


class BoaviztaCloudServer(Server):
    @classmethod
    def default_values(cls):
        return {
            "provider": SourceObject("scaleway"),
            "instance_type": SourceObject("ent1-s"),
            "server_type": ServerTypes.autoscaling(),
            "average_carbon_intensity": SourceValue(233 * u.g / u.kWh),
            "lifespan": SourceValue(6 * u.year),
            "idle_power": SourceValue(0 * u.W),
            "power_usage_effectiveness": SourceValue(1.2 * u.dimensionless),
            "server_utilization_rate": SourceValue(0.9 * u.dimensionless),
            "base_ram_consumption": SourceValue(0 * u.GB),
            "base_compute_consumption": SourceValue(0 * u.cpu_core),
            "fixed_nb_of_instances": EmptyExplainableObject()
        }

    @classmethod
    def list_values(cls):
        server_list_values = super().list_values()
        server_list_values.update({"provider": all_boavizta_cloud_providers})

        return server_list_values

    @classmethod
    def conditional_list_values(cls):
        server_conditional_list_values = super().conditional_list_values()
        server_conditional_list_values.update({"instance_type": instance_types_conditional_list_values_dict})

        return server_conditional_list_values

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "provider" and self.trigger_modeling_updates:
            raise PermissionError("The provider of a BoaviztaCloudServer cannot be changed after initialization. "
                                  "Use a ModelingUpdate to update both provider and a compatible model name.")
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)

    def __init__(
            self, name: str, provider: ExplainableObject, instance_type: ExplainableObject, server_type: ExplainableObject,
            lifespan: ExplainableQuantity, idle_power: ExplainableQuantity,
            power_usage_effectiveness: ExplainableQuantity, average_carbon_intensity: ExplainableQuantity,
            server_utilization_rate: ExplainableQuantity, base_ram_consumption: ExplainableQuantity,
            base_compute_consumption: ExplainableQuantity, storage: Storage,
            fixed_nb_of_instances: ExplainableQuantity | EmptyExplainableObject | None = None):
        super().__init__(
            name, server_type, carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(0 * u.W),
            lifespan=lifespan, idle_power=idle_power, ram=SourceValue(0 * u.GB), compute=SourceValue(0 * u.cpu_core),
            power_usage_effectiveness=power_usage_effectiveness, average_carbon_intensity=average_carbon_intensity,
            server_utilization_rate=server_utilization_rate, base_ram_consumption=base_ram_consumption,
            base_compute_consumption=base_compute_consumption, storage=storage,
            fixed_nb_of_instances=fixed_nb_of_instances)
        self.provider = provider.set_label(f"{self.name} cloud provider")
        self.instance_type = instance_type.set_label(f"{self.name} instance type")
        self.impact_url = "https://api.boavizta.org/v1/cloud/instance"
        self.api_call_response = EmptyExplainableObject()

    @property
    def calculated_attributes(self):
        return (["api_call_response", "carbon_footprint_fabrication", "power", "ram", "compute"]
                + super().calculated_attributes)

    @property
    def attributes_that_shouldnt_trigger_update_logic(self):
        return super().attributes_that_shouldnt_trigger_update_logic + ["impact_url"]

    def update_api_call_response(self):
        params = {"provider": self.provider.value, "instance_type": self.instance_type.value}
        impact_source = Source(name="Boavizta API cloud instances",
                               link=f"{self.impact_url}?{'&'.join([key + '=' + params[key] for key in params])}")

        call_response = call_boaviztapi(url=self.impact_url, params=params)
        self.api_call_response = ExplainableDict(
            call_response, "API call response",
            left_parent=self.provider, right_parent=self.instance_type, operator="combined in Boavizta API call with",
            source=impact_source)

    def update_carbon_footprint_fabrication(self):
        self.carbon_footprint_fabrication = ExplainableQuantity(
            self.api_call_response.value["impacts"]["gwp"]["embedded"]["value"] * u.kg,
            f"{self.name} fabrication carbon footprint", left_parent=self.api_call_response,
            operator="data extraction from", source=self.api_call_response.source)

    def update_power(self):
        average_power_unit = self.api_call_response.value["verbose"]["avg_power"]["unit"]
        use_time_ratio = self.api_call_response.value["verbose"]["use_time_ratio"]["value"]
        assert average_power_unit == "W", f"Unexpected power unit {average_power_unit}"
        assert float(use_time_ratio) == 1, f"Unexpected use time ratio {use_time_ratio}"
        average_power_value = self.api_call_response.value["verbose"]["avg_power"]["value"]

        self.power = ExplainableQuantity(
            average_power_value * u.W, f"{self.name} power", left_parent=self.api_call_response,
            operator="data extraction from", source=self.api_call_response.source)

    def update_ram(self):
        assert self.api_call_response.value["verbose"]["memory"]["unit"] == "GB", \
            f"Unexpected RAM unit {self.api_call_response.value['verbose']['memory']['unit']}"
        ram_spec = self.api_call_response.value["verbose"]["memory"]["value"]

        self.ram = ExplainableQuantity(
            ram_spec * u.GB, f"{self.name} ram",
            left_parent=self.api_call_response, operator="data extraction from", source=self.api_call_response.source)

    def update_compute(self):
        nb_vcpu = self.api_call_response.value["verbose"]["vcpu"]["value"]

        self.compute = ExplainableQuantity(
            nb_vcpu * u.cpu_core, f"{self.name} compute",
            left_parent=self.api_call_response, operator="data extraction from", source=self.api_call_response.source)

logger.info(f"Imported BoaviztaCloudServer in {time() - start:.5f} seconds.")


if __name__ == "__main__":
    from efootprint.abstract_modeling_classes.explainable_object_base_class import \
        retrieve_update_function_from_mod_obj_and_attr_name

    for provider in all_boavizta_cloud_providers:
        for instance_type in instance_types_conditional_list_values_dict["conditional_list_values"][provider]:
            try:
                cloud_server = BoaviztaCloudServer(name=f"test_{provider}_{instance_type}",
                                    provider=SourceObject(provider.value), instance_type=SourceObject(instance_type.value),
                                    server_type=ServerTypes.autoscaling(),
                                    lifespan=SourceValue(6 * u.year),
                                    idle_power=SourceValue(0 * u.W),
                                    power_usage_effectiveness=SourceValue(1.2 * u.dimensionless),
                                    average_carbon_intensity=SourceValue(0.233 * u.kg / u.kWh),
                                    server_utilization_rate=SourceValue(0.9 * u.dimensionless),
                                    base_ram_consumption=SourceValue(0 * u.GB),
                                    base_compute_consumption=SourceValue(0 * u.cpu_core),
                                    storage=Storage.ssd())
                for attr_name in ["api_call_response", "carbon_footprint_fabrication", "power", "ram", "compute"]:
                    update_func = retrieve_update_function_from_mod_obj_and_attr_name(cloud_server, attr_name)
                    update_func()
                logger.info(f"{provider} - {instance_type}: Compute {cloud_server.compute} RAM {cloud_server.ram} "
                            f"CCF {cloud_server.carbon_footprint_fabrication} power {cloud_server.power}.")
            except Exception as e:
                logger.error(f"Error with provider {provider} and instance type {instance_type}: {e}")
