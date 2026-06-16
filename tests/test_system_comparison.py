import os
import unittest
from datetime import datetime
from unittest import TestCase

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.comparison.duplication import assign_fresh_system_id, duplicate_system
from efootprint.comparison.system_comparison import PHASES, SystemComparison
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

os.environ.setdefault("MPLBACKEND", "Agg")


def build_system(system_name, server_name, hourly_starts=None, start="2025-01-01"):
    """Build a minimal but complete web system. Distinct names per object so ids stay unique under
    the test name-as-id convention."""
    storage = Storage.from_defaults(f"{server_name} storage")
    server = Server.from_defaults(server_name, server_type=ServerTypes.on_premise(), storage=storage)
    job = Job.from_defaults(f"{server_name} job", server=server)
    uj_step = UsageJourneyStep.from_defaults(f"{system_name} step", jobs=[job])
    uj = UsageJourney(f"{system_name} journey", uj_steps=[uj_step])
    network = Network.from_defaults(f"{system_name} network")
    start_date = datetime.strptime(start, "%Y-%m-%d")
    hourly_starts = hourly_starts if hourly_starts is not None else [1, 2, 4, 5, 8, 12, 2, 2, 3]
    usage_pattern = UsagePattern(
        f"{system_name} usage pattern", uj, [Device.laptop()], network, Countries.FRANCE(),
        create_source_hourly_values_from_list([elt * 1000000 for elt in hourly_starts], start_date))

    return System(system_name, [usage_pattern], edge_usage_patterns=[])


class TestDuplicateSystem(TestCase):
    def test_duplicate_system_mints_fresh_system_id_and_preserves_object_ids(self):
        """Test duplicate_system gives a new System id while every other object keeps its id."""
        system = build_system("original", "server A")

        duplicate = duplicate_system(system)

        self.assertNotEqual(system.id, duplicate.id)
        self.assertEqual(
            sorted(obj.id for obj in system.all_linked_objects),
            sorted(obj.id for obj in duplicate.all_linked_objects))

    def test_assign_fresh_system_id_changes_only_the_system_id(self):
        """Test assign_fresh_system_id re-ids the System and leaves object ids intact."""
        system = build_system("original", "server A")
        old_system_id = system.id
        old_object_ids = sorted(obj.id for obj in system.all_linked_objects)

        assign_fresh_system_id(system)

        self.assertNotEqual(old_system_id, system.id)
        self.assertEqual(old_object_ids, sorted(obj.id for obj in system.all_linked_objects))


