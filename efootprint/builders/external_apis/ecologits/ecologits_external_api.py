import math
from typing import List

from ecologits.electricity_mix_repository import electricity_mixes
from ecologits.impacts.llm import compute_llm_impacts_dag
from ecologits.model_repository import ModelRepository
from ecologits.model_repository import ParametersMoE
from ecologits.tracers.utils import PROVIDER_CONFIG_MAP
from ecologits.utils.range_value import ValueOrRange

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_dag_structure import ECOLOGITS_DEPENDENCY_GRAPH, get_formula
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
from efootprint.builders.external_apis.external_api_job_base_class import ExternalAPIJob
from efootprint.constants.units import u

models = ModelRepository.from_json()

ecologits_source = Source("Ecologits", "https://github.com/genai-impact/ecologits")
llm_impacts_function_source = Source(
    "Ecologits llm_impacts function",
    "https://github.com/genai-impact/ecologits/blob/main/ecologits/tracers/utils.py#L60")
compute_llm_impacts_dag_source = Source("Ecologits compute_llm_impacts_dag function",
                                        "https://github.com/genai-impact/ecologits/blob/main/ecologits/impacts/llm.py")

ecologits_calculated_attributes = [
    elt for elt in ECOLOGITS_DEPENDENCY_GRAPH.keys() if elt in ECOLOGITS_UNIT_MAPPING
    and not elt.endswith("_wue") and not elt.endswith("_pe") and not elt.endswith("_adpe")]
ecologits_input_hypotheses = [elt for elt in ECOLOGITS_UNIT_MAPPING if elt not in ecologits_calculated_attributes]


def _mean_value_or_range(value_or_range: ValueOrRange) -> float:
    if isinstance(value_or_range, (int, float)):
        return float(value_or_range)
    return (value_or_range.min + value_or_range.max) / 2


class EcoLogitsGenAIExternalAPIServer(ExternalAPIServer):
    @property
    def external_api(self) -> "EcoLogitsGenAIExternalAPI":
        return self.modeling_obj_containers[0]

    @property
    def jobs(self) -> List["EcoLogitsGenAIExternalAPIJob"]:
        return self.external_api.jobs

    def update_instances_fabrication_footprint(self) -> None:
        instances_fabrication_footprint = EmptyExplainableObject()

        for job in self.jobs:
            instances_fabrication_footprint += job.request_embodied_gwp * job.hourly_occurrences_across_usage_patterns

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Instances fabrication footprint for {self.external_api.model_name}")

    def update_instances_energy(self) -> None:
        instances_energy = EmptyExplainableObject()

        for job in self.jobs:
            instances_energy += job.request_energy * job.hourly_occurrences_across_usage_patterns

        self.instances_energy = instances_energy.set_label(f"Instances energy for {self.external_api.model_name}")

    def update_energy_footprint(self) -> None:
        energy_footprint = EmptyExplainableObject()

        for job in self.jobs:
            energy_footprint += job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns

        self.energy_footprint = energy_footprint.set_label(f"Energy footprint for {self.external_api.model_name}")


