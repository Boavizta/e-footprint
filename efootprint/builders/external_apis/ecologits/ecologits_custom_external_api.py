from typing import List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
    EcoLogitsGenAIExternalAPI,
    EcoLogitsGenAIExternalAPIJob,
    ECOLOGITS_UNIT_MAPPING,
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
    }

    list_values = {"provider": EcoLogitsGenAIExternalAPI.list_values["provider"]}
    conditional_list_values = {}

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject,
                 custom_model_total_parameter_count: ExplainableQuantity,
                 custom_model_active_parameter_count: ExplainableQuantity,
                 custom_data_center_pue: ExplainableQuantity,
                 custom_average_carbon_intensity: ExplainableQuantity):
        super().__init__(name=name, provider=provider, model_name=model_name)
        self.custom_model_total_parameter_count = custom_model_total_parameter_count.set_label(
            f"Custom model total parameter count for {self.model_name}")
        self.custom_model_active_parameter_count = custom_model_active_parameter_count.set_label(
            f"Custom model active parameter count for {self.model_name}")
        self.custom_data_center_pue = custom_data_center_pue.set_label(f"Custom datacenter PUE for {self.provider}")
        self.custom_average_carbon_intensity = custom_average_carbon_intensity.set_label(
            f"Custom average carbon intensity for {self.provider}")

    @classmethod
    def compatible_jobs(cls) -> List:
        return [EcoLogitsGenAIExternalAPIJob]

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