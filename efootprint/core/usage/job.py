import math
from abc import abstractmethod
from copy import copy
from typing import List, TYPE_CHECKING

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.server import Server
from efootprint.core.hardware.server_base import ServerBase
from efootprint.core.usage.compute_nb_occurrences_in_parallel import compute_nb_avg_hourly_occurrences

if TYPE_CHECKING:
    from efootprint.core.usage.usage_pattern import UsagePattern
    from efootprint.core.usage.usage_journey import UsageJourney
    from efootprint.core.usage.usage_journey_step import UsageJourneyStep
    from efootprint.core.hardware.network import Network
    from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
    from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed


class JobBase(ModelingObject):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, data_transferred: ExplainableQuantity, data_stored: ExplainableQuantity,
                 request_duration: ExplainableQuantity, compute_needed: ExplainableQuantity,
                 ram_needed: ExplainableQuantity):
        super().__init__(name)
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_transferred_per_usage_pattern = ExplainableObjectDict()
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        self.hourly_avg_occurrences_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_transferred_across_usage_patterns = EmptyExplainableObject()
        self.hourly_data_stored_across_usage_patterns = EmptyExplainableObject()
        self.data_transferred = data_transferred.set_label(
            f"Sum of all data uploads and downloads by request")
        self.data_stored = data_stored.set_label(f"Data stored by request")
        self.request_duration = request_duration.set_label(f"Request duration")
        self.ram_needed = ram_needed.set_label(f"RAM needed during job processing").to(u.MB_ram)
        self.compute_needed = compute_needed.set_label(f"CPU needed during job processing")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return self.networks

    @property
    def calculated_attributes(self) -> List[str]:
        return ["hourly_occurrences_per_usage_pattern", "hourly_avg_occurrences_per_usage_pattern",
                "hourly_data_transferred_per_usage_pattern", "hourly_data_stored_per_usage_pattern",
                "hourly_avg_occurrences_across_usage_patterns", "hourly_data_transferred_across_usage_patterns",
                "hourly_data_stored_across_usage_patterns"] + super().calculated_attributes

    @property
    def duration_in_full_hours(self):
        # Use copy not to convert self.request_duration in place
        return ExplainableQuantity(
                math.ceil(copy(self.request_duration.value).to(u.hour).magnitude) * u.dimensionless,
                "Duration in full hours")

    # Job objects can be referenced by UsageJourneySteps or by RecurrentServerNeeds
    @property
    def usage_journey_steps(self) -> List["UsageJourneyStep"]:
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep
        return [obj for obj in self.modeling_obj_containers if isinstance(obj, UsageJourneyStep)]

    @property
    def recurrent_server_needs(self) -> List["RecurrentServerNeed"]:
        from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
        return [obj for obj in self.modeling_obj_containers if isinstance(obj, RecurrentServerNeed)]

    @property
    def edge_usage_patterns(self) -> List["EdgeUsagePattern"]:
        return list(dict.fromkeys(sum([rsn.edge_usage_patterns for rsn in self.recurrent_server_needs], start=[])))

    @property
    def usage_journeys(self) -> List["UsageJourney"]:
        return list(dict.fromkeys(sum([uj_step.usage_journeys for uj_step in self.usage_journey_steps], start=[])))

    @property
    def web_usage_patterns(self) -> List["UsagePattern"]:
        return list(dict.fromkeys(sum([uj_step.usage_patterns for uj_step in self.usage_journey_steps], start=[])))

    @property
    def usage_patterns(self) -> List["UsagePattern| EdgeUsagePattern"]:
        return self.web_usage_patterns + self.edge_usage_patterns

    @property
    def networks(self) -> List["Network"]:
        return list(dict.fromkeys(up.network for up in self.usage_patterns))

    def update_dict_element_in_hourly_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        from efootprint.core.usage.usage_pattern import UsagePattern
        if isinstance(usage_pattern, UsagePattern):
            job_occurrences = EmptyExplainableObject()
            delay_between_uj_start_and_job_evt = EmptyExplainableObject()
            for uj_step in usage_pattern.usage_journey.uj_steps:
                for uj_step_job in uj_step.jobs:
                    if uj_step_job == self:
                        job_occurrences += usage_pattern.utc_hourly_usage_journey_starts.return_shifted_hourly_quantities(
                            delay_between_uj_start_and_job_evt)

                delay_between_uj_start_and_job_evt += uj_step.user_time_spent
        else:  # usage_pattern is an EdgeUsagePattern
            job_occurrences = EmptyExplainableObject()
            for recurrent_server_need in self.recurrent_server_needs:
                nb_of_occurrences_of_self_within_server_need = recurrent_server_need.jobs.count(self)
                if nb_of_occurrences_of_self_within_server_need == 0:
                    continue
                job_occurrences += (
                        recurrent_server_need.unitary_hourly_volume_per_usage_pattern[usage_pattern]
                        * usage_pattern.edge_usage_journey.
                        nb_edge_usage_journeys_in_parallel_per_edge_usage_pattern[usage_pattern]
                        * ExplainableQuantity(
                            nb_of_occurrences_of_self_within_server_need * u.dimensionless,
                            label=f"Occurrences within {recurrent_server_need.name}"))

        self.hourly_occurrences_per_usage_pattern[usage_pattern] = job_occurrences.to(u.occurrence).set_label(
            f"Hourly occurrences in {usage_pattern.name}")

    def update_hourly_occurrences_per_usage_pattern(self):
        """Hourly count of job invocations broken down by usage pattern, derived from when each usage pattern's journeys start and at what point in the journey this job is triggered."""
        self.hourly_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_occurrences_per_usage_pattern(up)

    def update_dict_element_in_hourly_avg_occurrences_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        hourly_avg_job_occurrences = compute_nb_avg_hourly_occurrences(
            self.hourly_occurrences_per_usage_pattern[usage_pattern], self.request_duration)

        self.hourly_avg_occurrences_per_usage_pattern[usage_pattern] = hourly_avg_job_occurrences.to(u.concurrent).set_label(
            f"Average hourly occurrences in {usage_pattern.name}")

    def update_hourly_avg_occurrences_per_usage_pattern(self):
        """Hourly count of job invocations averaged with respect to job duration, so a job that runs longer than an hour contributes a fractional occurrence to several modeling buckets."""
        self.hourly_avg_occurrences_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_avg_occurrences_per_usage_pattern(up)

    def compute_hourly_data_exchange_for_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern", data_exchange_type: str):
        data_exchange_type_no_underscore = data_exchange_type.replace("_", " ")

        data_exchange_per_hour = (
                getattr(self, data_exchange_type) * ExplainableQuantity(1 * u.hour, "one hour")
                / self.request_duration
        ).set_label(f"{data_exchange_type_no_underscore} per hour in {usage_pattern.name}")

        hourly_data_exchange = self.hourly_avg_occurrences_per_usage_pattern[usage_pattern] * data_exchange_per_hour
        target_unit = u.MB_stored if data_exchange_type == "data_stored" else u.MB

        return hourly_data_exchange.set_label(
                f"Hourly {data_exchange_type_no_underscore} in {usage_pattern.name}").to(target_unit)

    def update_dict_element_in_hourly_data_transferred_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        self.hourly_data_transferred_per_usage_pattern[usage_pattern] = \
            self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_transferred")

    def update_hourly_data_transferred_per_usage_pattern(self):
        """Hourly volume of data transferred over the network by this job, broken down by usage pattern."""
        self.hourly_data_transferred_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_data_transferred_per_usage_pattern(up)

    def update_dict_element_in_hourly_data_stored_per_usage_pattern(
            self, usage_pattern: "UsagePattern | EdgeUsagePattern"):
        self.hourly_data_stored_per_usage_pattern[usage_pattern] = \
            self.compute_hourly_data_exchange_for_usage_pattern(usage_pattern, "data_stored")

    def update_hourly_data_stored_per_usage_pattern(self):
        """Hourly net change in storage volume caused by this job, broken down by usage pattern."""
        self.hourly_data_stored_per_usage_pattern = ExplainableObjectDict()
        for up in self.usage_patterns:
            self.update_dict_element_in_hourly_data_stored_per_usage_pattern(up)

    def sum_calculated_attribute_across_usage_patterns(
            self, calculated_attribute_name: str, calculated_attribute_label: str):
        hourly_calc_attr_summed_across_ups = EmptyExplainableObject()
        for usage_pattern in self.usage_patterns:
            hourly_calc_attr_summed_across_ups += getattr(self, calculated_attribute_name)[usage_pattern]

        return hourly_calc_attr_summed_across_ups.set_label(
                f"Hourly {calculated_attribute_label} across usage patterns")

    def update_hourly_avg_occurrences_across_usage_patterns(self):
        """Total hourly count of duration-averaged job invocations summed over every usage pattern."""
        self.hourly_avg_occurrences_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_avg_occurrences_per_usage_pattern", "average occurrences").to(u.concurrent)

    def update_hourly_data_transferred_across_usage_patterns(self):
        """Total hourly volume of data transferred over the network by this job, summed over every usage pattern."""
        self.hourly_data_transferred_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_transferred_per_usage_pattern", "data transferred")

    def update_hourly_data_stored_across_usage_patterns(self):
        """Total hourly net change in storage volume caused by this job, summed over every usage pattern."""
        self.hourly_data_stored_across_usage_patterns = self.sum_calculated_attribute_across_usage_patterns(
            "hourly_data_stored_per_usage_pattern", "data stored")


