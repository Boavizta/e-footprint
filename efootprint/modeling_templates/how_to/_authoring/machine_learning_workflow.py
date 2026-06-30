"""Build the ``machine_learning_workflow`` how-to template.

Mirrors the Python sketch in ``machine_learning_workflow.md``: two
{class:UsagePattern} sharing a country and {class:Network}, one driving a
recurring training {class:GPUJob} and the other driving inference traffic.
"""

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.timeseries import ExplainableHourlyQuantitiesFromFormInputs
from efootprint.constants.countries import Countries
from efootprint.constants.sources import Sources
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.gpu_server import GPUServer
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server_base import ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import GPUJob
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    training_storage = Storage.from_defaults("Training dataset storage")
    training_server = GPUServer.from_defaults(
        "Training GPU server", server_type=ServerTypes.autoscaling(),
        compute=SourceValue(8 * u.gpu), storage=training_storage)
    training_job = GPUJob(
        "Weekly retraining", server=training_server,
        request_duration=SourceValue(8 * u.hour),
        compute_needed=SourceValue(8 * u.gpu),
        ram_needed=SourceValue(640 * u.GB_ram),
        data_transferred=SourceValue(500 * u.GB),
        data_stored=SourceValue(50 * u.GB_stored))

    inference_storage = Storage.from_defaults("Inference cache storage")
    inference_server = GPUServer.from_defaults(
        "Inference GPU server", server_type=ServerTypes.autoscaling(),
        compute=SourceValue(4 * u.gpu), storage=inference_storage)
    inference_job = GPUJob(
        "Inference GPU job", server=inference_server,
        request_duration=SourceValue(2 * u.s),
        compute_needed=SourceValue(1 * u.gpu),
        ram_needed=SourceValue(40 * u.GB_ram),
        data_transferred=SourceValue(20 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))

    training_step = UsageJourneyStep.from_defaults("Training run", jobs=[training_job])
    training_journey = UsageJourney("Monthly retraining journey", uj_steps=[training_step])
    inference_step = UsageJourneyStep.from_defaults("Inference call", jobs=[inference_job])
    inference_journey = UsageJourney("Inference journey", uj_steps=[inference_step])

    network = Network.wifi_network()
    laptop = Device.laptop()
    france = Countries.FRANCE()
    start_date = "2025-01-01"

    training_pattern = UsagePattern(
        "Weekly retraining pattern", training_journey, [], network, france,
        ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": start_date,
            "modeling_duration_value": 3,
            "modeling_duration_unit": "year",
            "initial_volume": 12,
            "initial_volume_timespan": "year",
            "net_growth_rate_in_percentage": 0,
            "net_growth_rate_timespan": "year",
        }, source=Sources.USER_DATA))
    inference_pattern = UsagePattern(
        "Production inference pattern", inference_journey, [laptop], network, france,
        ExplainableHourlyQuantitiesFromFormInputs({
            "start_date": start_date,
            "modeling_duration_value": 3,
            "modeling_duration_unit": "year",
            "initial_volume": 73000,
            "initial_volume_timespan": "year",
            "net_growth_rate_in_percentage": 25,
            "net_growth_rate_timespan": "year",
        }, source=Sources.USER_DATA))

    return System(
        "Machine learning workflow system", [training_pattern, inference_pattern],
        edge_usage_patterns=[])


if __name__ == "__main__":
    from efootprint.modeling_templates.how_to._authoring import _write_template
    _write_template("machine_learning_workflow", build_system)
