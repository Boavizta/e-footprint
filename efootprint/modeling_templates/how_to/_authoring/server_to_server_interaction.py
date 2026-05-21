"""Build the ``server_to_server_interaction`` how-to template.

Mirrors the Python sketch in ``server_to_server_interaction.md``: a web
{class:Server} fronting a database {class:Server}, with a single
{class:UsageJourneyStep} listing both jobs to encode the inter-server fan-out.
"""
from datetime import datetime

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_hourly_usage_from_frequency
from efootprint.constants.countries import Countries
from efootprint.constants.units import u
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


def build_system() -> System:
    db_storage = Storage.from_defaults(
        "PostgreSQL storage", base_storage_need=SourceValue(100 * u.GB_stored))
    db_server = Server.from_defaults(
        "PostgreSQL server", server_type=ServerTypes.on_premise(),
        base_ram_consumption=SourceValue(2 * u.GB_ram),
        base_compute_consumption=SourceValue(0.1 * u.cpu_core),
        storage=db_storage)

    web_storage = Storage.from_defaults(
        "Web app local storage", base_storage_need=SourceValue(1 * u.GB_stored))
    web_server = Server.from_defaults(
        "Web application server", server_type=ServerTypes.on_premise(),
        base_ram_consumption=SourceValue(1 * u.GB_ram),
        base_compute_consumption=SourceValue(0.1 * u.cpu_core),
        storage=web_storage)

    read_query = Job(
        "SELECT", server=db_server,
        request_duration=SourceValue(20 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(20 * u.MB_ram),
        data_transferred=SourceValue(5 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    serve_product_page = Job(
        "Serve product page", server=web_server,
        request_duration=SourceValue(50 * u.ms),
        compute_needed=SourceValue(0.3 * u.cpu_core),
        ram_needed=SourceValue(40 * u.MB_ram),
        data_transferred=SourceValue(30 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))

    browse_product = UsageJourneyStep(
        "Browse a product", user_time_spent=SourceValue(15 * u.s),
        jobs=[serve_product_page, read_query])
    journey = UsageJourney("Product browsing journey", uj_steps=[browse_product])

    start_date = datetime(2025, 1, 1)
    usage_pattern = UsagePattern(
        "Product browsing pattern", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=1000, frequency="daily", start_date=start_date))

    return System("Server-to-server interaction system", [usage_pattern], edge_usage_patterns=[])


if __name__ == "__main__":
    from efootprint.modeling_templates.how_to._authoring import _write_template
    _write_template("server_to_server_interaction", build_system)
