"""Recompute-counter variant of the parity harness.

Instruments slot computations to check invalidation granularity — an edit on one usage pattern must
only recompute slots in that pattern's dependency cone — and counts recomputations that produce a
value equal to the one they replaced. The equal-value frequency is reported so the decision on a
selective early-cutoff invalidation mode can be made on data at the performance checkpoint.
"""
from unittest import TestCase
from unittest.mock import patch

from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot, computed_slots, instance_slot_registry
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.logger import logger
from tests.performance_tests.generate_big_system import generate_big_system, form_inputs_hourly_starts

NB_YEARS = 1


class RecomputeRecorder:
    """Patches ReactiveSlot._compute to record the name of every slot computed while active."""

    def __init__(self):
        self.computed_slot_names = []
        self._original_compute = ReactiveSlot._compute

    def __enter__(self):
        recorder = self

        def recording_compute(slot):
            recorder.computed_slot_names.append(slot.name)
            return recorder._original_compute(slot)

        self._patcher = patch.object(ReactiveSlot, "_compute", recording_compute)
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._patcher.stop()


class TestRecomputeCounter(TestCase):
    @staticmethod
    def build_system():
        return generate_big_system(
            nb_of_servers_of_each_type=1, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=2,
            nb_of_up_per_uj=2, nb_of_edge_usage_patterns=2,
            nb_of_edge_processes_and_server_needs_per_edge_computer=2, nb_of_jobs_per_server_need=1,
            nb_years=NB_YEARS)

    @staticmethod
    def snapshot_cached_slot_values(system):
        snapshot = {}
        for obj in [system] + system.all_linked_objects:
            for slot in instance_slot_registry(obj).values():
                if slot.getter is not None and slot.has_cached_value:
                    snapshot[slot.name] = (slot, slot._value)
        return snapshot

    def test_one_usage_pattern_edit_touches_only_its_slot_cone(self):
        """Test that replacing one usage pattern's traffic timeseries recomputes slots only in its
        dependency cone: unrelated usage patterns, the edge side of the model, and devices serving
        only other patterns stay cached."""
        system = self.build_system()
        edited_pattern = system.usage_patterns[0]
        other_patterns = list(system.usage_patterns[1:]) + list(system.edge_usage_patterns)

        with RecomputeRecorder() as recorder:
            edited_pattern.hourly_usage_journey_starts = form_inputs_hourly_starts(NB_YEARS, initial_volume=1234.5)

        recomputed = set(recorder.computed_slot_names)
        self.assertGreater(len(recomputed), 0)

        self.assertIn(f"utc_hourly_usage_journey_starts of {edited_pattern.id}", recomputed)
        self.assertIn(f"total_footprint of {system.id}", recomputed)

        # Slots that only depend on other patterns' traffic must not recompute.
        for pattern in other_patterns:
            for slot_name in recomputed:
                self.assertFalse(
                    slot_name.startswith("utc_hourly") and slot_name.endswith(f"of {pattern.id}"),
                    f"{slot_name} recomputed but belongs to an unrelated usage pattern")
        edge_object_ids = {obj.id for obj in system.get_objects_linked_to_edge_usage_patterns(
            system.edge_usage_patterns)}
        for slot_name in recomputed:
            owner_id = slot_name.rsplit(" of ", 1)[-1]
            self.assertNotIn(
                owner_id, edge_object_ids,
                f"{slot_name} recomputed but its owner is only linked to the edge side of the model")

    def test_one_input_edit_invalidates_only_the_matrix_rows_in_its_cone(self):
        """Test that with the impact-repartition matrix materialized, a one-input edit voids only the
        per-source row slots in its dependency cone: re-reading the matrix recomputes the edited server's
        rows and the matrix concatenation, nothing else in the lazy attribution layer."""
        system = self.build_system()
        _ = system.impact_repartition_matrix
        edited_server = system.servers[0]
        untouched_rows_before = {
            source.id: source.impact_repartition_rows
            for source in [system.servers[1], system.networks[0], system.devices[0]]}

        edited_server.lifespan = SourceValue(edited_server.lifespan.value * 1.5)

        with RecomputeRecorder() as recorder:
            _ = system.impact_repartition_matrix
        self.assertEqual(
            {f"impact_repartition_rows of {edited_server.id}", f"impact_repartition_matrix of {system.id}"},
            set(recorder.computed_slot_names))
        for source_id, rows in untouched_rows_before.items():
            source = next(obj for obj in system.all_linked_objects if obj.id == source_id)
            self.assertIs(rows, source.impact_repartition_rows)

    def test_equal_value_recompute_frequency_is_measured(self):
        """Test that recomputations yielding a value equal to the replaced one are counted — the
        measurement that feeds the decision on a selective early-cutoff invalidation mode."""
        system = self.build_system()
        representative_edits = [
            lambda: setattr(
                system.usage_patterns[0], "hourly_usage_journey_starts",
                form_inputs_hourly_starts(NB_YEARS, initial_volume=987.6)),
            lambda: setattr(
                system.servers[0], "lifespan", SourceValue(system.servers[0].lifespan.value * 1.5)),
            lambda: setattr(
                system.usage_patterns[1], "devices", list(system.usage_patterns[1].devices[:1])),
        ]

        total_recomputes = 0
        equal_value_recomputes = 0
        for edit in representative_edits:
            snapshot = self.snapshot_cached_slot_values(system)
            with RecomputeRecorder() as recorder:
                edit()
            total_recomputes += len(recorder.computed_slot_names)
            for slot_name in recorder.computed_slot_names:
                snapshotted = snapshot.get(slot_name)
                if snapshotted is None:
                    continue
                slot, previous_value = snapshotted
                if slot.has_cached_value and slot._value == previous_value:
                    equal_value_recomputes += 1

        logger.info(
            f"Recompute counter over {len(representative_edits)} representative edits: "
            f"{total_recomputes} slot recomputations, {equal_value_recomputes} of which produced a value "
            f"equal to the one they replaced "
            f"({round(100 * equal_value_recomputes / total_recomputes, 1)}%).")
        self.assertGreater(total_recomputes, 0)
        self.assertGreaterEqual(equal_value_recomputes, 0)
