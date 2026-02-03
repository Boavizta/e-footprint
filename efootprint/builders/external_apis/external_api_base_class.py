from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class ExternalAPIServer(ModelingObject):
    def __init__(self, name: str):
        super().__init__(name=name)
        self.instances_fabrication_footprint = EmptyExplainableObject()
        self.instances_energy = EmptyExplainableObject()
        self.energy_footprint = EmptyExplainableObject()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return []

    @property
    def calculated_attributes(self) -> List[str]:
        return ["instances_fabrication_footprint", "instances_energy", "energy_footprint"]

    @abstractmethod
    def update_instances_fabrication_footprint(self) -> None:
        pass

    @abstractmethod
    def update_instances_energy(self) -> None:
        pass

    @abstractmethod
    def update_energy_footprint(self) -> None:
        pass


class ExternalAPI(ModelingObject):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass
    
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
