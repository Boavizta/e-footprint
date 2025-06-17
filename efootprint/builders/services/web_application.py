import csv
from typing import List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Source, SourceObject
from efootprint.builders.services.service_base_class import Service
from efootprint.builders.services.service_job_base_class import ServiceJob
from efootprint.core.hardware.server import Server
from efootprint.builders.services.ecobenchmark_analysis.ecobenchmark_data_analysis import ECOBENCHMARK_DATA, \
    ECOBENCHMARK_RESULTS_LINK, default_request_duration
from efootprint.constants.units import u


with open(ECOBENCHMARK_DATA, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    ecobenchmark_data = list(reader)

ecobenchmark_source = Source(
    "e-footprint analysis of Boavizta’s Ecobenchmark data", ECOBENCHMARK_RESULTS_LINK)


def get_ecobenchmark_technologies() -> List[str]:
    technologies = [row['service'] for row in ecobenchmark_data if row['service']]
    return list(set(technologies))

def get_implementation_details() -> List[str]:
    implementation_details = [row['use_case'] for row in ecobenchmark_data if row['use_case']]
    return list(set(implementation_details))


class WebApplication(Service):
    default_values =  {"technology": SourceObject("php-symfony")}

    list_values =  {"technology": [SourceObject(technology) for technology in get_ecobenchmark_technologies()]}

    conditional_list_values =  {}

    def __init__(self, name:str, server: Server, technology: ExplainableObject):
        super().__init__(name, server)
        self.technology = technology.set_label(f"Technology used in {self.name}")


class WebApplicationJob(ServiceJob):
    default_values =  {
            "data_transferred": SourceValue(2.2 * u.MB),
            "data_stored": SourceValue(100 * u.kB),
            "implementation_details": SourceObject("default"),
        }

    list_values =  {"implementation_details": [
            SourceObject(implementation_detail) for implementation_detail in get_implementation_details()]}

    def __init__(self, name: str, service: WebApplication, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, implementation_details: ExplainableObject):
        super().__init__(
            name, service, data_transferred, data_stored, request_duration=SourceValue(0 * u.s),
            compute_needed=SourceValue(0 * u.cpu_core), ram_needed=SourceValue(0 * u.GB))
        self.implementation_details = implementation_details.set_label(f"{self.name} implementation details")

    @property
    def calculated_attributes(self) -> List[str]:
        return ["request_duration", "compute_needed", "ram_needed"] + super().calculated_attributes

    def update_request_duration(self):
        self.request_duration = default_request_duration().set_label(f"{self.name} request duration")

    def update_compute_needed(self):
        tech_row = next(
            row for row in ecobenchmark_data
            if row['service'] == self.service.technology.value
            and row['use_case'] == self.implementation_details.value
        )

        self.compute_needed = ExplainableQuantity(
            tech_row['avg_cpu_core_per_request'] * u.cpu_core, "",
            right_parent=self.service.technology,
            left_parent=self.implementation_details,
            operator="query CPU Ecobenchmark data with",
            source=ecobenchmark_source)

    def update_ram_needed(self):
        tech_row = next(
            row for row in ecobenchmark_data
            if row['service'] == self.service.technology.value
            and row['use_case'] == self.implementation_details.value
        )

        self.ram_needed = ExplainableQuantity(
            tech_row['avg_ram_per_request_in_MB'] * u.MB, label="",
            right_parent=self.service.technology,
            left_parent=self.implementation_details,
            operator="query RAM Ecobenchmark data with",
            source=ecobenchmark_source)


class JobTypes:
    # Job types to add in the WebApplication class
    AUTH = "auth"
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_LIST = "data_list"
    DATA_SIMPLE_ANALYTIC = "data_simple_analytic"
    DATA_STREAM = "data_stream"  # video, musique, data
    TRANSACTION = "transaction"
    TRANSACTION_STRONG = "transaction_strong"
    NOTIFICATION = "notification"
    ANALYTIC_DATA_LOADING = "analytic_data_loading"
    ANALYTIC_READING_PREPARED = "analytic_reading_prepared"
    ANALYTIC_READING_ON_THE_FLY = "analytic_reading_on_the_fly"
    ML_RECOMMENDATION = "ml_reco"  # kvm
    ML_LLM = "ml_llm"
    ML_DEEPLEARNING = "ml_dl"
    ML_REGRESSION = "ml_regression"  # linear regression, polynomial regression, svm
    ML_CLASSIFIER = "ml_classifier"  # bayes, random forest
    UNDEFINED = "undefined"


if __name__ == "__main__":
    print(get_ecobenchmark_technologies())
