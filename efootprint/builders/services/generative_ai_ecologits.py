from typing import List

from ecologits.model_repository import ModelRepository
from ecologits.utils.range_value import RangeValue

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.source_objects import Source, SourceValue, Sources, SourceObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.builders.services.service_job_base_class import ServiceJob
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.builders.services.service_base_class import Service
from efootprint.constants.units import u

models = ModelRepository.from_json()

ecologits_source = Source("Ecologits", "https://github.com/genai-impact/ecologits")


class GenAIModel(Service):
    @classmethod
    def default_values(cls):
        return {
            "provider": SourceObject("mistralai"),
            "model_name": SourceObject("open-mistral-7b"),
            "nb_of_bits_per_parameter": SourceValue(16 * u.dimensionless, source=Sources.HYPOTHESIS),
            "gpu_latency_alpha": SourceValue(8.02e-4 * 1e-9 * u.s, source=ecologits_source),
            "gpu_latency_beta": SourceValue(2.23e-2 * u.s, source=ecologits_source),
            "llm_memory_factor": SourceValue(1.2 * u.dimensionless, source=ecologits_source),
            "bits_per_token": SourceValue(24 * u.dimensionless)
            }

    @classmethod
    def list_values(cls):
        sorted_provider_names = sorted(list(set([model.provider.name for model in models.list_models()])))
        return {"provider": [SourceObject(provider_name) for provider_name in sorted_provider_names]}

    @classmethod
    def conditional_list_values(cls):
        values = {}
        for provider in cls.list_values()["provider"]:
            values[provider] = [SourceObject(model.name) for model in models.list_models()
                                if model.provider.name == provider.value]

        return {"model_name": {"depends_on": "provider", "conditional_list_values": values}}

    def __setattr__(self, name, input_value, check_input_validity=True):
        if name == "provider" and self.trigger_modeling_updates:
            raise PermissionError("The provider of a GenAIModel cannot be changed after initialization. "
                                  "Use a ModelingUpdate to update both provider and a compatible model name.")
        super().__setattr__(name, input_value, check_input_validity=check_input_validity)

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject, server: GPUServer,
                 nb_of_bits_per_parameter: ExplainableQuantity, llm_memory_factor: ExplainableQuantity,
                 gpu_latency_alpha: ExplainableQuantity, gpu_latency_beta: ExplainableQuantity,
                 bits_per_token: ExplainableQuantity):
        super().__init__(name=name, server=server)
        self.provider = provider.set_label(str(provider))
        self.model_name = model_name.set_label(f"{provider} model used")
        self.nb_of_bits_per_parameter = nb_of_bits_per_parameter.set_label(f"{self.name} nb of bits per parameter")
        self.llm_memory_factor = (llm_memory_factor.set_label
                                  (f"{self.name} ratio between GPU memory footprint and model size"))
        self.gpu_latency_alpha = gpu_latency_alpha.set_label("GPU latency per active parameter and output token")
        self.gpu_latency_beta = gpu_latency_beta.set_label("Base GPU latency per output_token")
        self.bits_per_token = bits_per_token.set_label(f"Number of bits per token")
        self.active_params = EmptyExplainableObject()
        self.total_params = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return ["active_params", "total_params", "base_ram_consumption"]

    def update_active_params(self):
        model = models.find_model(provider=self.provider.value, model_name=self.model_name.value)
        if isinstance(model.architecture.parameters, int) or isinstance(model.architecture.parameters, float):
            model_active_params_in_billion = model.architecture.parameters
        elif isinstance(model.architecture.parameters, RangeValue):
            model_active_params_in_billion = (model.architecture.parameters.min + model.architecture.parameters.max) / 2
        elif isinstance(model.architecture.parameters.active, RangeValue):
            model_active_params_in_billion = (model.architecture.parameters.active.min
                                              + model.architecture.parameters.active.max) / 2
        else:
            model_active_params_in_billion = model.architecture.parameters.active

        self.active_params = ExplainableQuantity(
            model_active_params_in_billion * 1e9 * u.dimensionless,
            f"{self.model_name} from {self.provider} nb of active parameters", 
            left_parent=self.provider, right_parent=self.model_name, operator="query EcoLogits data with",
            source=ecologits_source)

    def update_total_params(self):
        model = models.find_model(provider=self.provider.value, model_name=self.model_name.value)
        if isinstance(model.architecture.parameters, int) or isinstance(model.architecture.parameters, float):
            model_total_params_in_billion = model.architecture.parameters
        elif isinstance(model.architecture.parameters, RangeValue):
            model_total_params_in_billion = (model.architecture.parameters.min + model.architecture.parameters.max) / 2
        elif isinstance(model.architecture.parameters.total, RangeValue):
            model_total_params_in_billion = (model.architecture.parameters.total.min
                                              + model.architecture.parameters.total.max) / 2
        else:
            model_total_params_in_billion = model.architecture.parameters.total

        self.total_params = ExplainableQuantity(
            model_total_params_in_billion * 1e9 * u.dimensionless,
            f"{self.model_name} from {self.provider} total nb of parameters",
            left_parent=self.provider, right_parent=self.model_name, operator="query EcoLogits data with",
            source=ecologits_source)

    def update_base_ram_consumption(self):
        self.base_ram_consumption = (
                self.llm_memory_factor * self.total_params * self.nb_of_bits_per_parameter).to(u.GB).set_label(
            f"{self.name} base RAM consumption")



