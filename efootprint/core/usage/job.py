import math
from copy import copy
from typing import List, Type

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_objects import ExplainableQuantity, EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.core.hardware.server import Server
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences


class Job(ModelingObject):
    @classmethod
    def default_values(cls):
        return {
            "data_upload": SourceValue(150 * u.kB),
            "data_download": SourceValue(2 * u.MB),
            "data_stored": SourceValue(100 * u.kB),
            "request_duration": SourceValue(1 * u.s),
            "cpu_needed": SourceValue(0.1 * u.core),
            "ram_needed": SourceValue(50 * u.MB)
        }

    def __init__(self, name: str, server: Server, data_upload: ExplainableQuantity,
                 data_download: ExplainableQuantity, data_stored: ExplainableQuantity,
                 request_duration: ExplainableQuantity, cpu_needed: ExplainableQuantity,
                 ram_needed: ExplainableQuantity):
        super().__init__(name)
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_upload_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_download_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        self.hourly_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.hourly_avg_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_upload_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_stored_across_usage_patterns = EmptyExplainableObject()
        self.server = ContextualModelingObjectAttribute(server)
        if data_upload.value.magnitude < 0:
            raise ValueError(f"Variable 'data_upload' must be greater than 0, got {data_upload.value}")
        self.data_upload = data_upload.set_label(f"Data upload of request {self.name}")
        if data_download.value.magnitude < 0:
            raise ValueError(f"Variable 'data_download' must be greater than 0, got {data_download.value}")
        self.data_download = data_download.set_label(f"Data download of request {self.name}")
        self.data_stored = data_stored.set_label(f"Data stored by request {self.name}")
        self.request_duration = request_duration.set_label(f"Request duration of {self.name} to {server.name}")
        self.ram_needed = ram_needed.set_label(
            f"RAM needed on server {self.server.name} to process {self.name}")
        self.cpu_needed = cpu_needed.set_label(
            f"CPU needed on server {self.server.name} to process {self.name}")

    @property
    def calculated_attributes(self) -> List[str]:
        return ["hourly_occurrences_per_usage_pattern", "hourly_avg_occurrences_per_usage_pattern",
                "hourly_data_upload_per_usage_pattern", "hourly_data_download_per_usage_pattern",
                "hourly_data_stored_per_usage_pattern", "hourly_occurrences_across_usage_patterns",
                "hourly_avg_occurrences_across_usage_patterns", "hourly_data_upload_across_usage_patterns",
                "hourly_data_stored_across_usage_patterns"]

    @property
    def duration_in_full_hours(self):
        # Use copy not to convert self.request_duration in place
        return ExplainableQuantity(
                math.ceil(copy(self.request_duration.value).to(u.hour).magnitude) * u.dimensionless,
                f"{self.name} duration in full hours")

    @property
    def user_journey_steps(self) -> List[Type["UserJourneyStep"]]:
        return self.modeling_obj_containers

    @property
    def user_journeys(self) -> List[Type["UserJourney"]]:
        return list(set(sum([uj_step.user_journeys for uj_step in self.user_journey_steps], start=[])))

    @property
    def usage_patterns(self) -> List[Type["UsagePattern"]]:
        return list(set(sum([uj_step.usage_patterns for uj_step in self.user_journey_steps], start=[])))

    @property
    def systems(self) -> List[Type["System"]]:
        return list(set(sum([up.systems for up in self.usage_patterns], start=[])))

    @property
    def networks(self) -> List[Type["Network"]]:
        return list(set(up.network for up in self.usage_patterns))

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.server] + self.networks

    def compute_hourly_occurrences_for_usage_pattern(self, usage_pattern: Type["UsagePattern"]):
        job_occurrences = EmptyExplainableObject()
        delay_between_uj_start_and_job_evt = EmptyExplainableObject()
        for uj_step in usage_pattern.user_journey.uj_steps:
            for uj_step_job in uj_step.jobs:
                if uj_step_job == self:
                    job_occurrences += usage_pattern.utc_hourly_user_journey_starts.return_shifted_hourly_quantities(
                        delay_between_uj_start_and_job_evt)

            delay_between_uj_start_and_job_evt += uj_step.user_time_spent

        return job_occurrences.set_label(f"Hourly {self.name} occurrences in {usage_pattern.name}")

    def update_hourly_occurrences_per_usage_pattern(self):
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.hourly_occurrences_per_usage_pattern[up] = self.compute_hourly_occurrences_for_usage_pattern(up)

    def update_hourly_avg_occurrences_per_usage_pattern(self):
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            hourly_avg_job_occurrences = compute_nb_avg_hourly_occurrences(
                self.hourly_occurrences_per_usage_pattern[up], self.request_duration)

            self.hourly_avg_occurrences_per_usage_pattern[up] = hourly_avg_job_occurrences.set_label(
                f"Average hourly {self.name} occurrences in {up.name}")

    def compute_hourly_data_exchange_for_usage_pattern(self, usage_pattern, data_exchange_type: str):
        data_exchange_type_no_underscore = data_exchange_type.replace("_", " ")

        hourly_data_exchange = EmptyExplainableObject()
        data_exchange_per_hour = (getattr(self, data_exchange_type) / self.duration_in_full_hours).set_label(
            f"{data_exchange_type_no_underscore} per hour for job {self.name} in {usage_pattern.name}")

        for hour_shift in range(0, self.duration_in_full_hours.magnitude):
            if not isinstance(self.hourly_occurrences_per_usage_pattern[usage_pattern], EmptyExplainableObject):
                explainable_hour_shift = ExplainableQuantity(
                    hour_shift * u.hour, f"hour nb {hour_shift} within {self.duration_in_full_hours}",
                    left_parent=self.duration_in_full_hours)
                hourly_data_exchange += (
                        self.hourly_occurrences_per_usage_pattern[usage_pattern].return_shifted_hourly_quantities(
                            explainable_hour_shift) * data_exchange_per_hour)

        return hourly_data_exchange.set_label(
                f"Hourly {data_exchange_type_no_underscore} for {self.name} in {usage_pattern.name}")

    def update_hourly_data_upload_per_usage_pattern(self):
        self.hourly_data_upload_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.hourly_data_upload_per_usage_pattern[up] = self.compute_hourly_data_exchange_for_usage_pattern(
                up, "data_upload")

    def update_hourly_data_download_per_usage_pattern(self):
        self.hourly_data_download_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.hourly_data_download_per_usage_pattern[up] = self.compute_hourly_data_exchange_for_usage_pattern(
                up, "data_download")

    def update_hourly_data_stored_per_usage_pattern(self):
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.hourly_data_stored_per_usage_pattern[up] = self.compute_hourly_data_exchange_for_usage_pattern(
                up, "data_stored")

    def sum_calculated_attribute_across_usage_patterns(
            self, calculated_attribute_name: str, calculated_attribute_label: str):
        hourly_calc_attr_summed_across_ups = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            hourly_calc_attr_summed_across_ups += getattr(self, calculated_attribute_name)[usage_pattern]

        return hourly_calc_attr_summed_across_ups.set_label(
                f"Hourly {self.name} {calculated_attribute_label} across usage patterns")

    def update_hourly_occurrences_across_usage_patterns(self):
        self.hourly_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_occurrences_per_usage_pattern", "occurrences")

    def update_hourly_avg_occurrences_across_usage_patterns(self):
        self.hourly_avg_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_avg_occurrences_per_usage_pattern", "average occurrences")

    def update_hourly_data_upload_across_usage_patterns(self):
        self.hourly_data_upload_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_upload_per_usage_pattern", "data upload")

    def update_hourly_data_stored_across_usage_patterns(self):
        self.hourly_data_stored_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_stored_per_usage_pattern", "data upload")