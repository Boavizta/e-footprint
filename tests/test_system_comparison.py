import os
import unittest
from datetime import datetime, timedelta
from unittest import TestCase

import numpy as np

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

    def test_time_series_per_phase_split_reconstructs_the_total(self):
        """Test usage + fabrication equals the combined total hour-by-hour on the shared axis, for both
        systems — so a consumer can split each period exactly instead of with a full-period ratio."""
        time_series = self.comparison.time_series
        for usage, fabrication, total in (
                (time_series.usage_a, time_series.fabrication_a, time_series.values_a),
                (time_series.usage_b, time_series.fabrication_b, time_series.values_b)):
            self.assertEqual(len(usage), len(total))
            self.assertEqual(len(fabrication), len(total))
            self.assertTrue(np.allclose(usage + fabrication, total, atol=1e-2))

    def test_time_series_per_phase_split_is_per_period_not_a_global_ratio(self):
        """Test the per-phase series carry a genuinely per-period mix: a system whose usage is front-loaded
        in year 1 and sparse in year 2 has a different usage/fabrication ratio each year, which a single
        full-period ratio would not reproduce. This is what makes the per-year split exact."""
        # ~14 months: heavy usage early (year 1), a sparse tail in year 2 → non-uniform yearly mix.
        starts = [5] * 4000 + [0] * 5000 + [0.1] * 1000
        system = build_system("front loaded", "fl server", hourly_starts=starts, start="2025-01-01")
        time_series = system.compare_to(system).time_series

        usage_by_year, fabrication_by_year = {}, {}
        for hour_offset, (usage, fabrication) in enumerate(zip(time_series.usage_a, time_series.fabrication_a)):
            year = (time_series.start_date + timedelta(hours=hour_offset)).year
            usage_by_year[year] = usage_by_year.get(year, 0.0) + float(usage)
            fabrication_by_year[year] = fabrication_by_year.get(year, 0.0) + float(fabrication)

        self.assertEqual({2025, 2026}, set(usage_by_year))
        share = {year: usage_by_year[year] / (usage_by_year[year] + fabrication_by_year[year])
                 for year in usage_by_year}
        # The two years' usage shares differ materially — a global ratio applied to both would be wrong.
        self.assertGreater(abs(share[2025] - share[2026]), 0.05)

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

    def test_input_diff_surfaces_a_changed_usage_journey_step_weight(self):
        """Test a difference consisting ONLY of a changed dict-relationship count (a uj_steps weight) is
        detected — these counts are ExplainableObjectDict values the scalar diff walk skips."""
        from efootprint.core.usage.usage_journey import UsageJourney

        uj_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, UsageJourney))
        step = next(iter(uj_b.uj_steps))
        uj_b.uj_steps[step] = SourceValue(3 * u.dimensionless)

        diff = self.system_a.compare_to(self.system_b).input_diff

        self.assertEqual([], diff.only_in_a)
        self.assertEqual([], diff.only_in_b)
        changed = [row for row in diff.changed if row.attribute.startswith("Times per journey")]
        self.assertEqual(1, len(changed))
        self.assertEqual("UsageJourney", changed[0].object_class)
        self.assertIn(step.name, changed[0].attribute)
        self.assertEqual("1", changed[0].value_a)
        self.assertEqual("3", changed[0].value_b)

    def test_input_diff_does_not_duplicate_a_dict_member_living_in_only_one_model(self):
        """Test a brand-new dict key (a job present only in B) is reported once — as an only-in object —
        not also as a membership add row on its parent, which would merely duplicate the only-in row."""
        from efootprint.core.hardware.server import Server
        from efootprint.core.usage.job import Job
        from efootprint.core.usage.usage_journey_step import UsageJourneyStep

        step_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, UsageJourneyStep))
        server_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, Server))
        step_b.jobs[Job.from_defaults("extra job", server=server_b)] = SourceValue(2 * u.dimensionless)

        diff = self.system_a.compare_to(self.system_b).input_diff

        self.assertIn("extra job", {obj.object_name for obj in diff.only_in_b})
        # The brand-new job is reported once (above); it must NOT also produce a membership row, so the
        # only changed attribute stays the server power edited in setUp — pinning the whole set rather than
        # a single label keeps the assertion from passing vacuously if a spurious row reappeared.
        self.assertEqual({"power"}, {row.attribute for row in diff.changed})

    def test_input_diff_does_not_duplicate_a_list_member_living_in_only_one_model(self):
        """Test a brand-new list link (a device present only in B) is reported once — as an only-in
        object — not also as a present/absent membership row on its parent, which would duplicate it."""
        up_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, UsagePattern))
        up_b.devices = list(up_b.devices) + [Device.smartphone("extra device")]

        diff = self.system_a.compare_to(self.system_b).input_diff

        self.assertIn("extra device", {obj.object_name for obj in diff.only_in_b})
        # Reported once (above); no membership row too, so the only changed attribute stays the server
        # power edited in setUp (pinning the whole set, not one label, so the check can't pass vacuously).
        self.assertEqual({"power"}, {row.attribute for row in diff.changed})

    def test_input_diff_keeps_a_membership_change_for_a_member_present_in_both_models(self):
        """Test a genuine re-link survives: a device present in BOTH models but linked to the paired usage
        pattern in A only surfaces as a present/absent row. There is no only-in row to duplicate (the device
        exists on both sides), so the only-in-one-model suppression must not fire here."""
        from efootprint.core.usage.usage_journey import UsageJourney

        up_a = next(o for o in self.system_a.all_linked_objects if isinstance(o, UsagePattern))
        up_a.devices = list(up_a.devices) + [Device.laptop("shared spare device")]
        # The same device (same name+type → pairs by identity) exists in B too, but hangs off a *second*
        # usage pattern rather than the paired one — so it is present in B (no only-in row) yet absent from
        # the paired pattern's device list, i.e. a genuine re-link.
        uj_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, UsageJourney))
        network_b = next(o for o in self.system_b.all_linked_objects if isinstance(o, Network))
        second_up_b = UsagePattern(
            "model B second pattern", uj_b, [Device.laptop("shared spare device")], network_b,
            Countries.FRANCE(),
            create_source_hourly_values_from_list([1, 2, 4, 5, 8, 12, 2, 2, 3], datetime(2025, 1, 1)))
        self.system_b.usage_patterns = list(self.system_b.usage_patterns) + [second_up_b]

        diff = self.system_a.compare_to(self.system_b).input_diff

        self.assertNotIn("shared spare device", {obj.object_name for obj in diff.only_in_a})
        self.assertNotIn("shared spare device", {obj.object_name for obj in diff.only_in_b})
        relink = [row for row in diff.changed if row.attribute == "devices (shared spare device)"]
        self.assertEqual(1, len(relink))
        self.assertEqual("UsagePattern", relink[0].object_class)
        self.assertEqual("present", relink[0].value_a)
        self.assertIsNone(relink[0].value_b)

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
