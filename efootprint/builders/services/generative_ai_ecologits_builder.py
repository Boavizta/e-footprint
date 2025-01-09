from ecologits.model_repository import ModelRepository
from efootprint.abstract_modeling_classes.source_objects import Source, SourceValue, Sources
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.constants.units import u
from efootprint.core.usage.job import Job
from efootprint.logger import logger

models = ModelRepository.from_json()

ecologits_source = Source("Ecologits", "https://github.com/genai-impact/ecologits")

NB_OF_BITS_PER_PARAMETER = ExplainableQuantity(
    16 * u.dimensionless, "nb of bits per parameter", source=Sources.HYPOTHESIS)
GPU_MEMORY = ExplainableQuantity(80 * u.GB, "GPU RAM", source=Sources.HYPOTHESIS)
GPU_LATENCY_ALPHA = ExplainableQuantity(8.02e-4 * 1e-9 * u.s, "GPU latency per active parameter and output token",
                                        source=ecologits_source)
GPU_LATENCY_BETA = ExplainableQuantity(2.23e-2 * u.s, "Base GPU latency per output_token", source=ecologits_source)

llm_memory_factor = SourceValue(1.2 * u.dimensionless, label="llm memory factor", source=ecologits_source)
nb_of_cpu_cores_per_gpu = SourceValue(1 * u.core, label="abstract nb of CPU cores per GPU", source=Sources.HYPOTHESIS)


class GenAIModel:
    def __init__(self, provider, model_name, server, install_on_server=True):
        self.provider = provider
        self.model_name = model_name
        self.server = server
        self.active_params = None
        self.total_params = None
        self.get_model_active_and_total_parameters()
        self.gpu_ram_needed = (llm_memory_factor * self.total_params * NB_OF_BITS_PER_PARAMETER).to(u.GB)
        self.nb_of_required_gpus_during_inference = (
            (llm_memory_factor * self.active_params * NB_OF_BITS_PER_PARAMETER / GPU_MEMORY).to(u.dimensionless))
        if install_on_server:
            self.server.base_ram_consumption = (
                    self.server.base_ram_consumption + self.gpu_ram_needed.set_label(f"{self.model_name} RAM")
            ).set_label(f"{self.server.name} base ram consumption after installation of {self.model_name}")

    def __str__(self):
        return f"{self.provider}/{self.model_name}"

    def get_model_active_and_total_parameters(self):
        """
        Retrieve the number of active and total parameters of the model attached to self.

        This method uses ecologits’ ModelRepository to fetch information about the model. If the model is not found,
        an error message is displayed.

        The retrieved values are then stored in the `active_params` and `total_params` attributes of self.
        These values are transformed into `ExplainableQuantity` objects, which allow storing a value with its source.

        Returns:
            None
        """
        model = models.find_model(provider=self.provider, model_name=self.model_name)
        if model is None:
            logger.debug(f"Could not find model `{self.model_name}` for {self.provider} provider.")
            return None
        model_active_params_in_billion = model.active_parameters \
            or (model.active_parameters_range[0] + model.active_parameters_range[1]) / 2
        model_total_params_in_billion = model.total_parameters \
            or (model.total_parameters_range[0] + model.total_parameters_range[1]) / 2

        self.active_params = ExplainableQuantity(
            model_active_params_in_billion * 1e9 * u.dimensionless,
            f"{self.model_name} from {self.provider} nb of active parameters", source=ecologits_source)

        self.total_params = ExplainableQuantity(
            model_total_params_in_billion * 1e9 * u.dimensionless,
            f"{self.model_name} from {self.provider} total nb of parameters", source=ecologits_source)

    def job(self, output_token_count: SourceValue):
        """
        Create a Job object for the model.

        This method takes a Storage object and a SourceValue object as parameters. It calculates the resources
        required to perform a task with the model, such as GPU latency and data storage needs.

        Args:
            output_token_count (SourceValue): The number of output tokens for the job.

        Returns:
            Job: An object that represents the resources needed for the task.
        """
        gpu_latency = output_token_count * (GPU_LATENCY_ALPHA * self.active_params + GPU_LATENCY_BETA)
        output_tokens_weight = output_token_count * SourceValue(24 * u.dimensionless, label="24 bits per token")

        return Job(
            f"request to {self.model_name} installed on {self.server.name}", self.server,
            data_upload=SourceValue(100 * u.kB),
            data_stored=SourceValue(100 * u.kB) + output_tokens_weight,
            data_download=SourceValue(100 * u.kB) + output_tokens_weight,
            request_duration=gpu_latency,
            cpu_needed=self.nb_of_required_gpus_during_inference * nb_of_cpu_cores_per_gpu,
            ram_needed=SourceValue(0 * u.GB))
