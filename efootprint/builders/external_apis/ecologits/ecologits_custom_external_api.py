import math
from typing import List

from ecologits.impacts.llm import compute_llm_impacts_dag
from ecologits.tracers.utils import PROVIDER_CONFIG_MAP

from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI,
    EcoLogitsGenAIExternalAPIJob,
    ECOLOGITS_UNIT_MAPPING,
    _mean_value_or_range,
    compute_llm_impacts_dag_source,
    ecologits_source,
)
from efootprint.constants.units import u


class EcoLogitsCustomGenAIExternalAPI(EcoLogitsGenAIExternalAPI):
    default_values = {
        "provider": SourceObject("anthropic"),
        "model_name": SourceObject("custom-inference-model"),
        "custom_model_total_parameter_count": SourceValue(100 * ECOLOGITS_UNIT_MAPPING["model_total_parameter_count"]),
        "custom_model_active_parameter_count": SourceValue(100 * ECOLOGITS_UNIT_MAPPING["model_active_parameter_count"]),
        "custom_data_center_pue": SourceValue(1.2 * u.dimensionless),
        "custom_average_carbon_intensity": SourceValue(500 * ECOLOGITS_UNIT_MAPPING["if_electricity_mix_gwp"]),
        "custom_batch_size": SourceValue(64 * ECOLOGITS_UNIT_MAPPING["batch_size"]),
        "custom_model_quantization_bits": SourceValue(16 * ECOLOGITS_UNIT_MAPPING["model_quantization_bits"]),
        "custom_server_power": SourceValue(1.2 * ECOLOGITS_UNIT_MAPPING["server_power"]),
        "custom_server_gpu_count": SourceValue(8 * ECOLOGITS_UNIT_MAPPING["server_gpu_count"]),
        "custom_request_latency": SourceValue(math.inf * ECOLOGITS_UNIT_MAPPING["request_latency"]),
    }

    list_values = {"provider": EcoLogitsGenAIExternalAPI.list_values["provider"]}
    conditional_list_values = {}

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject,
                 custom_model_total_parameter_count: ExplainableQuantity,
                 custom_model_active_parameter_count: ExplainableQuantity,
                 custom_data_center_pue: ExplainableQuantity,
                 custom_average_carbon_intensity: ExplainableQuantity,
                 custom_batch_size: ExplainableQuantity,
                 custom_model_quantization_bits: ExplainableQuantity,
                 custom_server_power: ExplainableQuantity,
                 custom_server_gpu_count: ExplainableQuantity,
                 custom_request_latency: ExplainableQuantity):
        super().__init__(name=name, provider=provider, model_name=model_name)
        self.custom_model_total_parameter_count = custom_model_total_parameter_count.set_label(
            f"Custom model total parameter count for {self.model_name}")
        self.custom_model_active_parameter_count = custom_model_active_parameter_count.set_label(
            f"Custom model active parameter count for {self.model_name}")
        self.custom_data_center_pue = custom_data_center_pue.set_label(f"Custom datacenter PUE for {self.provider}")
        self.custom_average_carbon_intensity = custom_average_carbon_intensity.set_label(
            f"Custom average carbon intensity for {self.provider}")
        self.custom_batch_size = custom_batch_size.set_label(f"Custom batch size for {self.model_name}")
        self.custom_model_quantization_bits = custom_model_quantization_bits.set_label(
            f"Custom model quantization bits for {self.model_name}")
        self.custom_server_power = custom_server_power.set_label(f"Custom server power for {self.provider}")
        self.custom_server_gpu_count = custom_server_gpu_count.set_label(f"Custom server GPU count for {self.provider}")
        self.custom_request_latency = custom_request_latency.set_label(f"Custom request latency for {self.model_name}")

    @classmethod
    def compatible_jobs(cls) -> List:
        return [EcoLogitsCustomGenAIExternalAPIJob]

    def update_model_total_params(self) -> None:
        self.model_total_params = ExplainableQuantity(
            self.custom_model_total_parameter_count.to(ECOLOGITS_UNIT_MAPPING["model_total_parameter_count"]).value,
            f"{self.model_name} total parameter count (in billions)",
            left_parent=self.custom_model_total_parameter_count,
            operator="use custom inference parameter",
            source=ecologits_source,
        )

    def update_model_active_params(self) -> None:
        self.model_active_params = ExplainableQuantity(
            self.custom_model_active_parameter_count.to(ECOLOGITS_UNIT_MAPPING["model_active_parameter_count"]).value,
            f"{self.model_name} active parameter count (in billions)",
            left_parent=self.custom_model_active_parameter_count,
            operator="use custom inference parameter",
            source=ecologits_source,
        )

    def update_data_center_pue(self) -> None:
        self.data_center_pue = ExplainableQuantity(
            self.custom_data_center_pue.to(u.dimensionless).value,
            f"Datacenter PUE for {self.provider}",
            left_parent=self.custom_data_center_pue,
            operator="use custom inference parameter",
            source=ecologits_source,
        )

    def update_average_carbon_intensity(self) -> None:
        self.average_carbon_intensity = ExplainableQuantity(
            self.custom_average_carbon_intensity.to(ECOLOGITS_UNIT_MAPPING["if_electricity_mix_gwp"]).value,
            f"Average carbon intensity of electricity mix for {self.provider}",
            left_parent=self.custom_average_carbon_intensity,
            operator="use custom inference parameter",
            source=ecologits_source,
        )

