"""Integrity checks for the big-system fixture.

The fixture is gitignored (too heavy to commit) and regenerated locally with
`python tests/performance_tests/generate_big_system.py`; these tests are skipped when it is
absent (e.g. in CI). They guard against fixture drift: a fixture saved with an older serialized
shape can load but crash on the first live update.
"""
import json
import os
from unittest import TestCase, skipUnless
from unittest.mock import patch

from efootprint.abstract_modeling_classes.modeling_object import (
    invalidate_slots_system_wide, pull_slots_system_wide)
from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot, _compute_stack
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from tests.performance_tests.generate_big_system import BIG_SYSTEM_FIXTURE

fixture_exists = os.path.exists(BIG_SYSTEM_FIXTURE)


@skipUnless(fixture_exists, "big-system fixture not generated locally")
class TestBigSystemFixture(TestCase):
    def test_fixture_loads_without_any_computation_and_accepts_updates(self):
        """Test that the canonical fixture loads with zero slot computations (stored values attach as
        trusted caches) and supports live updates afterwards."""
        with open(BIG_SYSTEM_FIXTURE) as file:
            system_dict = json.load(file)

        computed_slot_names = []
        original_compute = ReactiveSlot._compute

        def counting_compute(slot):
            computed_slot_names.append(slot.name)
            return original_compute(slot)

        with patch.object(ReactiveSlot, "_compute", counting_compute):
            class_obj_dict, _, _ = json_to_system(system_dict)

        self.assertEqual([], computed_slot_names)
        system = next(iter(class_obj_dict["System"].values()))
        initial_footprint = system.total_footprint
        job = next(iter(class_obj_dict["Job"].values()))

        job.data_transferred = SourceValue(2 * job.data_transferred.value)

        self.assertNotEqual(initial_footprint, system.total_footprint)

    def test_full_computation_recursion_depth_stays_bounded(self):
        """Test that computing the big fixture from inputs keeps the compute-stack depth (the pull
        recursion, which follows the longest dependency chain, not the model size) within a small
        fraction of the interpreter's recursion budget."""
        with open(BIG_SYSTEM_FIXTURE) as file:
            system_dict = json.load(file)

        class_obj_dict, _, _ = json_to_system(system_dict)
        system = next(iter(class_obj_dict["System"].values()))
        invalidate_slots_system_wide([system])

        max_depth = 0
        original_compute = ReactiveSlot._compute

        def depth_tracking_compute(slot):
            nonlocal max_depth
            max_depth = max(max_depth, len(_compute_stack.get()) + 1)
            return original_compute(slot)

        with patch.object(ReactiveSlot, "_compute", depth_tracking_compute):
            pull_slots_system_wide([system])

        self.assertGreater(max_depth, 5)
        self.assertLess(max_depth, 100, f"compute-stack depth reached {max_depth}")
