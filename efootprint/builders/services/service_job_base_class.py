from abc import abstractmethod
from inspect import signature

from efootprint.builders.services.service_base_class import Service
from efootprint.core.usage.job import Job


class ServiceJob(Job):
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    @classmethod
    def compatible_services(cls):
        init_sig_params = signature(cls.__init__).parameters
        service_annotation = init_sig_params["service"].annotation

        return [service_annotation]

    def __init__(self, name: str, service: Service, *args, **kwargs):
        super().__init__(name, service.server, *args, **kwargs)
        self.service = service
