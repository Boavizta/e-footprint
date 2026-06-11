from datetime import datetime

import numpy as np
import pytz
from pint import Quantity
from unittest import TestCase

from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.attribution import attributed_footprint, footprint_per_node_per_source
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.edge.edge_device import EdgeDevice
from efootprint.core.hardware.edge.edge_workload_component import EdgeWorkloadComponent
from efootprint.core.hardware.network import Network
from efootprint.core.hardware.server import Server, ServerTypes
from efootprint.core.hardware.storage import Storage
from efootprint.core.system import System
from efootprint.core.usage.edge.edge_function import EdgeFunction
from efootprint.core.usage.edge.edge_usage_journey import EdgeUsageJourney
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_device_need import RecurrentEdgeDeviceNeed
from efootprint.core.usage.edge.recurrent_server_need import RecurrentServerNeed
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


class TestPerUsagePatternImpactCascade(TestCase):
    @staticmethod
    def _country(name: str, carbon_intensity):
        return Country(
            name,
            name[:3].upper(),
            SourceValue(carbon_intensity),
            ExplainableTimezone(pytz.utc, "UTC timezone"),
        )

    @staticmethod
    def _neutral_storage(name: str):
        return Storage.from_defaults(
            name,
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(0 * u.kg / u.TB_stored),
            data_storage_duration=SourceValue(1 * u.hour),
            base_storage_need=SourceValue(0 * u.TB_stored),
        )

    @staticmethod
    def _server(name: str, storage: Storage):
        return Server.from_defaults(
            name,
            server_type=ServerTypes.serverless(),
            storage=storage,
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1000 * u.W),
            idle_power=SourceValue(0 * u.W),
            lifespan=SourceValue(1 * u.year),
            ram=SourceValue(1 * u.GB_ram),
            compute=SourceValue(1 * u.cpu_core),
            power_usage_effectiveness=SourceValue(1 * u.dimensionless),
            average_carbon_intensity=SourceValue(500 * u.g / u.kWh),
            utilization_rate=SourceValue(1 * u.dimensionless),
            base_ram_consumption=SourceValue(0 * u.GB_ram),
            base_compute_consumption=SourceValue(0 * u.cpu_core),
        )

    def test_shared_usage_journey_attributes_country_dependent_and_neutral_usage_separately(self):
        storage = self._neutral_storage("web storage")
        server = self._server("web server", storage)
        job = Job.from_defaults(
            "web job",
            server=server,
            data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored),
            request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(0 * u.GB_ram),
        )
        step = UsageJourneyStep("web step", SourceValue(1 * u.hour), [job])
        journey = UsageJourney("shared web journey", [step])
        device = Device.from_defaults(
            "shared laptop",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1000 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(24 * u.hour / u.day),
        )
        network = Network("shared network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_carbon_pattern = UsagePattern(
            "low carbon web usage",
            journey,
            [device],
            network,
            self._country("low carbon country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date),
        )
        high_carbon_pattern = UsagePattern(
            "high carbon web usage",
            journey,
            [device],
            network,
            self._country("high carbon country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date),
        )
        system = System("shared web system", [low_carbon_pattern, high_carbon_pattern], edge_usage_patterns=[])

        # Per-source split, pinned per pattern so a regression that re-balances between sources while
        # preserving totals would still fail. Device and network usage stays on the pattern's country.
        per_source = footprint_per_node_per_source(system, UsagePattern, LifeCyclePhases.USAGE)
        self.assertAlmostEqual(
            0.2, (per_source[(device, low_carbon_pattern)]
                  + per_source[(network, low_carbon_pattern)]).sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            0.4, (per_source[(device, high_carbon_pattern)]
                  + per_source[(network, high_carbon_pattern)]).sum().to(u.kg).magnitude, places=6)
        # Server-side usage splits evenly by demand; both patterns have one journey start.
        self.assertAlmostEqual(0.5, per_source[(server, low_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(0.5, per_source[(server, high_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        # Aggregate totals.
        self.assertAlmostEqual(
            0.7, attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            0.9, attributed_footprint(high_carbon_pattern, LifeCyclePhases.USAGE).sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(1.6, system.total_footprint.sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            system.total_footprint.sum().to(u.kg).magnitude,
            (
                attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum()
                + attributed_footprint(high_carbon_pattern, LifeCyclePhases.USAGE).sum()
            ).to(u.kg).magnitude,
            places=6,
        )

    def test_per_usage_pattern_attribution_handles_partial_zero_activity_hours(self):
        storage = self._neutral_storage("web storage")
        server = self._server("web server", storage)
        job = Job.from_defaults(
            "web job",
            server=server,
            data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored),
            request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(0 * u.GB_ram),
        )
        step = UsageJourneyStep("web step", SourceValue(1 * u.hour), [job])
        journey = UsageJourney("shared web journey", [step])
        device = Device.from_defaults(
            "shared laptop",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1000 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(24 * u.hour / u.day),
        )
        network = Network("shared network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_carbon_pattern = UsagePattern(
            "low carbon web usage", journey, [device], network,
            self._country("low carbon country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([0, 1, 0, 1], start_date),
        )
        high_carbon_pattern = UsagePattern(
            "high carbon web usage", journey, [device], network,
            self._country("high carbon country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([0, 1, 0, 1], start_date),
        )
        System("shared web system", [low_carbon_pattern, high_carbon_pattern], edge_usage_patterns=[])

        for pattern in (low_carbon_pattern, high_carbon_pattern):
            magnitudes = np.asarray(attributed_footprint(pattern, LifeCyclePhases.USAGE).magnitude)
            self.assertFalse(
                np.any(np.isnan(magnitudes)),
                f"{pattern.name}: NaN in attributed footprint at zero-activity hours",
            )
            self.assertAlmostEqual(0.0, float(magnitudes[0]), places=6)
            self.assertAlmostEqual(0.0, float(magnitudes[2]), places=6)

    def test_leaf_mutation_invalidates_attribution_fold_memo(self):
        storage = self._neutral_storage("web storage")
        server = self._server("web server", storage)
        job = Job.from_defaults(
            "web job",
            server=server,
            data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored),
            request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(0 * u.GB_ram),
        )
        step = UsageJourneyStep("web step", SourceValue(1 * u.hour), [job])
        journey = UsageJourney("shared web journey", [step])
        device = Device.from_defaults(
            "shared laptop",
            carbon_footprint_fabrication=SourceValue(0 * u.kg),
            power=SourceValue(1000 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(24 * u.hour / u.day),
        )
        network = Network("shared network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_country = self._country("low carbon country", 100 * u.g / u.kWh)
        high_country = self._country("high carbon country", 200 * u.g / u.kWh)
        low_carbon_pattern = UsagePattern(
            "low carbon web usage", journey, [device], network, low_country,
            create_source_hourly_values_from_list([1], start_date),
        )
        high_carbon_pattern = UsagePattern(
            "high carbon web usage", journey, [device], network, high_country,
            create_source_hourly_values_from_list([1], start_date),
        )
        system = System(
            "shared web system", [low_carbon_pattern, high_carbon_pattern], edge_usage_patterns=[])

        def read_low_footprint():
            return attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum().to(u.kg).magnitude

        def assert_invalidates(label: str, mutate):
            before = read_low_footprint()
            # The read memoizes the fold in the system's render_cache; the mutation must wipe it.
            self.assertIn("render_cache", system.__dict__, label)
            mutate()
            self.assertNotIn(
                "render_cache", system.__dict__,
                f"{label}: attribution fold memo not flushed",
            )
            after = read_low_footprint()
            self.assertNotAlmostEqual(before, after, places=6, msg=f"{label}: footprint unchanged after mutation")
            # Conservation: per-pattern attribution must sum to system total after the mutation,
            # which fails if any stale memo survives the post-recompute flush.
            self.assertAlmostEqual(
                system.total_footprint.sum().to(u.kg).magnitude,
                (attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum()
                 + attributed_footprint(high_carbon_pattern, LifeCyclePhases.USAGE).sum()).to(u.kg).magnitude,
                places=6,
                msg=f"{label}: per-pattern attributed footprints do not sum to system total",
            )

        assert_invalidates(
            "country.average_carbon_intensity",
            lambda: setattr(low_country, "average_carbon_intensity", SourceValue(300 * u.g / u.kWh)),
        )
        assert_invalidates(
            "device.power",
            lambda: setattr(device, "power", SourceValue(2000 * u.W)),
        )
        assert_invalidates(
            "network.bandwidth_energy_intensity",
            lambda: setattr(network, "bandwidth_energy_intensity", SourceValue(2 * u.kWh / u.GB)),
        )

    def test_shared_edge_usage_journey_attributes_edge_device_and_recurrent_server_usage_separately(self):
        storage = self._neutral_storage("edge server storage")
        server = self._server("edge server", storage)
        job = Job.from_defaults(
            "edge server job",
            server=server,
            data_transferred=SourceValue(0 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored),
            request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core),
            ram_needed=SourceValue(0 * u.GB_ram),
        )
        workload_component = EdgeWorkloadComponent.from_defaults(
            "edge workload component",
            carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
            power_per_unit=SourceValue(1000 * u.W),
            idle_power_per_unit=SourceValue(0 * u.W),
            lifespan=SourceValue(1 * u.year),
        )
        edge_device = EdgeDevice.from_defaults(
            "edge device",
            structure_carbon_footprint_fabrication=SourceValue(0 * u.kg),
            components=[workload_component],
            lifespan=SourceValue(1 * u.year),
        )
        component_need = RecurrentEdgeComponentNeed(
            "edge workload need",
            workload_component,
            SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.concurrent)),
        )
        device_need = RecurrentEdgeDeviceNeed("edge device need", edge_device, [component_need])
        server_need = RecurrentServerNeed(
            "edge server need",
            edge_device,
            SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.occurrence)),
            [job],
        )
        edge_function = EdgeFunction("edge function", [device_need], [server_need])
        journey = EdgeUsageJourney("shared edge journey", [edge_function], SourceValue(1 * u.hour))
        network = Network("edge network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_carbon_pattern = EdgeUsagePattern(
            "low carbon edge usage",
            journey,
            network,
            self._country("low carbon edge country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date),
        )
        high_carbon_pattern = EdgeUsagePattern(
            "high carbon edge usage",
            journey,
            network,
            self._country("high carbon edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date),
        )
        system = System("shared edge system", [], [low_carbon_pattern, high_carbon_pattern])

        # Per-source split (edge-device usage stays on the pattern's country; this scenario has no
        # network data transfer).
        per_source = footprint_per_node_per_source(system, EdgeUsagePattern, LifeCyclePhases.USAGE)
        self.assertAlmostEqual(
            0.1, per_source[(edge_device, low_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            0.2, per_source[(edge_device, high_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        # Recurrent server work splits evenly by demand across the two patterns.
        self.assertAlmostEqual(0.5, per_source[(server, low_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(0.5, per_source[(server, high_carbon_pattern)].sum().to(u.kg).magnitude, places=6)
        # Aggregate totals.
        self.assertAlmostEqual(
            0.6, attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            0.7, attributed_footprint(high_carbon_pattern, LifeCyclePhases.USAGE).sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(1.3, system.total_footprint.sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(
            system.total_footprint.sum().to(u.kg).magnitude,
            (
                attributed_footprint(low_carbon_pattern, LifeCyclePhases.USAGE).sum()
                + attributed_footprint(high_carbon_pattern, LifeCyclePhases.USAGE).sum()
            ).to(u.kg).magnitude,
            places=6,
        )
