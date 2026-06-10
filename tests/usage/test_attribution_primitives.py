import unittest
from datetime import datetime
from unittest import TestCase

import numpy as np
import pytz
from pint import Quantity

from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceRecurrentValues, SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
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
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern


class TestAttributionPrimitives(TestCase):
    """Partition / tiling identities of the attribution-only occurrence and data primitives, on a real model with
    web + edge sides and within-journey reuse (a step repeated in uj_steps, a job repeated within a step, an RSN
    reached through two edge functions)."""

    @classmethod
    def setUpClass(cls):
        def country(name, carbon_intensity):
            return Country(name, name[:3].upper(), SourceValue(carbon_intensity),
                           ExplainableTimezone(pytz.utc, "UTC timezone"))

        storage = Storage.from_defaults("attribution primitives storage")
        server = Server.from_defaults(
            "attribution primitives server", server_type=ServerTypes.autoscaling(), storage=storage)
        cls.dual_job = Job.from_defaults(
            "dual side job", server=server, request_duration=SourceValue(90 * u.min),
            data_transferred=SourceValue(2 * u.MB), data_stored=SourceValue(1 * u.MB_stored))
        cls.web_only_job = Job.from_defaults(
            "web only job", server=server, request_duration=SourceValue(10 * u.min),
            data_transferred=SourceValue(5 * u.MB), data_stored=SourceValue(3 * u.MB_stored))

        cls.step_a = UsageJourneyStep(
            "step a", SourceValue(30 * u.min), [cls.dual_job, cls.web_only_job, cls.dual_job])
        cls.step_b = UsageJourneyStep("step b", SourceValue(1 * u.hour), [cls.dual_job])
        cls.journey = UsageJourney("journey with step reuse", [cls.step_a, cls.step_b, cls.step_a])

        device = Device.from_defaults("attribution primitives laptop")
        network = Network("attribution primitives network", SourceValue(0.05 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        cls.up1 = UsagePattern(
            "web usage pattern 1", cls.journey, [device], network, country("first web country", 100 * u.g / u.kWh),
            create_source_hourly_values_from_list([10, 0, 5, 0, 8], start_date))
        cls.up2 = UsagePattern(
            "web usage pattern 2", cls.journey, [device], network, country("second web country", 300 * u.g / u.kWh),
            create_source_hourly_values_from_list([3, 7], start_date))

        workload_component = EdgeWorkloadComponent.from_defaults("attribution primitives workload component")
        edge_device = EdgeDevice.from_defaults("attribution primitives edge device", components=[workload_component])
        component_need = RecurrentEdgeComponentNeed(
            "attribution primitives workload need", workload_component,
            SourceRecurrentValues(Quantity(np.array([0.5] * 168, dtype=np.float32), u.concurrent)))
        device_need = RecurrentEdgeDeviceNeed("attribution primitives device need", edge_device, [component_need])
        cls.shared_rsn = RecurrentServerNeed(
            "shared recurrent server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([2.0] * 168, dtype=np.float32), u.occurrence)),
            [cls.dual_job, cls.dual_job])
        cls.other_rsn = RecurrentServerNeed(
            "other recurrent server need", edge_device,
            SourceRecurrentValues(Quantity(np.array([1.0] * 168, dtype=np.float32), u.occurrence)),
            [cls.dual_job])
        cls.ef1 = EdgeFunction("edge function 1", [device_need], [cls.shared_rsn])
        cls.ef2 = EdgeFunction("edge function 2", [], [cls.shared_rsn, cls.other_rsn])
        cls.edge_journey = EdgeUsageJourney(
            "edge journey", [cls.ef1, cls.ef2], usage_span=SourceValue(1 * u.year))
        cls.edge_up = EdgeUsagePattern(
            "edge usage pattern", cls.edge_journey, network, country("edge country", 200 * u.g / u.kWh),
            create_source_hourly_values_from_list([4, 0, 6], start_date))

        cls.system = System(
            "attribution primitives system", [cls.up1, cls.up2], edge_usage_patterns=[cls.edge_up])

    def assert_hourly_quantities_equal(self, expected, actual):
        max_abs_diff = (expected - actual).abs().max()
        scale = max(expected.abs().max().magnitude, 1e-9)
        self.assertAlmostEqual(0, max_abs_diff.magnitude / scale, places=4)

    def test_per_step_and_per_rsn_occurrences_partition_across_usage_patterns_total(self):
        """Test that per-step plus per-RSN occurrences sum to the job's across-patterns total, with step and job
        reuse within the journey and an RSN shared across edge functions."""
        for job in (self.dual_job, self.web_only_job):
            partition_sum = (
                sum(job.hourly_avg_occurrences_per_usage_journey_step.values())
                + sum(job.hourly_avg_occurrences_per_recurrent_server_need.values()))
            self.assert_hourly_quantities_equal(job.hourly_avg_occurrences_across_usage_patterns, partition_sum)

    def test_per_step_and_per_rsn_data_stored_partition_across_usage_patterns_total(self):
        """Test that per-step plus per-RSN data-stored rates sum to the job's across-patterns data-stored rate."""
        for job in (self.dual_job, self.web_only_job):
            partition_sum = (
                sum(job.hourly_data_stored_per_step.values())
                + sum(job.hourly_data_stored_per_recurrent_server_need.values()))
            self.assert_hourly_quantities_equal(job.hourly_data_stored_across_usage_patterns, partition_sum)

    def test_per_cell_data_transferred_partition_across_usage_patterns_total(self):
        """Test that per-(step, up) plus per-(rsn, edge_up) data transferred sum to the job's across-patterns
        data-transferred rate."""
        job = self.dual_job
        partition_sum = sum(
            job.compute_hourly_data_transferred_per_usage_pattern_per_step(up, uj_step)
            for uj_step in job.usage_journey_steps for up in uj_step.usage_patterns)
        partition_sum += sum(
            job.compute_hourly_data_transferred_per_usage_pattern_per_recurrent_server_need(edge_up, rsn)
            for rsn in job.recurrent_server_needs for edge_up in rsn.edge_usage_patterns)
        self.assert_hourly_quantities_equal(job.hourly_data_transferred_across_usage_patterns, partition_sum)

    def test_per_usage_journey_regroups_match_per_usage_pattern_partitions(self):
        """Test that the per-journey and per-edge-journey regroups recover the web and edge per-pattern sums."""
        job = self.dual_job
        web_total = (job.hourly_avg_occurrences_per_usage_pattern[self.up1]
                     + job.hourly_avg_occurrences_per_usage_pattern[self.up2])
        self.assert_hourly_quantities_equal(web_total, job.hourly_avg_occurrences_per_usage_journey[self.journey])
        self.assert_hourly_quantities_equal(
            job.hourly_avg_occurrences_per_usage_pattern[self.edge_up],
            job.hourly_avg_occurrences_per_edge_usage_journey[self.edge_journey])

    def test_step_occupancy_tiles_nb_usage_journeys_in_parallel(self):
        """Test that step occupancies summed over a journey's distinct steps tile the journey's parallel count,
        including for a step repeated within the journey."""
        for up in (self.up1, self.up2):
            occupancy_sum = (self.step_a.hourly_avg_occurrences_per_usage_pattern[up]
                             + self.step_b.hourly_avg_occurrences_per_usage_pattern[up])
            self.assert_hourly_quantities_equal(
                self.journey.nb_usage_journeys_in_parallel_per_usage_pattern[up], occupancy_sum)

    def test_attribution_cells_shares_partition_to_one(self):
        """Test that hourly shares sum to 1 at every hour the job runs and to exactly 0 — the fallback-0 contract,
        never NaN — at zero-occurrence hours, and that flat shares sum to 1 over the cells."""
        for job in (self.dual_job, self.web_only_job):
            total_occurrences = job.hourly_avg_occurrences_across_usage_patterns
            hourly_share_sum = sum(cell.hourly_share for cell in job.attribution_cells)
            self.assertEqual(total_occurrences.start_date, hourly_share_sum.start_date)
            np.testing.assert_allclose(
                hourly_share_sum.magnitude, np.where(total_occurrences.magnitude > 0, 1, 0), atol=1e-4)
            flat_share_sum = sum(cell.flat_share.magnitude for cell in job.attribution_cells)
            self.assertAlmostEqual(1, flat_share_sum, places=5)

    def test_attribution_cells_equal_share_fallback_when_job_never_runs(self):
        """Test that a job whose usage patterns carry zero traffic gets equal flat shares summing to 1 and
        zero-acting hourly shares instead of a division-by-zero crash."""
        zero_job = Job.from_defaults(
            "zero traffic job", server=Server.from_defaults(
                "zero traffic server", server_type=ServerTypes.autoscaling(),
                storage=Storage.from_defaults("zero traffic storage")),
            request_duration=SourceValue(10 * u.min),
            data_transferred=SourceValue(1 * u.MB), data_stored=SourceValue(1 * u.MB_stored))
        step_one = UsageJourneyStep("zero traffic step one", SourceValue(30 * u.min), [zero_job])
        step_two = UsageJourneyStep("zero traffic step two", SourceValue(15 * u.min), [zero_job])
        journey = UsageJourney("zero traffic journey", [step_one, step_two])
        up = UsagePattern(
            "zero traffic usage pattern", journey, [Device.from_defaults("zero traffic laptop")],
            Network("zero traffic network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("zero traffic country", "ZTC", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([0, 0, 0], datetime(2026, 1, 1)))
        System("zero traffic system", [up], edge_usage_patterns=[])

        cells = zero_job.attribution_cells
        self.assertEqual(2, len(cells))
        for cell in cells:
            self.assertAlmostEqual(0.5, cell.flat_share.magnitude, places=6)
            self.assertEqual(0, np.max(np.abs(cell.hourly_share.magnitude)))

    def test_attribution_cells_slot_multiplicities_partition_per_rsn(self):
        """Test that the (rsn, ef, up) slot multiplicities of an RSN reached through two edge functions split its
        occurrences with shares summing to 1."""
        shared_rsn_cells = [cell for cell in self.dual_job.attribution_cells if cell.rsn == self.shared_rsn]
        self.assertEqual(2, len(shared_rsn_cells))
        self.assertEqual({self.ef1.id, self.ef2.id}, {cell.ef.id for cell in shared_rsn_cells})
        for cell in shared_rsn_cells:
            self.assertAlmostEqual(0.5, cell.slot_multiplicity, places=6)
        other_rsn_cells = [cell for cell in self.dual_job.attribution_cells if cell.rsn == self.other_rsn]
        self.assertEqual(1, len(other_rsn_cells))
        self.assertAlmostEqual(1, other_rsn_cells[0].slot_multiplicity, places=6)

    def test_attribution_cells_web_cells_carry_step_and_up_coordinates(self):
        """Test that web cells enumerate every (step, up) the job runs in with no edge coordinates."""
        web_cells = [cell for cell in self.dual_job.attribution_cells if cell.step is not None]
        self.assertEqual(
            {(self.step_a.id, self.up1.id), (self.step_a.id, self.up2.id),
             (self.step_b.id, self.up1.id), (self.step_b.id, self.up2.id)},
            {(cell.step.id, cell.up.id) for cell in web_cells})
        for cell in web_cells:
            self.assertIsNone(cell.rsn)
            self.assertIsNone(cell.ef)
            self.assertEqual(1, cell.slot_multiplicity)


if __name__ == "__main__":
    unittest.main()
