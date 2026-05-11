from abc import abstractmethod
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.utils.tools import get_init_signature_params

if TYPE_CHECKING:
    from efootprint.core.hardware.server_base import ServerBase


class Service(ModelingObject):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    param_descriptions = {
        "server": (
            "{class:ServerBase} on which the service is installed. The service consumes the server's compute "
            "and memory and inherits its provisioning and energy model."),
        "base_ram_consumption": (
            "RAM occupied per server by the service itself (operating system, runtime, idle services), "
            "independent of jobs running through the service."),
        "base_compute_consumption": (
            "Compute occupied per server by the service itself, independent of jobs running through the service."),
    }

    @classmethod
    def installable_on(cls) -> List:
        init_sig_params = get_init_signature_params(cls)
        server_annotation = init_sig_params["server"].annotation

        return [server_annotation]

    @classmethod
    def compatible_jobs(cls) -> List:
        from efootprint.all_classes_in_order import SERVICE_JOB_CLASSES
        compatible_jobs = []
        for service_job_class in SERVICE_JOB_CLASSES:
            if cls in service_job_class.compatible_services():
                compatible_jobs.append(service_job_class)

        return compatible_jobs

    def __init__(self, name, server: "ServerBase",
                 base_ram_consumption: ExplainableQuantity = None,
                 base_compute_consumption: ExplainableQuantity = None):
        super().__init__(name=name)
        self.name = name
        self.server = server
        self.base_ram_consumption = (
            base_ram_consumption if base_ram_consumption is not None else EmptyExplainableObject())
        self.base_compute_consumption = (
            base_compute_consumption if base_compute_consumption is not None else EmptyExplainableObject())

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

    calculated_attributes: List[str] = []
