"""Build the ``database_modeling`` how-to template.

Mirrors the Python sketch in ``docs_sources/mkdocs_sourcefiles/database_modeling.md``:
a PostgreSQL-style server backed by a Storage, with one read and one write
{class:Job} pinned to it. Wired into a minimal usage journey + pattern so the
template loads as a runnable {class:System}.
"""
from datetime import datetime
from pathlib import Path

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.system_to_json import system_to_json
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
    storage = Storage.from_defaults(
        "PostgreSQL storage", base_storage_need=SourceValue(100 * u.GB_stored))
    db_server = Server.from_defaults(
        "PostgreSQL server", server_type=ServerTypes.on_premise(),
        base_ram_consumption=SourceValue(2 * u.GB_ram),
        base_compute_consumption=SourceValue(0.1 * u.cpu_core),
        storage=storage)

    read_query = Job(
        "SELECT", server=db_server,
        request_duration=SourceValue(20 * u.ms),
        compute_needed=SourceValue(0.1 * u.cpu_core),
        ram_needed=SourceValue(20 * u.MB_ram),
        data_transferred=SourceValue(5 * u.kB),
        data_stored=SourceValue(0 * u.kB_stored))
    write_query = Job(
        "INSERT", server=db_server,
        request_duration=SourceValue(40 * u.ms),
        compute_needed=SourceValue(0.2 * u.cpu_core),
        ram_needed=SourceValue(50 * u.MB_ram),
        data_transferred=SourceValue(2 * u.kB),
        data_stored=SourceValue(0.5 * u.kB_stored))

    read_step = UsageJourneyStep.from_defaults("Read step", jobs=[read_query])
    write_step = UsageJourneyStep.from_defaults("Write step", jobs=[write_query])
    journey = UsageJourney("Database usage journey", uj_steps=[read_step, write_step])

    start_date = datetime(2025, 1, 1)
    usage_pattern = UsagePattern(
        "Database usage pattern", journey, [Device.laptop()], Network.from_defaults("Default network"),
        Countries.FRANCE(),
        create_hourly_usage_from_frequency(
            timespan=7 * u.day, input_volume=1000, frequency="daily", start_date=start_date))

    return System("Database modeling system", [usage_pattern], edge_usage_patterns=[])


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "database_modeling.json"
    system_to_json(build_system(), save_calculated_attributes=False, output_filepath=str(target))
    print(f"Wrote {target}")
