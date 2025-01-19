from typing import List

import pandas as pd

from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity
from efootprint.abstract_modeling_classes.source_objects import SourceValue, Source, SourceObject
from efootprint.builders.services.service_base_class import Service
from efootprint.core.hardware.server import Server
from efootprint.core.usage.job import Job
from efootprint.builders.services.ecobenchmark_analysis.ecobenchmark_data_analysis import ECOBENCHMARK_DATA, \
    ECOBENCHMARK_RESULTS_LINK, default_request_duration
from efootprint.constants.units import u

ECOBENCHMARK_DF = pd.read_csv(ECOBENCHMARK_DATA)
ecobenchmark_source = Source(
    "e-footprint analysis of Boavizta’s Ecobenchmark data", ECOBENCHMARK_RESULTS_LINK)


def get_ecobenchmark_technologies() -> List[str]:
    return list(ECOBENCHMARK_DF["service"].unique())

def get_implementation_details() -> List[str]:
    return list(ECOBENCHMARK_DF["use_case"].unique())


class WebApplicationService(Service):
    _default_values = {}

    @classmethod
    def list_values(cls):
        return {"technology": get_ecobenchmark_technologies(),
                "implementation_details": get_implementation_details()}

    @classmethod
    def conditional_list_values(cls):
        return {}

    def __init__(self, name, server: Server, technology: str):
        super().__init__(name, server)
        self.technology = SourceObject(technology, ecobenchmark_source, f"Technology used in {self.name}")

    def generate_job(self, name: str, data_upload: SourceValue, data_download: SourceValue,
                     data_stored: SourceValue, implementation_details: str = "default"):
        filter_df = ECOBENCHMARK_DF[
            (ECOBENCHMARK_DF['service'] == self.technology.value) & (ECOBENCHMARK_DF['use_case'] == implementation_details)]
        tech_row = filter_df.iloc[0]

        cpu_needed = ExplainableQuantity(
            tech_row['avg_cpu_core_per_request'] * u.core, "",
            right_parent=self.technology,
            left_parent=SourceObject(implementation_details, ecobenchmark_source, f"{name} implementation details"),
            operator="query CPU Ecobenchmark data with",
            source=ecobenchmark_source)

        ram_needed = ExplainableQuantity(
            tech_row['avg_ram_per_request_in_MB'] * u.MB, label="",
            right_parent=self.technology,
            left_parent=SourceObject(implementation_details, ecobenchmark_source, f"{name} implementation details"),
            operator="query RAM Ecobenchmark data with",
            source=ecobenchmark_source)

        return Job(
            name, self.server, data_upload, data_download, data_stored, request_duration=default_request_duration(),
            cpu_needed=cpu_needed, ram_needed=ram_needed)


class JobTypes:
    # Job types to add in the WebApplicationService class
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
