from typing import List, Optional, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.builders.external_apis.external_api_base_class import ExternalAPIServer
from efootprint.constants.units import u
from efootprint.core.lifecycle_phases import LifeCyclePhases

if TYPE_CHECKING:
    from efootprint.builders.external_apis.ecologits.ecologits_external_api import (
        EcoLogitsGenAIExternalAPI, EcoLogitsGenAIExternalAPIJob)


class EcoLogitsExternalAPIServerBase(ExternalAPIServer):
    """Shared aggregator for the EcoLogits LLM and video Server classes. Reads per-request
    embodied / energy / usage GWP off the API's jobs and sums them into the three standard hourly
    footprints; exposes the matching per-job repartition weights. Concrete subclasses only need to
    declare their own class-level docstring and `param_descriptions`."""

    param_descriptions = {}

    @staticmethod
    def _spread_over_request_duration(job, per_request_value):
        """Spread a per-request total over the hours the request runs, mirroring the network/storage
        per-hour-spread idiom: (per_request_value * 1h / request_duration) * avg hourly occurrences.
        Returns an empty object when the per-request value isn't set yet (e.g. a job with no usage
        patterns), whose request_duration is still its 0 s default."""
        if isinstance(per_request_value, EmptyExplainableObject):
            return EmptyExplainableObject()
        per_hour_value = per_request_value * ExplainableQuantity(1 * u.hour, "one hour") / job.request_duration
        return per_hour_value * job.hourly_avg_occurrences_across_usage_patterns

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
        """Hourly fabrication-phase footprint of the model server: each job's per-request embodied GWP spread over its request_duration (per-request * 1h / request_duration * hourly average occurrences across usage patterns), summed over jobs."""
        instances_fabrication_footprint = EmptyExplainableObject()

        for job in self.jobs:
            instances_fabrication_footprint += self._spread_over_request_duration(job, job.request_embodied_gwp)

        self.instances_fabrication_footprint = instances_fabrication_footprint.set_label(
            f"Instances fabrication footprint for {self.external_api_model_name}")

    def update_instances_energy(self) -> None:
        """Hourly energy consumed by the model server: each job's per-request energy spread over its request_duration (per-request * 1h / request_duration * hourly average occurrences across usage patterns), summed over jobs."""
        instances_energy = EmptyExplainableObject()

        for job in self.jobs:
            instances_energy += self._spread_over_request_duration(job, job.request_energy)

        self.instances_energy = instances_energy.set_label(f"Instances energy for {self.external_api_model_name}")

    def update_energy_footprint(self) -> None:
        """Hourly energy-use footprint of the model server: each job's per-request usage GWP spread over its request_duration (per-request * 1h / request_duration * hourly average occurrences across usage patterns), summed over jobs."""
        energy_footprint = EmptyExplainableObject()

        for job in self.jobs:
            energy_footprint += self._spread_over_request_duration(job, job.request_usage_gwp)

        self.energy_footprint = energy_footprint.set_label(f"Energy footprint for {self.external_api_model_name}")

    def job_request_footprint(self, job: "EcoLogitsGenAIExternalAPIJob", phase: LifeCyclePhases):
        """The job's duration-aware request footprint for a life-cycle phase: per-request embodied (fabrication)
        or usage (energy) GWP spread over request_duration times hourly average occurrences — the per-job
        summand of the matching eager footprint total."""
        per_request_gwp = (job.request_embodied_gwp if phase == LifeCyclePhases.MANUFACTURING
                           else job.request_usage_gwp)
        return self._spread_over_request_duration(job, per_request_gwp)