class DirectServerJob(JobBase):
    # Mark the class as abstract but not its children when they define a default_values class attribute
    @classmethod
    @abstractmethod
    def default_values(cls):
        pass

    def __init__(self, name: str, server: ServerBase, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
        self.server = server
        self.ram_needed.set_label(f"RAM needed during job processing")
        self.compute_needed.set_label(
            f"{str(compute_needed.value.units).replace('_', ' ')}s needed on server {self.server.name} "
            f"during job processing")

    @property
    def modeling_objects_whose_attributes_depend_directly_on_me(self) -> List[ModelingObject]:
        return [self.server] + super().modeling_objects_whose_attributes_depend_directly_on_me


class Job(DirectServerJob):
    """A unit of server-side processing triggered by a {class:UsageJourneyStep} or by a {class:RecurrentServerNeed}. Defines how much CPU, memory, network bandwidth, and storage are consumed per invocation."""

    disambiguation = (
        "Use {class:Job} for CPU jobs running on a {class:Server}. Use {class:GPUJob} for jobs whose compute "
        "requirement is in GPUs. For high-level abstractions over common workloads (video streaming, generative "
        "AI), prefer the corresponding service builder rather than wiring jobs by hand.")

    pitfalls = (
        "{param:Job.request_duration} drives concurrency. If the duration exceeds one hour the job is in flight "
        "across multiple modeling buckets at once and consumes a fraction of the server's resources in each.")

    param_descriptions = {
        "server": (
            "{class:Server} that processes the job. The server's resource use and footprint follow from the "
            "jobs it hosts."),
        "data_transferred": (
            "Total bytes uploaded plus downloaded over the network for one invocation of the job."),
        "data_stored": (
            "Net change in stored data per invocation. Positive values only. "
            "Data deletion is handled by {param:Storage.data_storage_duration}"),
        "request_duration": (
            "How long the job takes to process from start to finish on the server."),
        "compute_needed": (
            "CPU consumed by one invocation of the job, expressed in CPU cores held for the request duration."),
        "ram_needed": (
            "RAM held by one invocation of the job for its full duration."),
    }

    default_values =  {
            "data_transferred": SourceValue(150 * u.kB),
            "data_stored": SourceValue(100 * u.kB_stored),
            "request_duration": SourceValue(1 * u.s),
            "compute_needed": SourceValue(0.1 * u.cpu_core),
            "ram_needed": SourceValue(50 * u.MB_ram)
        }

    # __init__ method is copied to change server type.
    def __init__(self, name: str, server: Server, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, server, data_transferred, data_stored, request_duration, compute_needed, ram_needed)


class GPUJob(DirectServerJob):
    """A {class:Job} whose compute requirement is expressed in GPUs and which therefore must run on a {class:GPUServer}."""

    param_descriptions = {
        "server": (
            "{class:GPUServer} that processes the job."),
        "data_transferred": (
            "Total bytes uploaded plus downloaded over the network for one invocation of the job."),
        "data_stored": (
            "Net change in stored data per invocation. Positive values only. "
            "Data deletion is handled by {param:Storage.data_storage_duration}"),
        "request_duration": (
            "How long the job takes to process from start to finish on the server."),
        "compute_needed": (
            "GPU consumed by one invocation of the job, expressed in GPUs held for the request duration."),
        "ram_needed": (
            "GPU memory held by one invocation of the job for its full duration."),
    }

    default_values =  {
            "data_transferred": SourceValue(150 * u.kB),
            "data_stored": SourceValue(100 * u.kB_stored),
            "request_duration": SourceValue(1 * u.s),
            "compute_needed": SourceValue(1 * u.gpu),
            "ram_needed": SourceValue(50 * u.MB_ram)
        }

    def __init__(self, name: str, server: GPUServer, data_transferred: ExplainableQuantity,
                 data_stored: ExplainableQuantity, request_duration: ExplainableQuantity,
                 compute_needed: ExplainableQuantity, ram_needed: ExplainableQuantity):
        super().__init__(name, server, data_transferred, data_stored, request_duration, compute_needed, ram_needed)
