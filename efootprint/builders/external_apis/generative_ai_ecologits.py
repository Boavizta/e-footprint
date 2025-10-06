from typing import List

from efootprint.builders.external_apis.external_api_base_class import ExternalAPI


class EcoLogitsGenAIExternalAPI(ExternalAPI):
    default_values = {
        "provider": SourceObject("mistralai"),
        "model_name": SourceObject("open-mistral-7b")
    }

    @property
    def jobs(self):
        return self.modeling_obj_containers

    def __init__(self, name: str, provider: ExplainableObject, model_name: ExplainableObject):
        pass

    def calculated_attributes(self) -> List[str]:
        return ["fabrication_footprint", "energy_footprint"]


class EcoLogitsGenAIExternalAPIJob():
    def __init__(self, name: str, external_api: EcoLogitsGenAIExternalAPI, output_token_count):
        pass

    def calculated_attributes(self) -> List[str]:
        return ["individual_query_fabrication_impact", ""]