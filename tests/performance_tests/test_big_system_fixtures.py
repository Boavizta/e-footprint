"""Integrity checks for the big-system fixtures.

The fixtures are gitignored (too heavy to commit) and regenerated locally with
`python tests/performance_tests/generate_big_system.py`; these tests are skipped when they are
absent (e.g. in CI). They guard against fixture drift: a fixture saved with an older serialized
shape can load but crash on the first live update.
"""
import json
import os
from unittest import TestCase, skipUnless
from unittest.mock import patch

from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot, _compute_stack
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from tests.performance_tests.generate_big_system import INPUTS_ONLY_FIXTURE, WITH_CALC_ATTR_FIXTURE

fixtures_exist = os.path.exists(INPUTS_ONLY_FIXTURE) and os.path.exists(WITH_CALC_ATTR_FIXTURE)


@skipUnless(fixtures_exist, "big-system fixtures not generated locally")
class TestBigSystemFixtures(TestCase):
    def test_inputs_only_fixture_loads(self):
        """Test that the inputs-only fixture loads with the current engine."""
        with open(INPUTS_ONLY_FIXTURE) as file:
            system_dict = json.load(file)

        class_obj_dict, _, _ = json_to_system(system_dict, launch_system_computations=False)

        self.assertEqual(1, len(class_obj_dict["System"]))

    def test_with_calc_attr_fixture_loads_and_accepts_updates(self):
        """Test that the calculated-attributes fixture loads without recomputation and supports live updates."""
        with open(WITH_CALC_ATTR_FIXTURE) as file:
            system_dict = json.load(file)

        class_obj_dict, _, _ = json_to_system(system_dict, launch_system_computations=False)
        system = next(iter(class_obj_dict["System"].values()))
        initial_footprint = system.total_footprint
        job = next(iter(class_obj_dict["Job"].values()))

        job.data_transferred = SourceValue(2 * job.data_transferred.value)

        self.assertNotEqual(initial_footprint, system.total_footprint)

    def test_full_computation_recursion_depth_stays_bounded(self):
        """Test that computing the big fixture from inputs keeps the compute-stack depth (the pull
        recursion, which follows the longest dependency chain, not the model size) within a small
        fraction of the interpreter's recursion budget."""
        with open(INPUTS_ONLY_FIXTURE) as file:
            system_dict = json.load(file)

        max_depth = 0
        original_compute = ReactiveSlot._compute

        def depth_tracking_compute(slot):
            nonlocal max_depth
            max_depth = max(max_depth, len(_compute_stack.get()) + 1)
            return original_compute(slot)

        with patch.object(ReactiveSlot, "_compute", depth_tracking_compute):
            class_obj_dict, _, _ = json_to_system(system_dict, launch_system_computations=True)

        self.assertGreater(max_depth, 5)
        self.assertLess(max_depth, 100, f"compute-stack depth reached {max_depth}")