class EcoLogitsCustomGenAIExternalAPIJob(EcoLogitsGenAIExternalAPIJob):
    @classmethod
    def compatible_external_apis(cls) -> List:
        return [EcoLogitsCustomGenAIExternalAPI]

    def update_impacts(self) -> None:
        datacenter_wue = _mean_value_or_range(PROVIDER_CONFIG_MAP[self.external_api.provider.value].datacenter_wue)

        impacts = compute_llm_impacts_dag(
            model_active_parameter_count=self.external_api.model_active_params.value.magnitude,
            model_total_parameter_count=self.external_api.model_total_params.value.magnitude,
            output_token_count=self.output_token_count.value.magnitude,
            request_latency=self.external_api.custom_request_latency.to(
                ECOLOGITS_UNIT_MAPPING["request_latency"]).value.magnitude,
            if_electricity_mix_adpe=0,
            if_electricity_mix_pe=0,
            if_electricity_mix_gwp=self.external_api.average_carbon_intensity.value.magnitude,
            if_electricity_mix_wue=0,
            datacenter_pue=self.external_api.data_center_pue.value.magnitude,
            datacenter_wue=datacenter_wue,
            batch_size=self.external_api.custom_batch_size.to(ECOLOGITS_UNIT_MAPPING["batch_size"]).value.magnitude,
            model_quantization_bits=self.external_api.custom_model_quantization_bits.to(
                ECOLOGITS_UNIT_MAPPING["model_quantization_bits"]).value.magnitude,
            server_power=self.external_api.custom_server_power.to(ECOLOGITS_UNIT_MAPPING["server_power"]).value.magnitude,
            server_gpu_count=self.external_api.custom_server_gpu_count.to(
                ECOLOGITS_UNIT_MAPPING["server_gpu_count"]).value.magnitude,
        )

        self.impacts = ExplainableDict(
            impacts,
            f"Ecologits impacts for {self.name}",
            left_parent=self.external_api.model_active_params,
            right_parent=self.external_api.model_total_params,
            operator="compute impacts with EcoLogits compute_llm_impacts_dag function",
            source=compute_llm_impacts_dag_source,
        ).generate_explainable_object_with_logical_dependency(
            self.output_token_count
        ).generate_explainable_object_with_logical_dependency(
            self.external_api.average_carbon_intensity
        )