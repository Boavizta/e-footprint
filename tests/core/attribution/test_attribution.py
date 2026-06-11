import unittest
from datetime import datetime
from unittest import TestCase

import pytz

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.attribution import (
    atoms, atoms_of, attributed_footprint, footprint_per_node, footprint_per_node_per_source, node_totals_and_links)
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import (
    assert_hourly_quantities_equal, assert_source_atoms_conserve, sum_atom_values)


class TrackedDevice(Device):
    """Device subclass distinguishable by class for exclusion tests."""
    default_values = {**Device.default_values}


ALL_LEVELS = (Device, UsageJourneyStep, UsageJourney, UsagePattern, Country)


class TestAttributionFold(TestCase):
    """The fold's structural invariants and cache behaviour, exercised end to end on a real multi-pattern,
    multi-country model through its first atom builder (Device)."""

    @classmethod
    def setUpClass(cls):
        def country(name, carbon_intensity):
            return Country(name, name[:3].upper(), SourceValue(carbon_intensity),
                           ExplainableTimezone(pytz.utc, "UTC timezone"))

        cls.step_a = UsageJourneyStep("fold step a", SourceValue(20 * u.min), [])
        cls.step_b = UsageJourneyStep("fold step b", SourceValue(40 * u.min), [])
        cls.journey = UsageJourney("fold journey", [cls.step_a, cls.step_b])
        cls.step_c = UsageJourneyStep("fold step c", SourceValue(30 * u.min), [])
        cls.other_journey = UsageJourney("fold other journey", [cls.step_c])

        cls.device = Device.from_defaults("fold laptop")
        cls.tracked_device = TrackedDevice.from_defaults("fold tracked smartphone")
        network = Network("fold network", SourceValue(0.05 * u.kWh / u.GB))
        cls.low_ci_country = country("fold low ci country", 80 * u.g / u.kWh)
        start_date = datetime(2026, 1, 1)
        cls.up1 = UsagePattern(
            "fold usage pattern 1", cls.journey, [cls.device, cls.tracked_device], network, cls.low_ci_country,
            create_source_hourly_values_from_list([12, 0, 7, 3], start_date))
        cls.up2 = UsagePattern(
            "fold usage pattern 2", cls.journey, [cls.device], network,
            country("fold high ci country", 450 * u.g / u.kWh),
            create_source_hourly_values_from_list([2, 9], start_date))
        cls.up3 = UsagePattern(
            "fold usage pattern 3", cls.other_journey, [cls.device], network, cls.low_ci_country,
            create_source_hourly_values_from_list([5, 5, 5], start_date))

        cls.system = System("fold system", [cls.up1, cls.up2, cls.up3], edge_usage_patterns=[])

    def test_device_atoms_conserve_through_generic_harness(self):
        """Test that both devices' atoms conserve each phase's eager total (single stream per phase)."""
        for device in (self.device, self.tracked_device):
            assert_source_atoms_conserve(
                self, device,
                stream_footprints_by_phase={
                    LifeCyclePhases.USAGE: {"single": device.energy_footprint},
                    LifeCyclePhases.MANUFACTURING: {"single": device.instances_fabrication_footprint}})

    def test_fold_node_totals_balance_incoming_and_outgoing_links(self):
        """Test that at every node of the full fold, Σ incoming links == node total == Σ outgoing links
        (whenever the node has incoming / outgoing links)."""
        for phase in LifeCyclePhases:
            node_totals, links = node_totals_and_links(self.system, phase, ALL_LEVELS)
            for node, total in node_totals.items():
                incoming = [value for (_, coarser), value in links.items() if coarser == node]
                outgoing = [value for (finer, _), value in links.items() if finer == node]
                if incoming:
                    assert_hourly_quantities_equal(
                        self, total, sum(incoming, start=0 * u.kg),
                        msg=f"Incoming links don't sum to {node.name} total in {phase.value}")
                if outgoing:
                    assert_hourly_quantities_equal(
                        self, total, sum(outgoing, start=0 * u.kg),
                        msg=f"Outgoing links don't sum to {node.name} total in {phase.value}")

    def test_fold_column_sums_equal_phase_total_at_every_level(self):
        """Test that summing node totals over each level recovers the full atom sum (columns conserve)."""
        for phase in LifeCyclePhases:
            full_atom_sum = sum_atom_values(atoms(self.system, phase))
            node_totals, _ = node_totals_and_links(self.system, phase, ALL_LEVELS)
            for level in ALL_LEVELS:
                level_sum = sum(
                    (total for node, total in node_totals.items() if isinstance(node, level)),
                    start=0 * u.kg)
                assert_hourly_quantities_equal(
                    self, full_atom_sum.sum().value, level_sum,
                    msg=f"{level.__name__} column doesn't conserve the {phase.value} total")

    def test_column_skip_equals_regrouping_the_full_fold(self):
        """Test that folding with the UsageJourney level hidden preserves the surviving node totals and links
        steps directly to patterns with the values of the atom-level (step, up) regroup."""
        phase = LifeCyclePhases.USAGE
        visible_levels_without_journey = (Device, UsageJourneyStep, UsagePattern, Country)
        full_node_totals, _ = node_totals_and_links(self.system, phase, ALL_LEVELS)
        skipped_node_totals, skipped_links = node_totals_and_links(
            self.system, phase, visible_levels_without_journey)

        self.assertEqual(
            {node.id for node in full_node_totals if not isinstance(node, UsageJourney)},
            {node.id for node in skipped_node_totals})
        for node, total in skipped_node_totals.items():
            assert_hourly_quantities_equal(self, full_node_totals[node], total)

        expected_step_to_up = {}
        for atom in atoms(self.system, phase):
            key = (atom.step, atom.up)
            expected_step_to_up[key] = expected_step_to_up.get(key, EmptyExplainableObject()) + atom.value
        step_to_up_links = {
            (finer, coarser): value for (finer, coarser), value in skipped_links.items()
            if isinstance(finer, UsageJourneyStep) and isinstance(coarser, UsagePattern)}
        self.assertEqual(
            {(finer.id, coarser.id) for finer, coarser in expected_step_to_up},
            {(finer.id, coarser.id) for finer, coarser in step_to_up_links})
        for key, expected_value in expected_step_to_up.items():
            assert_hourly_quantities_equal(self, expected_value.sum().value, step_to_up_links[key])

    def test_exclusion_filters_atoms_without_rescaling(self):
        """Test that excluding a source class removes its atoms and leaves every other contribution
        untouched (no rescale)."""
        phase = LifeCyclePhases.MANUFACTURING
        full_node_totals, _ = node_totals_and_links(self.system, phase, ALL_LEVELS)
        excluded_node_totals, _ = node_totals_and_links(
            self.system, phase, ALL_LEVELS, exclude=(TrackedDevice,))

        self.assertNotIn(self.tracked_device, excluded_node_totals)
        self.assertIn(self.tracked_device, full_node_totals)
        assert_hourly_quantities_equal(
            self, full_node_totals[self.device], excluded_node_totals[self.device])
        tracked_up1_contribution = sum_atom_values(
            atom for atom in atoms_of(self.tracked_device, phase) if atom.up == self.up1)
        assert_hourly_quantities_equal(
            self, full_node_totals[self.up1] - tracked_up1_contribution.sum().value,
            excluded_node_totals[self.up1])

    def test_footprint_per_node_matches_eager_per_usage_pattern_dicts(self):
        """Test that the per-UsagePattern programmatic read recovers the devices' eager per-pattern dicts."""
        per_up = footprint_per_node(self.system, UsagePattern, LifeCyclePhases.USAGE)
        assert_hourly_quantities_equal(
            self,
            self.device.energy_footprint_per_usage_pattern[self.up1]
            + self.tracked_device.energy_footprint_per_usage_pattern[self.up1],
            per_up[self.up1])
        assert_hourly_quantities_equal(
            self, self.device.energy_footprint_per_usage_pattern[self.up3], per_up[self.up3])

    def test_footprint_per_node_per_source_separates_sources(self):
        """Test that the per-source variant keys each (source, node) cell with the source's own contribution."""
        per_up_per_source = footprint_per_node_per_source(self.system, UsagePattern, LifeCyclePhases.USAGE)
        assert_hourly_quantities_equal(
            self, self.device.energy_footprint_per_usage_pattern[self.up1],
            per_up_per_source[(self.device, self.up1)])
        assert_hourly_quantities_equal(
            self, self.tracked_device.energy_footprint_per_usage_pattern[self.up1],
            per_up_per_source[(self.tracked_device, self.up1)])
        self.assertNotIn((self.tracked_device, self.up2), per_up_per_source)

    def test_country_groups_usage_patterns_orthogonally_to_journeys(self):
        """Test that a country node sums the per-pattern totals of its patterns across different journeys."""
        per_up = footprint_per_node(self.system, UsagePattern, LifeCyclePhases.USAGE)
        per_country = footprint_per_node(self.system, Country, LifeCyclePhases.USAGE)
        assert_hourly_quantities_equal(
            self, per_up[self.up1] + per_up[self.up3], per_country[self.low_ci_country])

    def test_memo_hit_within_a_query(self):
        """Test that atom lists and folded results are memoized: same args return the same objects, and list
        args normalize to the same key as tuple args."""
        phase = LifeCyclePhases.USAGE
        self.assertIs(atoms_of(self.device, phase), atoms_of(self.device, phase))
        self.assertIs(
            node_totals_and_links(self.system, phase, ALL_LEVELS),
            node_totals_and_links(self.system, phase, list(ALL_LEVELS)))

    def test_modeling_update_flushes_attribution_memos_and_cached_primitives(self):
        """Test that an input change wipes every render cache and cached primitive system-wide, so the next
        query rebuilds atoms that conserve the new eager totals."""
        phase = LifeCyclePhases.USAGE
        stale_atoms = atoms_of(self.device, phase)
        node_totals_and_links(self.system, phase, ALL_LEVELS)
        self.assertIn("render_cache", self.device.__dict__)
        initial_power = self.device.power
        try:
            self.device.power = SourceValue(100 * u.W)
            self.assertNotIn("render_cache", self.device.__dict__)
            self.assertNotIn("render_cache", self.system.__dict__)
            self.assertNotIn("hourly_avg_occurrences_per_usage_pattern", self.step_a.__dict__)
            fresh_atoms = atoms_of(self.device, phase)
            self.assertIsNot(stale_atoms, fresh_atoms)
            assert_hourly_quantities_equal(self, self.device.energy_footprint, sum_atom_values(fresh_atoms))
        finally:
            self.device.power = initial_power

    def test_attributed_footprint_equals_footprint_per_node_entry(self):
        """Test that the attributed_footprint convenience read is an exact delegation: each object's value
        equals its node entry in footprint_per_node at its own class level, for each phase."""
        for obj, level in ((self.device, Device), (self.step_a, UsageJourneyStep), (self.journey, UsageJourney),
                           (self.up1, UsagePattern), (self.low_ci_country, Country)):
            assert_hourly_quantities_equal(
                self, footprint_per_node(self.system, level, LifeCyclePhases.USAGE)[obj],
                attributed_footprint(obj, LifeCyclePhases.USAGE), msg=f"{obj.name} energy delegation mismatch")
            assert_hourly_quantities_equal(
                self, footprint_per_node(self.system, level, LifeCyclePhases.MANUFACTURING)[obj],
                attributed_footprint(obj, LifeCyclePhases.MANUFACTURING),
                msg=f"{obj.name} fabrication delegation mismatch")

    def test_attributed_footprint_flushes_on_modeling_update(self):
        """Test that a ModelingUpdate flushes the fold memo behind attributed_footprint so the next read
        reflects the new inputs."""
        initial_power = self.device.power
        _ = attributed_footprint(self.up1, LifeCyclePhases.USAGE)
        self.assertIn("render_cache", self.system.__dict__)
        try:
            self.device.power = SourceValue(100 * u.W)
            self.assertNotIn("render_cache", self.system.__dict__)
            assert_hourly_quantities_equal(
                self, footprint_per_node(self.system, UsagePattern, LifeCyclePhases.USAGE)[self.up1],
                attributed_footprint(self.up1, LifeCyclePhases.USAGE))
        finally:
            self.device.power = initial_power

    def test_initial_build_flushes_cached_properties_materialized_before_system_creation(self):
        """Test that a cached property materialized on a not-yet-linked object is flushed by the initial
        build, so post-build reads see the full graph."""
        step = UsageJourneyStep("prebuild step", SourceValue(10 * u.min), [])
        self.assertEqual({}, step.hourly_avg_occurrences_per_usage_pattern)
        journey = UsageJourney("prebuild journey", [step])
        usage_pattern = UsagePattern(
            "prebuild usage pattern", journey, [Device.from_defaults("prebuild laptop")],
            Network("prebuild network", SourceValue(0.05 * u.kWh / u.GB)),
            Country("prebuild country", "PBC", SourceValue(100 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([1, 2], datetime(2026, 1, 1)))
        System("prebuild system", [usage_pattern], edge_usage_patterns=[])

        self.assertIn(usage_pattern, step.hourly_avg_occurrences_per_usage_pattern)


if __name__ == "__main__":
    unittest.main()
