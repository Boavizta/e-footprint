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
from efootprint.utils.impact_repartition import ImpactRepartitionSankey


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

    def test_shared_job_across_two_countries_keeps_carbon_provenance(self):
        # The SAME Job is shared across two journeys (one step in each) mapped to patterns in different
        # countries, and a bulk job rides the same network only in the high-carbon country, blending the
        # network's overall traffic heavily toward it. The shared job's country-dependent (network/device)
        # footprint must still split per its own per-(job, pattern) contribution — each pattern keeps its own
        # grid intensity — not a basis proportional to each pattern's overall traffic.
        storage = self._neutral_storage("web storage")
        server = self._server("web server", storage)
        shared_job = Job.from_defaults(
            "shared job", server=server, data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        bulk_job = Job.from_defaults(
            "bulk job", server=server, data_transferred=SourceValue(1000 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        low_journey = UsageJourney(
            "low carbon journey", [UsageJourneyStep("low step", SourceValue(1 * u.min), [shared_job])])
        high_journey = UsageJourney("high carbon journey", [
            UsageJourneyStep("high step", SourceValue(1 * u.min), [shared_job]),
            UsageJourneyStep("bulk step", SourceValue(1 * u.min), [bulk_job])])
        device = Device.from_defaults(
            "laptop", carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(1000 * u.W),
            lifespan=SourceValue(1 * u.year), fraction_of_usage_time=SourceValue(24 * u.hour / u.day))
        network = Network("shared network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_pattern = UsagePattern(
            "low carbon web usage", low_journey, [device], network,
            self._country("low carbon country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date))
        high_pattern = UsagePattern(
            "high carbon web usage", high_journey, [device], network,
            self._country("high carbon country", 300 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date))
        system = System("shared web system", [low_pattern, high_pattern], edge_usage_patterns=[])

        # The network's per-pattern footprint is grid-weighted by each pattern's country: the low pattern
        # (only the shared job, 1 GB at 1 kWh/GB, 100 g/kWh) is exactly 0.1 kg and is NOT polluted by the
        # high pattern's bulk traffic. The high pattern carries its own jobs (shared 0.3 + bulk 300 kg)
        # at 300 g/kWh.
        per_source = footprint_per_node_per_source(system, UsagePattern, LifeCyclePhases.USAGE)
        self.assertAlmostEqual(0.1, per_source[(network, low_pattern)].sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(300.3, per_source[(network, high_pattern)].sum().to(u.kg).magnitude, places=4)
        # The shared device is also country-dependent; each pattern carries a nonzero share of it.
        self.assertGreater(per_source[(device, low_pattern)].sum().to(u.kg).magnitude, 0.0)
        self.assertGreater(per_source[(device, high_pattern)].sum().to(u.kg).magnitude, 0.0)
        # Conservation: the system total reconciles with the sum of the patterns' attributed footprints.
        self.assertAlmostEqual(
            system.total_footprint.sum().to(u.kg).magnitude,
            (attributed_footprint(low_pattern, LifeCyclePhases.USAGE).sum()
             + attributed_footprint(high_pattern, LifeCyclePhases.USAGE).sum()).to(u.kg).magnitude, places=3)

    def test_job_longer_than_journey_renders_diagram_and_spans_run_window(self):
        # A short (1 min) journey triggers a 150 min job whose run window spills two hours past the only
        # journey start. The attribution must carry the job's whole run window up to the pattern, and the
        # impact-repartition Sankey (what opening Results does) must build over it without raising.
        storage = self._neutral_storage("web storage")
        server = self._server("web server", storage)
        job = Job.from_defaults(
            "web job", server=server, data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(150 * u.min),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        journey = UsageJourney("web journey", [UsageJourneyStep("web step", SourceValue(1 * u.min), [job])])
        device = Device.from_defaults(
            "laptop", carbon_footprint_fabrication=SourceValue(0 * u.kg), power=SourceValue(1000 * u.W),
            lifespan=SourceValue(1 * u.year), fraction_of_usage_time=SourceValue(24 * u.hour / u.day))
        network = Network("network", SourceValue(1 * u.kWh / u.GB))
        pattern = UsagePattern(
            "web usage", journey, [device], network, self._country("country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([1, 0, 0, 0], datetime(2026, 1, 1)))
        system = System("web system", [pattern], edge_usage_patterns=[])

        ImpactRepartitionSankey(system, aggregation_threshold_percent=1).build()

        # A 150 min job starting in hour 0 runs across hours 0, 1 and 2.
        attributed = np.asarray(attributed_footprint(pattern, LifeCyclePhases.USAGE).to(u.kg).magnitude)
        self.assertGreater(float(attributed[0]), 0.0)
        self.assertGreater(float(attributed[1]), 0.0)
        self.assertGreater(float(attributed[2]), 0.0)
        # Conservation hour-by-hour: a single pattern carries every source's full footprint, so its
        # attribution equals the unrounded source energy footprints hour by hour.
        source_energy = device.energy_footprint + network.energy_footprint + server.energy_footprint
        self.assertTrue(np.allclose(np.asarray(source_energy.to(u.kg).magnitude), attributed, atol=1e-9))

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

    def test_shared_edge_job_across_two_countries_keeps_carbon_provenance(self):
        # Edge mirror of the shared-job carbon-provenance test: the SAME edge server job is triggered by two
        # edge journeys mapped to patterns in different countries, and a bulk job blends the shared network
        # heavily toward the high-carbon country. The shared job's network footprint must still split per its
        # own per-(job, pattern) contribution — each pattern keeps its own grid intensity.
        storage = self._neutral_storage("edge server storage")
        server = self._server("edge server", storage)
        shared_job = Job.from_defaults(
            "shared edge job", server=server, data_transferred=SourceValue(1 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        bulk_job = Job.from_defaults(
            "bulk edge job", server=server, data_transferred=SourceValue(1000 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(1 * u.hour),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))

        def make_edge_device(name):
            workload_component = EdgeWorkloadComponent.from_defaults(
                f"{name} workload component", carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
                power_per_unit=SourceValue(0 * u.W), idle_power_per_unit=SourceValue(0 * u.W),
                lifespan=SourceValue(1 * u.year))
            return EdgeDevice.from_defaults(
                name, structure_carbon_footprint_fabrication=SourceValue(0 * u.kg),
                components=[workload_component], lifespan=SourceValue(1 * u.year))

        def recurrent_volume():
            return SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.occurrence))

        low_device = make_edge_device("low edge device")
        high_device = make_edge_device("high edge device")
        low_server_need = RecurrentServerNeed("low edge server need", low_device, recurrent_volume(), [shared_job])
        high_server_need = RecurrentServerNeed("high edge server need", high_device, recurrent_volume(), [shared_job])
        bulk_server_need = RecurrentServerNeed("bulk edge server need", high_device, recurrent_volume(), [bulk_job])
        low_journey = EdgeUsageJourney(
            "low edge journey", [EdgeFunction("low edge function", [], [low_server_need])], SourceValue(1 * u.hour))
        high_journey = EdgeUsageJourney(
            "high edge journey", [EdgeFunction("high edge function", [], [high_server_need, bulk_server_need])],
            SourceValue(1 * u.hour))
        network = Network("shared edge network", SourceValue(1 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        low_pattern = EdgeUsagePattern(
            "low carbon edge usage", low_journey, network,
            self._country("low carbon edge country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date))
        high_pattern = EdgeUsagePattern(
            "high carbon edge usage", high_journey, network,
            self._country("high carbon edge country", 300 * u.g / u.kWh),
            create_source_hourly_values_from_list([1], start_date))
        system = System("shared edge system", [], [low_pattern, high_pattern])

        # The network's per-pattern footprint is grid-weighted by each pattern's country: the low pattern
        # (only the shared job, 1 GB at 1 kWh/GB, 100 g/kWh) is exactly 0.1 kg and is NOT polluted by the
        # high pattern's bulk traffic (shared 0.3 + bulk 300 kg at 300 g/kWh).
        per_source = footprint_per_node_per_source(system, EdgeUsagePattern, LifeCyclePhases.USAGE)
        self.assertAlmostEqual(0.1, per_source[(network, low_pattern)].sum().to(u.kg).magnitude, places=6)
        self.assertAlmostEqual(300.3, per_source[(network, high_pattern)].sum().to(u.kg).magnitude, places=4)
        # Conservation: the system total reconciles with the sum of the patterns' attributed footprints.
        self.assertAlmostEqual(
            system.total_footprint.sum().to(u.kg).magnitude,
            (attributed_footprint(low_pattern, LifeCyclePhases.USAGE).sum()
             + attributed_footprint(high_pattern, LifeCyclePhases.USAGE).sum()).to(u.kg).magnitude, places=3)

    def test_edge_job_longer_than_journey_renders_diagram_and_spans_run_window(self):
        # Edge mirror of the long-job test: a 1 h-span edge journey triggers a 150 min server job whose run
        # window spills two hours past the only journey start. The attribution must carry the whole run window
        # up to the pattern, and the impact-repartition Sankey must build over it without raising.
        storage = self._neutral_storage("edge server storage")
        server = self._server("edge server", storage)
        job = Job.from_defaults(
            "edge server job", server=server, data_transferred=SourceValue(0 * u.GB),
            data_stored=SourceValue(0 * u.GB_stored), request_duration=SourceValue(150 * u.min),
            compute_needed=SourceValue(1 * u.cpu_core), ram_needed=SourceValue(0 * u.GB_ram))
        workload_component = EdgeWorkloadComponent.from_defaults(
            "edge workload component", carbon_footprint_fabrication_per_unit=SourceValue(0 * u.kg),
            power_per_unit=SourceValue(1000 * u.W), idle_power_per_unit=SourceValue(0 * u.W),
            lifespan=SourceValue(1 * u.year))
        edge_device = EdgeDevice.from_defaults(
            "edge device", structure_carbon_footprint_fabrication=SourceValue(0 * u.kg),
            components=[workload_component], lifespan=SourceValue(1 * u.year))
        component_need = RecurrentEdgeComponentNeed(
            "edge workload need", workload_component,
            SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.concurrent)))
        device_need = RecurrentEdgeDeviceNeed("edge device need", edge_device, [component_need])
        server_need = RecurrentServerNeed(
            "edge server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([1] * 168, dtype=np.float32), u.occurrence)), [job])
        edge_function = EdgeFunction("edge function", [device_need], [server_need])
        journey = EdgeUsageJourney("edge journey", [edge_function], SourceValue(1 * u.hour))
        network = Network("edge network", SourceValue(1 * u.kWh / u.GB))
        pattern = EdgeUsagePattern(
            "edge usage", journey, network, self._country("edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([1, 0, 0, 0], datetime(2026, 1, 1)))
        system = System("edge system", [], [pattern])

        ImpactRepartitionSankey(system, aggregation_threshold_percent=1).build()

        # A 150 min job starting in hour 0 runs across hours 0, 1 and 2.
        attributed = np.asarray(attributed_footprint(pattern, LifeCyclePhases.USAGE).to(u.kg).magnitude)
        self.assertGreater(float(attributed[0]), 0.0)
        self.assertGreater(float(attributed[1]), 0.0)
        self.assertGreater(float(attributed[2]), 0.0)
        # Conservation: a single pattern carries the device's and the server's full footprints hour by hour.
        source_energy = edge_device.energy_footprint + server.energy_footprint
        self.assertTrue(np.allclose(np.asarray(source_energy.to(u.kg).magnitude), attributed, atol=1e-9))
