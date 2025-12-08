from typing import List

from ecologits.model_repository import ModelRepository

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, Source
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.builders.external_apis.ecologits.ecologits_dag_structure import ECOLOGITS_DEPENDENCY_GRAPH, get_formula
from efootprint.builders.external_apis.ecologits.ecologits_explainable_object import EcoLogitsExplainableObject
from efootprint.builders.external_apis.ecologits.ecologits_model import EcoLogitsModel
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI
from efootprint.constants.units import u
from efootprint.core.usage.job import JobBase

models = ModelRepository.from_json()

ecologits_source = Source("Ecologits", "https://github.com/genai-impact/ecologits")

ecologits_calculated_attributes = [elt for elt in ECOLOGITS_DEPENDENCY_GRAPH.keys() if elt in ECOLOGITS_UNIT_MAPPING]
ecologits_input_hypotheses = [elt for elt in ECOLOGITS_UNIT_MAPPING if elt not in ecologits_calculated_attributes]


class EcoLogitsGenAIExternalAPI(ExternalAPI):
    default_values = {
        "provider": SourceObject("mistralai"),
        "model_name": SourceObject("open-mistral-7b")
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
        self.provider = provider.set_label(str(provider))
        self.model_name = model_name.set_label(f"{provider} model used")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List:
        return []

    @property
    def jobs(self):
        return self.modeling_obj_containers

    def update_instances_fabrication_footprint(self) -> None:
        instances_fabrication_footprint = EmptyExplainableObject()

        for job in self.jobs:
            instances_fabrication_footprint += job.request_embodied_gwp * job.hourly_occurrences_across_usage_patterns

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Instances fabrication footprint for {self.model_name}")

    def update_instances_energy(self) -> None:
        instances_energy = EmptyExplainableObject()

        for job in self.jobs:
            instances_energy += job.request_energy_energy * job.hourly_occurrences_across_usage_patterns

        self.instances_energy = instances_energy.set_label(f"Instances energy for {self.model_name}")

    def update_energy_footprint(self) -> None:
        energy_footprint = EmptyExplainableObject()

        for job in self.jobs:
            energy_footprint += job.request_usage_gwp * job.hourly_occurrences_across_usage_patterns

        self.energy_footprint = energy_footprint.set_label(f"Energy footprint for {self.model_name}")


class EcoLogitsGenAIExternalAPIJob(JobBase):
    default_values = {
        "output_token_count": SourceObject(1000 * u.dimensionless)
    }
    def __init__(self, name: str, external_api: EcoLogitsGenAIExternalAPI, output_token_count: ExplainableQuantity):
        super().__init__(name=name, data_transferred=SourceValue(0 * u.MB), data_stored=SourceValue(0 * u.MB),
                 request_duration=SourceValue(0 * u.s), compute_needed = SourceValue(0 * u.cpu_core),
                 ram_needed = SourceValue(0 * u.GB_ram))
        self.external_api = external_api
        self.output_token_count = output_token_count.set_label(f"Output token count for {self.external_api.model_name}")

        self.hourly_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.ecologits_modeling = EmptyExplainableObject()
        for ecologits_attr in ecologits_calculated_attributes:
            setattr(self, ecologits_attr, EmptyExplainableObject())

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ExternalAPI]:
        return [self.external_api]

    @property
    def calculated_attributes(self) -> List[str]:
        return (["data_transferred", "hourly_occurrences_across_usage_patterns", "ecologits_modeling"]
                + ecologits_calculated_attributes)

    def update_data_transferred(self):
        # One token is approximately 4 characters (4 bytes) + 1 byte json overhead
        bytes_per_token = SourceValue(5 * u.B)
        self.data_transferred = (bytes_per_token * self.output_token_count).set_label(
            f"Data transferred for {self.external_api.model_name}")

    def update_hourly_occurrences_across_usage_patterns(self):
        self.hourly_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_occurrences_per_usage_pattern", "occurrences")

    def update_ecologits_modeling(self) -> None:
        ecologits_modeling = EcoLogitsModel(
            self.external_api.provider.value, self.external_api.model_name.value, self.output_token_count.value,
            request_latency=None, electricity_mix_zone=None)

        provider_and_model_name = ExplainableObject(
            self.external_api.provider.value + " " + self.external_api.model_name.value, "Provider and model name",
        left_parent=self.external_api.provider, right_parent=self.external_api.model_name, operator="concat")

        self.ecologits_modeling = ExplainableObject(
            ecologits_modeling, "Ecologits modeling", left_parent=provider_and_model_name,
            right_parent=self.output_token_count, operator="combined in EcoLogits computation",source=ecologits_source)

    def update_ecologits_calculated_attribute(self, attribute_name: str) -> None:
        if attribute_name not in self.ecologits_modeling.value.impacts:
            raise ValueError(f"Ecologits modeling has no attribute `{attribute_name}`.")
        attribute_value = self.ecologits_modeling.value.impacts[attribute_name] * ECOLOGITS_UNIT_MAPPING[attribute_name]
        ancestors = {}
        for ancestor in ECOLOGITS_DEPENDENCY_GRAPH[attribute_name]:
            if hasattr(self.ecologits_modeling, ancestor):
                ancestors[ancestor] = getattr(self.ecologits_modeling, ancestor) * ECOLOGITS_UNIT_MAPPING[ancestor]
        formula = get_formula(attribute_name)
        attribute_explainable = EcoLogitsExplainableObject(
            attribute_value, f"Ecologits {attribute_name} for {self.external_api.model_name}",
            parent=self.ecologits_modeling, ancestors=ancestors, formula=formula, source=ecologits_source)
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