class TestSystemComparison(TestCase):
    def setUp(self):
        self.system_a = build_system("model A", "shared server")
        self.system_b = duplicate_system(self.system_a)
        edited_server = next(o for o in self.system_b.all_linked_objects if isinstance(o, Server))
        edited_server.power = SourceValue(500 * u.W)
        self.comparison = self.system_a.compare_to(self.system_b)

    def test_compare_to_returns_system_comparison(self):
        """Test System.compare_to returns a SystemComparison over the two systems."""
        self.assertIsInstance(self.comparison, SystemComparison)
        self.assertIs(self.comparison.system_a, self.system_a)
        self.assertIs(self.comparison.system_b, self.system_b)

    def test_total_delta_arithmetic(self):
        """Test the headline delta is after − before, with the relative fraction over the baseline."""
        delta = self.comparison.total_delta
        self.assertEqual(delta.before, self.comparison.total_a)
        self.assertEqual(delta.after, self.comparison.total_b)
        self.assertAlmostEqual(delta.absolute, delta.after - delta.before)
        self.assertAlmostEqual(delta.relative, delta.absolute / delta.before)

    def test_relative_delta_is_none_without_baseline(self):
        """Test the relative delta is None when the baseline is zero (no division by zero)."""
        from efootprint.comparison.system_comparison import Delta
        self.assertIsNone(Delta(before=0, after=5).relative)

    def test_decomposition_sums_to_headline_delta(self):
        """Test the per-(category, phase) deltas sum to the headline total delta."""
        decomposition_sum = sum(row.delta.absolute for row in self.comparison.decomposition)
        self.assertAlmostEqual(decomposition_sum, self.comparison.total_delta.absolute, places=2)

    def test_decomposition_covers_every_category_and_phase(self):
        """Test the decomposition has exactly one row per (OBJECT_CATEGORIES, phase)."""
        from efootprint.all_classes_in_order import OBJECT_CATEGORIES
        keys = {(row.category, row.phase) for row in self.comparison.decomposition}
        self.assertEqual(keys, {(cat, phase) for cat in OBJECT_CATEGORIES for phase in PHASES})

    def test_time_series_aligned_and_cumulative(self):
        """Test the two systems' series share one axis and the cumulative sum ends at the period total."""
        time_series = self.comparison.time_series
        self.assertEqual(len(time_series.values_a), len(time_series.values_b))
        self.assertEqual(len(time_series.hours), len(time_series.values_a))
        self.assertAlmostEqual(float(time_series.cumulative_a[-1]), self.comparison.total_a, places=1)
        self.assertAlmostEqual(float(time_series.cumulative_b[-1]), self.comparison.total_b, places=1)

    def test_time_series_aligns_differing_calendars(self):
        """Test systems with different start dates are aligned onto a shared, longer calendar axis without
        losing or misplacing any value (cumulative end still equals each system's own period total)."""
        other = build_system("model C", "server C", start="2025-02-01")
        comparison = self.system_a.compare_to(other)
        time_series = comparison.time_series
        self.assertEqual(len(time_series.values_a), len(time_series.values_b))
        self.assertGreater(len(time_series.values_a), len(self.system_a.total_footprint.value))
        self.assertAlmostEqual(float(time_series.cumulative_a[-1]), comparison.total_a, places=1)
        self.assertAlmostEqual(float(time_series.cumulative_b[-1]), comparison.total_b, places=1)

    def test_input_diff_emits_only_changed_attributes_for_paired_objects(self):
        """Test the diff lists the changed input attribute (value + source) and nothing identical."""
        diff = self.comparison.input_diff
        self.assertEqual([], diff.only_in_a)
        self.assertEqual([], diff.only_in_b)
        changed = [row for row in diff.changed if row.attribute == "power"]
        self.assertEqual(1, len(changed))
        self.assertEqual("Server", changed[0].object_class)
        self.assertEqual("300.0 watt", changed[0].value_a)
        self.assertEqual("500.0 watt", changed[0].value_b)

    def test_input_diff_matches_by_id_first(self):
        """Test renaming an object in B still pairs it by id (no spurious only-in entries)."""
        renamed_server = next(o for o in self.system_b.all_linked_objects if isinstance(o, Server))
        renamed_server.name = "renamed shared server"

        diff = self.system_a.compare_to(self.system_b).input_diff

        self.assertEqual([], diff.only_in_a)
        self.assertEqual([], diff.only_in_b)

    def test_input_diff_falls_back_to_name_and_type_then_only_in_a_b(self):
        """Test independently built systems (fresh ids) pair shared (name, type) objects — so an edited input
        surfaces as a changed row through the fallback path — and report nothing as A/B-only."""
        independent = build_system("model A", "shared server")  # same names, fresh ids → forces (name, type) match
        edited_server = next(o for o in independent.all_linked_objects if isinstance(o, Server))
        edited_server.power = SourceValue(500 * u.W)

        diff = self.system_a.compare_to(independent).input_diff

        self.assertEqual([], diff.only_in_a)
        self.assertEqual([], diff.only_in_b)
        changed = [row for row in diff.changed if row.attribute == "power"]
        self.assertEqual(1, len(changed))
        self.assertEqual("Server", changed[0].object_class)
        self.assertEqual("300.0 watt", changed[0].value_a)
        self.assertEqual("500.0 watt", changed[0].value_b)

    def test_input_diff_reports_unmatched_objects(self):
        """Test objects present in only one system are reported as A-only / B-only."""
        independent = build_system("model D", "server D")
        diff = self.system_a.compare_to(independent).input_diff

        self.assertTrue(diff.only_in_a)
        self.assertTrue(diff.only_in_b)
        names_only_in_b = {row.object_name for row in diff.only_in_b}
        self.assertIn("server D", names_only_in_b)

    def test_plot_helpers_smoke_render(self):
        """Test the notebook plot helpers render without error."""
        from matplotlib import pyplot as plt
        for plot in (self.comparison.plot_emissions_over_time, self.comparison.plot_cumulative_emissions,
                     self.comparison.plot_decomposition):
            figure, axes = plot()
            self.assertIsNotNone(figure)
            self.assertIsNotNone(axes)
            plt.close(figure)


if __name__ == "__main__":
    unittest.main()