class EcoLogitsGenAIExternalAPI(ExternalAPI):
    server_class = EcoLogitsGenAIExternalAPIServer

    default_values = {
        "provider": SourceObject("anthropic"),
        "model_name": SourceObject("claude-opus-4-5")
    }

    sorted_provider_names = sorted(list(set([model.provider.name for model in models.list_models()])))
    list_values = {"provider": [SourceObject(provider_name) for provider_name in sorted_provider_names]}

    @staticmethod
    def generate_conditional_list_values(list_values):
        values = {}
        for provider in list_values["provider"]:
            values[provider] = [SourceObject(model.name) for model in models.list_models()
                                if model.provider.name == provider.value]

        return {"model_name": {"depends_on": "provider", "conditional_list_values": values}}

    conditional_list_values = generate_conditional_list_values(list_values)

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject):
        super().__init__(name=name)
        self.provider = provider.set_label(f"{self.name} provider")
        self.model_name = model_name.set_label(f"Model used")
        self.model_total_params = EmptyExplainableObject()
        self.model_active_params = EmptyExplainableObject()
        self.datacenter_location = EmptyExplainableObject()
        self.data_center_pue = EmptyExplainableObject()
        self.average_carbon_intensity = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return super().calculated_attributes + [
            "model_total_params", "model_active_params", "datacenter_location", "data_center_pue",
            "average_carbon_intensity"]


    def _get_model_or_raise(self):
        model = models.find_model(provider=self.provider.value, model_name=self.model_name.value)
        if model is None:
            raise ValueError(
                f"Could not find model `{self.model_name.value}` for {self.provider.value} provider."
            )
        return model

    def update_model_total_params(self) -> None:
        model = self._get_model_or_raise()
        params = model.architecture.parameters
        if isinstance(params, ParametersMoE):
            model_total_params = _mean_value_or_range(params.total)
        else:
            model_total_params = _mean_value_or_range(params)

        self.model_total_params = ExplainableQuantity(
            model_total_params * ECOLOGITS_UNIT_MAPPING["model_total_parameter_count"],
            f"{self.model_name} total parameter count (in billions)",
            left_parent=self.provider,
            right_parent=self.model_name,
            operator="query EcoLogits model repository with",
            source=llm_impacts_function_source,
        )

    def update_model_active_params(self) -> None:
        model = self._get_model_or_raise()
        params = model.architecture.parameters
        if isinstance(params, ParametersMoE):
            model_active_params = _mean_value_or_range(params.active)
        else:
            model_active_params = _mean_value_or_range(params)

        self.model_active_params = ExplainableQuantity(
            model_active_params * ECOLOGITS_UNIT_MAPPING["model_active_parameter_count"],
            f"{self.model_name} active parameter count (in billions)",
            left_parent=self.provider,
            right_parent=self.model_name,
            operator="query EcoLogits model repository with",
            source=llm_impacts_function_source,
        )

    def update_datacenter_location(self) -> None:
        datacenter_location = PROVIDER_CONFIG_MAP[self.provider.value].datacenter_location
        self.datacenter_location = ExplainableObject(
            datacenter_location,
            f"Datacenter location for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits provider config",
            source=llm_impacts_function_source,
        )

    def update_data_center_pue(self) -> None:
        datacenter_pue = _mean_value_or_range(PROVIDER_CONFIG_MAP[self.provider.value].datacenter_pue)
        self.data_center_pue = ExplainableQuantity(
            datacenter_pue * u.dimensionless,
            f"Datacenter PUE for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits provider config",
            source=llm_impacts_function_source,
        )

    def update_average_carbon_intensity(self) -> None:
        electricity_mix_zone = self.datacenter_location.value
        if electricity_mix_zone is None:
            electricity_mix_zone = "WOR"
        if_electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)
        if if_electricity_mix is None:
            raise ValueError(f"Could not find electricity mix for `{electricity_mix_zone}` zone.")
        average_carbon_intensity = if_electricity_mix.gwp
        self.average_carbon_intensity = ExplainableQuantity(
            average_carbon_intensity * ECOLOGITS_UNIT_MAPPING["if_electricity_mix_gwp"],
            f"Average carbon intensity of electricity mix for {self.provider}",
            left_parent=self.datacenter_location,
            operator="query EcoLogits electricity mix repository with datacenter location",
            source=llm_impacts_function_source,
        )


