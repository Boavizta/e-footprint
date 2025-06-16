from abc import abstractmethod
from typing import List

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.builders.services.service_base_class import Service
from efootprint.core.usage.job import JobBase
from efootprint.utils.tools import get_init_signature_params


class ServiceJob(JobBase):
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    @classmethod
    def compatible_services(cls):
        init_sig_params = get_init_signature_params(cls)
        service_annotation = init_sig_params["service"].annotation

        return [service_annotation]

    def __init__(self, name: str, service: Service, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
        self.service = service
        self.ram_needed.set_label(f"RAM needed on server {self.service.server.name} to process {self.name}")
        self.compute_needed.set_label(f"CPU needed on server {self.service.server.name} to process {self.name}")

    @property
    def server(self) -> ModelingObject:
        return self.service.server

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.server] + super().modeling_objects_whose_attributes_depend_directly_on_me
