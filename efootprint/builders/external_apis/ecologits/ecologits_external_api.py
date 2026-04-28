import math
from typing import List, Optional

from ecologits.electricity_mix_repository import electricity_mixes
from ecologits.impacts.llm import compute_llm_impacts_dag
from ecologits.model_repository import ModelRepository
from ecologits.model_repository import ParametersMoE
from ecologits.tracers.utils import PROVIDER_CONFIG_MAP
from ecologits.utils.range_value import ValueOrRange

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_dict import ExplainableDict
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
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
    """Virtual server backing an {class:EcoLogitsGenAIExternalAPI}. Aggregates the per-request fabrication and energy footprints emitted by the underlying EcoLogits model into hourly footprints."""

    param_descriptions = {}

    @property
    def external_api(self) -> Optional["EcoLogitsGenAIExternalAPI"]:
        if self.modeling_obj_containers:
            return self.modeling_obj_containers[0]
        return None

    @property
    def jobs(self) -> List["EcoLogitsGenAIExternalAPIJob"]:
        if self.external_api:
            return self.external_api.jobs
        return []
    
    @property
    def external_api_model_name(self) -> str:
        if self.external_api:
            return str(self.external_api.model_name)
        return "no external API"

    def update_instances_fabrication_footprint(self) -> None:
        """Hourly fabrication-phase footprint of the model server, equal to per-request embodied GWP times hourly request count, summed over jobs."""
        instances_fabrication_footprint = EmptyExplainableObject()

        for job in self.jobs:
            instances_fabrication_footprint += job.request_embodied_gwp * job.hourly_occurrences_across_usage_patterns

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Instances fabrication footprint for {self.external_api_model_name}")

    def update_instances_energy(self) -> None:
        """Hourly energy consumed by the model server, equal to per-request energy times hourly request count, summed over jobs."""
        instances_energy = EmptyExplainableObject()

        for job in self.jobs:
            instances_energy += job.request_energy * job.hourly_occurrences_across_usage_patterns

        self.instances_energy = instances_energy.set_label(f"Instances energy for {self.external_api_model_name}")

    def update_energy_footprint(self) -> None:
        """Hourly energy-use footprint of the model server, equal to per-request usage GWP times hourly request count, summed over jobs."""
        energy_footprint = EmptyExplainableObject()

        for job in self.jobs:
            energy_footprint += job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns

        self.energy_footprint = energy_footprint.set_label(f"Energy footprint for {self.external_api_model_name}")

    def update_dict_element_in_fabrication_impact_repartition_weights(self, job: "EcoLogitsGenAIExternalAPIJob"):
        self.fabrication_impact_repartition_weights[job] = (
            job.request_embodied_gwp * job.hourly_occurrences_across_usage_patterns
        ).set_label(f"{job.name} fabrication weight in impact repartition")

    def update_fabrication_impact_repartition_weights(self):
        """Per-job weights used to attribute the model server's fabrication footprint, proportional to per-request embodied GWP times hourly request volume."""
        self.fabrication_impact_repartition_weights = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_fabrication_impact_repartition_weights(job)

    def update_dict_element_in_usage_impact_repartition_weights(self, job: "EcoLogitsGenAIExternalAPIJob"):
        self.usage_impact_repartition_weights[job] = (
            job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns
        ).set_label(f"{job.name} usage weight in impact repartition")

    def update_usage_impact_repartition_weights(self):
        """Per-job weights used to attribute the model server's energy-use footprint, proportional to per-request usage GWP times hourly request volume."""
        self.usage_impact_repartition_weights = ExplainableObjectDict()
        for job in self.jobs:
            self.update_dict_element_in_usage_impact_repartition_weights(job)


