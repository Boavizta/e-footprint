from abc import abstractmethod
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.builders.external_apis.external_api_base_class import ExternalAPI
from efootprint.core.usage.job import JobBase
from efootprint.utils.tools import get_init_signature_params

if TYPE_CHECKING:
    from efootprint.builders.external_apis.external_api_base_class import ExternalAPIServer


class ExternalAPIJob(JobBase):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    @classmethod
    def compatible_external_apis(cls):
        init_sig_params = get_init_signature_params(cls)
        external_api_annotation = init_sig_params["external_api"].annotation

        return [external_api_annotation]

    def __init__(self, name: str, external_api: ExternalAPI, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
        self.external_api = external_api

    @property
    def server(self) -> "ExternalAPIServer":
        return self.external_api.server

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.server] + super().modeling_objects_whose_attributes_depend_directly_on_me
