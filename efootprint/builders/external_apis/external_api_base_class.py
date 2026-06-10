from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.constants.units import u
from efootprint.core.attribution import Atom
from efootprint.core.lifecycle_phases import LifeCyclePhases


class ExternalAPIServer(ModelingObject):
    param_descriptions = {}

    def __init__(self, name: str):
        super().__init__(name=name)
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return []

    @property
    def external_api(self) -> "ExternalAPI":
        return self.modeling_obj_containers[0]

    calculated_attributes: List[str] = (
        ["instances_fabrication_footprint", "instances_energy", "energy_footprint"]
        + ModelingObject.calculated_attributes)

    @abstractmethod
    def update_instances_fabrication_footprint(self) -> None:
        pass

    @abstractmethod
    def update_instances_energy(self) -> None:
        pass

    @abstractmethod
    def update_energy_footprint(self) -> None:
        pass

    @abstractmethod
    def update_dict_element_in_fabrication_impact_repartition_weights(self, modeling_obj: "ModelingObject"):
        pass

    @abstractmethod
    def update_fabrication_impact_repartition_weights(self):
        pass

    @abstractmethod
    def update_dict_element_in_usage_impact_repartition_weights(self, modeling_obj: "ModelingObject"):
        pass

    @abstractmethod
    def update_usage_impact_repartition_weights(self):
        pass

    @abstractmethod
    def job_request_footprint(self, job: "ModelingObject", phase: LifeCyclePhases):
        """The job's duration-aware hourly request footprint for a life-cycle phase — the per-job summand the
        server's eager phase total sums over its jobs. Atom values are built from it, so Σ atoms == the total."""
        pass

    def attribution_atoms(self, phase: LifeCyclePhases):
        """One atom per containment cell of each job calling the API — a single demand stream relaying each
        job's duration-aware request footprint by its hourly cell occurrence shares (exact for a pure demand
        stream: the footprint is occurrence-driven, zero at zero-occurrence hours)."""
        for job in self.jobs:
            job_footprint = self.job_request_footprint(job, phase)
            for cell in job.attribution_cells:
                location = cell.step.name if cell.step is not None else f"{cell.rsn.name} via {cell.ef.name}"
                yield Atom(
                    source=self, stream="single", job=job, up=cell.up, step=cell.step, rsn=cell.rsn, ef=cell.ef,
                    value=(job_footprint * cell.hourly_share).to(u.kg).set_label(
                        f"{self.name} {phase.value.lower()} footprint via {job.name} "
                        f"in {location} ({cell.up.name})"))


class ExternalAPI(ModelingObject):
    """Abstract base for third-party APIs the digital service calls out to. Concrete subclasses (e.g. {class:EcoLogitsGenAIExternalAPI}) model the per-call carbon and energy cost of a specific provider; usage is driven by {class:Job}s that target the API, and an internal {class:ExternalAPIServer} aggregates the resulting hourly footprints."""

    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    param_descriptions = {}

    classes_outside_init_params_needed_for_generating_from_json = [ExternalAPIServer]
    server_class = ExternalAPIServer

    def __init__(self, name: str):
        super().__init__(name=name)
        self.server = None

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ExternalAPIServer]:
        return [self.server] + self.jobs

    def after_init(self):
        if not hasattr(self, "server") or self.server is None:
            self.server = self.server_class(name=f"{self.name} server")
        super().after_init()
        self.compute_calculated_attributes()

    @classmethod
    def compatible_jobs(cls) -> List:
        from efootprint.all_classes_in_order import EXTERNAL_API_JOB_CLASSES
        compatible_jobs = []
        for external_api_job_class in EXTERNAL_API_JOB_CLASSES:
            if cls in external_api_job_class.compatible_external_apis():
                compatible_jobs.append(external_api_job_class)

        return compatible_jobs

    @property
    def jobs(self):
        return self.modeling_obj_containers

    @property
    def instances_fabrication_footprint(self) -> ExplainableHourlyQuantities:
        return self.server.instances_fabrication_footprint

    @property
    def instances_energy(self) -> ExplainableHourlyQuantities:
        return self.server.instances_energy

    @property
    def energy_footprint(self) -> ExplainableHourlyQuantities:
        return self.server.energy_footprint

    @property
    def fabrication_impact_repartition(self):
        return self.server.fabrication_impact_repartition

    @property
    def usage_impact_repartition(self):
        return self.server.usage_impact_repartition

    def self_delete(self):
        super().self_delete()
        self.server.self_delete()

    calculated_attributes: List[str] = []
