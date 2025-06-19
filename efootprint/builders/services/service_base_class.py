from abc import abstractmethod
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.utils.tools import get_init_signature_params

if TYPE_CHECKING:
    from efootprint.core.hardware.server_base import ServerBase


class Service(ModelingObject):
    default_values = {}

    @classmethod
    def installable_on(cls) -> List:
        init_sig_params = get_init_signature_params(cls)
        server_annotation = init_sig_params["server"].annotation

        return [server_annotation]

    @classmethod
    def compatible_jobs(cls) -> List:
        from efootprint.core.all_classes_in_order import SERVICE_JOB_CLASSES
        compatible_jobs = []
        for service_job_class in SERVICE_JOB_CLASSES:
            if cls in service_job_class.compatible_services():
                compatible_jobs.append(service_job_class)

        return compatible_jobs

    def __init__(self, name, server: "ServerBase"):
        super().__init__(name=name)
        self.name = name
        self.server = server
        self.base_ram_consumption = EmptyExplainableObject()
        self.base_compute_consumption = EmptyExplainableObject()

    def after_init(self):
        super().after_init()
        self.compute_calculated_attributes()
        # Compute server calculated attributes so that it raises an error if not enough resources
        self.server.compute_calculated_attributes()
        for system in self.systems:
            # Systems need to be recomputed because they depend on the server’s recomputed attributes
            system.compute_calculated_attributes()

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self):
        return [self.server] + self.jobs

    @property
    def systems(self) -> List:
        return self.server.systems

    @property
    def jobs(self) -> List[ModelingObject]:
        return self.modeling_obj_containers
