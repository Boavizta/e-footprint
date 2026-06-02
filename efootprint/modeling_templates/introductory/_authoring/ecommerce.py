"""Build the ``ecommerce`` introductory template.

A shopping journey served by a web application server calling a database server.
This scenario backs the interface's e-commerce starter and the database /
server-to-server how-to links.
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
        "Product database storage", base_storage_need=SourceValue(200 * u.GB_stored))
    db_server = Server.from_defaults(
        "Product database server", server_type=ServerTypes.on_premise(),
        base_ram_consumption=SourceValue(2 * u.GB_ram),
        base_compute_consumption=SourceValue(0.1 * u.cpu_core),
        storage=db_storage)

    web_storage = Storage.from_defaults(
        "Web app local storage", base_storage_need=SourceValue(1 * u.GB_stored))
    web_server = Server.from_defaults(
        "Web application server", server_type=ServerTypes.autoscaling(),
        base_ram_consumption=SourceValue(4 * u.GB_ram),
        base_compute_consumption=SourceValue(0.2 * u.cpu_core),
        storage=web_storage)

    serve_catalog = Job(
        "Serve catalog page", server=web_server,
        request_duration=SourceValue(120 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(80 * u.MB_ram),
        data_transferred=SourceValue(1.5 * u.MB),
        data_stored=SourceValue(0 * u.kB_stored))
    read_catalog = Job(
        "Read product catalog", server=db_server,
        request_duration=SourceValue(20 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(20 * u.MB_ram),
        data_transferred=SourceValue(5 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))

    update_cart = Job(
        "Update cart", server=web_server,
        request_duration=SourceValue(60 * u.ms),
        compute_needed=SourceValue(0.05 * u.cpu_core),
        ram_needed=SourceValue(40 * u.MB_ram),
        data_transferred=SourceValue(30 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    write_cart = Job(
        "Write cart row", server=db_server,
        request_duration=SourceValue(40 * u.ms),
        compute_needed=SourceValue(0.2 * u.cpu_core),
        ram_needed=SourceValue(50 * u.MB_ram),
        data_transferred=SourceValue(2 * u.kB),
        data_stored=SourceValue(2 * u.kB_stored))

    submit_order = Job(
        "Submit order", server=web_server,
        request_duration=SourceValue(200 * u.ms),
        compute_needed=SourceValue(0.15 * u.cpu_core),
        ram_needed=SourceValue(120 * u.MB_ram),
        data_transferred=SourceValue(80 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    write_order = Job(
        "Write order row", server=db_server,
        request_duration=SourceValue(80 * u.ms),
        compute_needed=SourceValue(0.25 * u.cpu_core),
        ram_needed=SourceValue(80 * u.MB_ram),
        data_transferred=SourceValue(8 * u.kB),
        data_stored=SourceValue(10 * u.kB_stored))

    browse_step = UsageJourneyStep.from_defaults(
        "Browse the catalog", jobs=[serve_catalog, read_catalog])
    cart_step = UsageJourneyStep.from_defaults(
        "Add an item to the cart", jobs=[update_cart, write_cart])
    checkout_step = UsageJourneyStep.from_defaults(
        "Check out", jobs=[submit_order, write_order])
    journey = UsageJourney("Shopping journey", uj_steps=[browse_step, cart_step, checkout_step])

    start_date = datetime(2025, 1, 1)
    usage_pattern = UsagePattern(
        "Daily shoppers", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=5000, frequency="daily", start_date=start_date))

    return System("E-commerce web and database system", [usage_pattern], edge_usage_patterns=[])


if __name__ == "__main__":
    from efootprint.modeling_templates.introductory._authoring import _write_template
    _write_template("ecommerce", build_system)