class EcoLogitsGenAIExternalAPIJob(ExternalAPIJob):
    default_values = {
        "output_token_count": SourceValue(1000 * u.dimensionless)
    }
    def __init__(self, name: str, external_api: EcoLogitsGenAIExternalAPI, output_token_count: ExplainableQuantity):
        super().__init__(name=name, external_api=external_api, data_transferred=SourceValue(0 * u.MB),
                         data_stored=SourceValue(0 * u.MB), request_duration=SourceValue(0 * u.s),
                         compute_needed = SourceValue(0 * u.cpu_core), ram_needed = SourceValue(0 * u.GB_ram))
        self.output_token_count = output_token_count.set_label(f"Output token count for {self.external_api.model_name}")

        self.hourly_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.impacts = EmptyExplainableObject()
        for ecologits_attr in ecologits_calculated_attributes:
            setattr(self, ecologits_attr, EmptyExplainableObject())

    @property
    def calculated_attributes(self) -> List[str]:
        return (["data_transferred", "impacts"] + ecologits_calculated_attributes
                + ["request_duration"]
                + super().calculated_attributes +
                ["hourly_occurrences_across_usage_patterns"])

    def update_data_transferred(self):
        # One token is approximately 4 characters (4 bytes) + 1 byte json overhead
        bytes_per_token = ExplainableQuantity(5 * u.B, label="Bytes per token")
        self.data_transferred = (bytes_per_token * self.output_token_count).to(u.kB).set_label(
            f"Data transferred for {self.external_api.model_name}")

    def update_request_duration(self):
        self.request_duration = self.generation_latency.copy()

    def update_hourly_occurrences_across_usage_patterns(self):
        self.hourly_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_occurrences_per_usage_pattern", "occurrences")

    def update_impacts(self) -> None:
        datacenter_wue = _mean_value_or_range(PROVIDER_CONFIG_MAP[self.external_api.provider.value].datacenter_wue)

        impacts = compute_llm_impacts_dag(
            model_active_parameter_count=self.external_api.model_active_params.value.magnitude,
            model_total_parameter_count=self.external_api.model_total_params.value.magnitude,
            output_token_count=self.output_token_count.value.magnitude,
            request_latency=math.inf,
            if_electricity_mix_adpe=0,
            if_electricity_mix_pe=0,
            if_electricity_mix_gwp=self.external_api.average_carbon_intensity.value.magnitude,
            if_electricity_mix_wue=0,
            datacenter_pue=self.external_api.data_center_pue.value.magnitude,
            datacenter_wue=datacenter_wue,
        )

        self.impacts = ExplainableDict(
            impacts, f"Ecologits impacts for {self.name}", left_parent=self.external_api.model_active_params,
            right_parent=self.external_api.model_total_params,
            operator="compute impacts with EcoLogits compute_llm_impacts_dag function",
            source=compute_llm_impacts_dag_source).generate_explainable_object_with_logical_dependency(
            self.output_token_count).generate_explainable_object_with_logical_dependency(
            self.external_api.average_carbon_intensity)

    def update_ecologits_calculated_attribute(self, attribute_name: str) -> None:
        if attribute_name not in self.impacts.value:
            raise ValueError(f"Ecologits impacts has no attribute `{attribute_name}`.")
        attribute_value = self.impacts.value[attribute_name]
        ancestors = {}
        for ancestor in ECOLOGITS_DEPENDENCY_GRAPH[attribute_name]:
            if ancestor in self.impacts.value:
                ancestors[ancestor] = self.impacts.value[ancestor]
        formula = get_formula(attribute_name)
        ecologits_unit = ECOLOGITS_UNIT_MAPPING[attribute_name]
        value = attribute_value * ecologits_unit
        if ecologits_unit == u.kWh and value.magnitude < 0.01:
            value = value.to(u.Wh)
        attribute_explainable = EcoLogitsExplainableQuantity(
            value,
            f"Ecologits {attribute_name} for {self.external_api.model_name}",
            parent=self.impacts, operator="extraction", ancestors=dict(sorted(ancestors.items())), formula=formula,
            source=compute_llm_impacts_dag_source)
        setattr(self, attribute_name, attribute_explainable)


def _create_update_method(attribute_name: str):
    """Factory function to create update methods for ecologits calculated attributes."""
    def update_method(self):
        self.update_ecologits_calculated_attribute(attribute_name)
    update_method.__name__ = f"update_{attribute_name}"
    return update_method


# Auto-generate update methods for each ecologits calculated attribute
for attr_name in ecologits_calculated_attributes:
    method_name = f"update_{attr_name}"
    setattr(EcoLogitsGenAIExternalAPIJob, method_name, _create_update_method(attr_name))