class GenAIJob(ServiceJob):
    @classmethod
    def default_values(cls):
        return {
            "output_token_count": SourceValue(1000 * u.dimensionless)
        }

    def __init__(self, name: str, service: GenAIModel, output_token_count: ExplainableQuantity):
        """
        Create a Job object requesting the Gen AI model.

        Args:
            service (GenAIModel): The Gen AI model to use for the job.
            output_token_count (SourceValue): The number of output tokens for the job.
        Returns:
            Job: An object that represents the resources needed for the task.
        """
        super().__init__(
            name or f"request to {service.model_name} installed on {service.server.name}",
            service,
            data_transferred=SourceValue(0 * u.kB),
            data_stored=SourceValue(0 * u.kB),
            request_duration=SourceValue(0 * u.s),
            compute_needed=SourceValue(0 * u.gpu),
            ram_needed=SourceValue(0 * u.GB))
        self.output_token_count = output_token_count.set_label(f"{self.name} output token count")
        self.output_token_weights = EmptyExplainableObject()

    @property
    def calculated_attributes(self) -> List[str]:
        return (["output_token_weights", "data_stored", "data_transferred", "request_duration", "ram_needed",
                 "compute_needed"] + super().calculated_attributes)

    def update_output_token_weights(self):
        self.output_token_weights = (self.output_token_count * self.service.bits_per_token).to(u.kB).set_label(
            f"{self.name} output token weights")

    def update_data_stored(self):
        self.data_stored = (SourceValue(100 * u.kB) + self.output_token_weights).set_label(f"{self.name} data stored")

    def update_data_transferred(self):
        self.data_transferred = (SourceValue(100 * u.kB) + self.output_token_weights).set_label(
            f"{self.name} data transferred")

    def update_request_duration(self):
        gpu_latency = self.output_token_count * (
            self.service.gpu_latency_alpha * self.service.active_params + self.service.gpu_latency_beta)
        self.request_duration = gpu_latency.set_label(f"{self.name} request duration")

    def update_ram_needed(self):
        self.ram_needed = SourceValue(0 * u.GB).set_label(
            f"No additional GPU RAM needed because model is already loaded in memory")

    def update_compute_needed(self):
        self.compute_needed = (
            (self.service.llm_memory_factor * self.service.active_params * self.service.nb_of_bits_per_parameter
             / self.server.ram_per_gpu)).to(u.gpu).set_label(f"{self.name} nb of required GPUs during inference")