class EcoLogitsGenAIExternalAPI(ExternalAPI):
    """An external generative-AI API (OpenAI, Anthropic, Mistral...) modelled through the EcoLogits library. Picks a model and provider; EcoLogits supplies parameter counts, throughput, datacenter location, and grid carbon intensity."""

    interactions = (
        "Pick {param:EcoLogitsGenAIExternalAPI.provider} and {param:EcoLogitsGenAIExternalAPI.model_name} "
        "from the EcoLogits catalog, then attach {class:EcoLogitsGenAIExternalAPIJob}s sized by output token "
        "count. EcoLogits queries are cached as calculated attributes so they fire only when the model changes.")

    param_descriptions = {
        "provider": (
            "Provider key from the EcoLogits catalog (anthropic, openai, mistralai...)."),
        "model_name": (
            "Specific model name from the chosen provider's EcoLogits catalog. Drives parameter counts, "
            "throughput, and the datacenter location used for grid carbon intensity."),
    }

    server_class = EcoLogitsGenAIExternalAPIServer

    default_values = {
        "provider": SourceObject("anthropic"),
        "model_name": SourceObject("claude-opus-4-5")
    }

    sorted_provider_names = sorted(list(dict.fromkeys([model.provider.name for model in models.list_models()])))
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
        self.provider = provider.set_label("Provider")
        self.model_name = model_name.set_label(f"Model used")
        self.model_total_params = EmptyExplainableObject()
        self.model_active_params = EmptyExplainableObject()
        self.tokens_per_second = EmptyExplainableObject()
        self.time_to_first_token = EmptyExplainableObject()
        self.datacenter_location = EmptyExplainableObject()
        self.data_center_pue = EmptyExplainableObject()
        self.average_carbon_intensity = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return super().calculated_attributes + [
            "model_total_params", "model_active_params", "tokens_per_second", "time_to_first_token",
            "datacenter_location", "data_center_pue", "average_carbon_intensity"]


    def _get_model_or_raise(self):
        model = models.find_model(provider=self.provider.value, model_name=self.model_name.value)
        if model is None:
            raise ValueError(
                f"Could not find model `{self.model_name.value}` for {self.provider.value} provider."
            )
        return model

    def update_model_total_params(self) -> None:
        """Total parameter count of the chosen model in billions, looked up in the EcoLogits model repository."""
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
        """Active parameter count per inference step in billions (less than total for mixture-of-experts models), looked up in the EcoLogits model repository."""
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

    def update_tokens_per_second(self) -> None:
        """Average generation throughput of the model in tokens per second, looked up in the EcoLogits model repository. Empty if the model does not publish a value."""
        model = self._get_model_or_raise()
        tps = model.deployment.tps if model.deployment else None
        if tps is None:
            self.tokens_per_second = EmptyExplainableObject(
                f"{self.model_name} token per second", left_parent=self.provider, right_parent=self.model_name,
                operator="query EcoLogits model repository with", source=llm_impacts_function_source)
        else:
            self.tokens_per_second = ExplainableQuantity(
                tps * ECOLOGITS_UNIT_MAPPING["tps"],
                f"{self.model_name} token per second",
                left_parent=self.provider,
                right_parent=self.model_name,
                operator="query EcoLogits model repository with",
                source=llm_impacts_function_source
            )

    def update_time_to_first_token(self) -> None:
        """Time between sending the prompt and receiving the first generated token, looked up in the EcoLogits model repository. Empty if the model does not publish a value."""
        model = self._get_model_or_raise()
        ttft = model.deployment.ttft if model.deployment else None
        if ttft is None:
            self.time_to_first_token = EmptyExplainableObject(
                f"{self.model_name} time to first token", left_parent=self.provider, right_parent=self.model_name,
                operator="query EcoLogits model repository with", source=llm_impacts_function_source)
        else:
            self.time_to_first_token = ExplainableQuantity(
                ttft * ECOLOGITS_UNIT_MAPPING["ttft"],
                f"{self.model_name} time to first token",
                left_parent=self.provider,
                right_parent=self.model_name,
                operator="query EcoLogits model repository with",
                source=llm_impacts_function_source
            )

    def update_datacenter_location(self) -> None:
        """Geographic zone where the provider's datacenter runs, looked up in the EcoLogits provider config. Drives which electricity mix is applied."""
        datacenter_location = PROVIDER_CONFIG_MAP[self.provider.value].datacenter_location
        self.datacenter_location = ExplainableObject(
            datacenter_location,
            f"Datacenter location for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits provider config",
            source=llm_impacts_function_source,
        )

    def update_data_center_pue(self) -> None:
        """Power Usage Effectiveness of the provider's datacenter, looked up in the EcoLogits provider config."""
        datacenter_pue = _mean_value_or_range(PROVIDER_CONFIG_MAP[self.provider.value].datacenter_pue)
        self.data_center_pue = ExplainableQuantity(
            datacenter_pue * u.dimensionless,
            f"Datacenter PUE for {self.provider}",
            left_parent=self.provider,
            operator="query EcoLogits provider config",
            source=llm_impacts_function_source,
        )

    def update_average_carbon_intensity(self) -> None:
        """Average grid carbon intensity at the datacenter location, looked up in the EcoLogits electricity mix repository."""
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
    """One inference call against an {class:EcoLogitsGenAIExternalAPI}, sized by the average output token count. Per-request energy and embodied GWP are computed from the EcoLogits impact DAG."""

    param_descriptions = {
        "external_api": (
            "{class:EcoLogitsGenAIExternalAPI} the call is routed to."),
        "output_token_count": (
            "Average number of tokens generated per call. Drives generation latency, energy use, and embodied "
            "GWP through the EcoLogits impact model."),
    }

    default_values = {
        "output_token_count": SourceValue(1000 * u.dimensionless)
    }
    def __init__(self, name: str, external_api: EcoLogitsGenAIExternalAPI, output_token_count: ExplainableQuantity):
        super().__init__(name=name, external_api=external_api, data_transferred=SourceValue(0 * u.MB),
                         data_stored=SourceValue(0 * u.MB_stored), request_duration=SourceValue(0 * u.s),
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
        """Data transferred per call, estimated as 5 bytes per token (4 bytes UTF-8 plus 1 byte JSON overhead) times the output token count."""
        # One token is approximately 4 characters (4 bytes) + 1 byte json overhead
        bytes_per_token = ExplainableQuantity(5 * u.B, label="Bytes per token")
        self.data_transferred = (bytes_per_token * self.output_token_count).to(u.kB).set_label(
            f"Data transferred for {self.external_api.model_name}")

    def update_request_duration(self):
        """Request duration of one call, equal to the generation latency derived from EcoLogits."""
        self.request_duration = self.generation_latency.copy()

    def update_hourly_occurrences_across_usage_patterns(self):
        """Hourly count of occurrences of this job summed across all usage patterns that trigger it."""
        self.hourly_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_occurrences_per_usage_pattern", "occurrences")

    def update_impacts(self) -> None:
        """Cached EcoLogits impact dictionary for one call, computed from the model parameters, output token count, and grid carbon intensity. Subsequent updates extract individual fields from this dictionary."""
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
            tps = self.external_api.tokens_per_second.value.magnitude
            if not isinstance(self.external_api.tokens_per_second, EmptyExplainableObject) else None,
            ttft = self.external_api.time_to_first_token.value.magnitude
            if not isinstance(self.external_api.time_to_first_token, EmptyExplainableObject) else None,
        )

        impacts = ExplainableDict(
            impacts, f"Ecologits impacts", left_parent=self.external_api.model_active_params,
            right_parent=self.external_api.model_total_params,
            operator="compute impacts with EcoLogits compute_llm_impacts_dag function"
            ).generate_explainable_object_with_logical_dependency(
            self.output_token_count).generate_explainable_object_with_logical_dependency(
            self.external_api.average_carbon_intensity).generate_explainable_object_with_logical_dependency(
            self.external_api.tokens_per_second).generate_explainable_object_with_logical_dependency(
            self.external_api.time_to_first_token)
        impacts.source = compute_llm_impacts_dag_source

        self.impacts = impacts

    def update_ecologits_calculated_attribute(self, attribute_name: str) -> None:
        """Helper called by every auto-generated ``update_<ecologits_attr>`` method to read one field out of the cached EcoLogits impact dictionary, attach the right unit, and wire its EcoLogits formula and ancestors for explainability."""
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
        if ecologits_unit == u.kg and value.magnitude < 0.01:
            value = value.to(u.g)
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
    update_method.__doc__ = (
        f"Extracts the {attribute_name} field from the cached EcoLogits impact dictionary on this job, "
        f"converted into a typed e-footprint quantity.")
    return update_method


# Auto-generate update methods for each ecologits calculated attribute
for attr_name in ecologits_calculated_attributes:
    method_name = f"update_{attr_name}"
    setattr(EcoLogitsGenAIExternalAPIJob, method_name, _create_update_method(attr_name))
