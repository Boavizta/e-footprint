from abc import ABC

from efootprint.builders.services.service_base_class import Service
from efootprint.builders.services.service_job_base_class import ServiceJob


class GenAIJob(ServiceJob, ABC):
    pass

class GenAIModel(Service, ABC):
    pass

class WebApplicationJob(ServiceJob, ABC):
    pass

class WebApplication(Service, ABC):
    pass

ALL_SUPPRESSED_EFOOTPRINT_CLASSES = [GenAIJob, GenAIModel, WebApplicationJob, WebApplication]
ALL_SUPPRESSED_EFOOTPRINT_CLASSES_DICT = {
    modeling_object_class.__name__: modeling_object_class
    for modeling_object_class in ALL_SUPPRESSED_EFOOTPRINT_CLASSES
}
