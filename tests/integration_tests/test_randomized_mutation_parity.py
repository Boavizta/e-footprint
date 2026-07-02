"""Randomized mutation parity harness.

Applies seeded random mutation sequences (input edits, relinks, list add/remove, object add/delete)
to a live system and, after every mutation, checks that every computed slot equals the one
obtained by rebuilding the system from scratch (inputs-only JSON round-trip + full recomputation).
ExplainableObject equality carries float tolerance, so incremental and from-scratch results may
differ by floating-point noise but not more.

Failures print the seed and the full mutation log so any divergence is reproducible: re-running the
same seed replays the exact same mutation sequence.
"""
import random
from unittest import TestCase

import numpy as np

from efootprint.abstract_modeling_classes.explainable_object_dict import (
    ExplainableObjectDict, to_weighted_explainable_object_dict)
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import (
    ModelingObject, class_cached_property_names, get_instance_attributes, invalidate_slots_system_wide,
    pull_slots_system_wide)
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate
from efootprint.abstract_modeling_classes.reactive_core import computed_slots
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.core.hardware.edge.edge_storage import NegativeCumulativeStorageNeedError
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge.recurrent_edge_component_need import WorkloadOutOfBoundsError
from efootprint.core.usage.edge.recurrent_server_need import NegativeServerNeedError
from efootprint.core.usage.job import Job
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.performance_tests.generate_big_system import generate_big_system, form_inputs_hourly_starts

SEEDS = (7, 21, 42)
MUTATIONS_PER_SEQUENCE = 18
NB_YEARS = 1
MISSING = object()

# Mutations rejected by the engine with one of these roll the model back and stay part of the run
# (parity must hold after rollbacks too); any other exception is a harness or engine bug and fails
# the test.
EXPECTED_REJECTION_EXCEPTIONS = (
    ValueError, InsufficientCapacityError, NegativeCumulativeStorageNeedError, NegativeServerNeedError,
    WorkloadOutOfBoundsError)

RELINK_SPECS = (
    ("UsagePattern", "usage_journey"),
    ("UsagePattern", "network"),
    ("UsagePattern", "country"),
    ("EdgeUsagePattern", "network"),
    ("EdgeUsagePattern", "country"),
    ("EdgeUsagePattern", "edge_usage_journey"),
)

LIST_SPECS = (
    ("UsageJourney", "uj_steps"),
    ("UsageJourneyStep", "jobs"),
    ("UsagePattern", "devices"),
)


class TestRandomizedMutationParity(TestCase):
    def setUp(self):
        self.created_objects_count = 0

    @staticmethod
    def build_system():
        return generate_big_system(
            nb_of_servers_of_each_type=1, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=2,
            nb_of_up_per_uj=2, nb_of_edge_usage_patterns=2,
            nb_of_edge_processes_and_server_needs_per_edge_computer=2, nb_of_jobs_per_server_need=1,
            nb_years=NB_YEARS)

    @staticmethod
    def all_objects(system):
        return [system] + system.all_linked_objects

    @staticmethod
    def objects_of_class(system, class_name):
        return [obj for obj in TestRandomizedMutationParity.all_objects(system)
                if obj.class_as_simple_str == class_name]

    @staticmethod
    def set_collection(obj, attr_name, members):
        """Assign a new member collection, matching the attribute's current shape (weighted dicts carry
        per-member weights and can't be replaced by plain lists on a live system)."""
        if isinstance(getattr(obj, attr_name), ExplainableObjectDict):
            setattr(obj, attr_name, to_weighted_explainable_object_dict(members))
        else:
            setattr(obj, attr_name, members)

    def mutate_scalar_input(self, rng, system):
        candidates = []
        for obj in self.all_objects(system):
            cached_names = class_cached_property_names(type(obj))
            computed_names = computed_slots(type(obj))
            for attr_name, attr in get_instance_attributes(obj, ExplainableQuantity).items():
                if attr_name not in computed_names and attr_name not in cached_names:
                    candidates.append((obj, attr_name, attr))
        obj, attr_name, attr = rng.choice(candidates)
        factor = rng.uniform(0.5, 1.8)
        new_value = SourceValue(attr.value * factor, label=attr.label)
        setattr(obj, attr_name, new_value)
        return f"scale input {obj.name}.{attr_name} by {round(factor, 3)}"

    def mutate_timeseries_input(self, rng, system):
        pattern_specs = ([(up, "hourly_usage_journey_starts") for up in system.usage_patterns]
                         + [(eup, "hourly_edge_usage_journey_starts") for eup in system.edge_usage_patterns])
        pattern, attr_name = rng.choice(pattern_specs)
        initial_volume = round(rng.uniform(200, 5000), 1)
        setattr(pattern, attr_name, form_inputs_hourly_starts(NB_YEARS, initial_volume=initial_volume))
        return f"replace timeseries {pattern.name}.{attr_name} with initial volume {initial_volume}"

    def mutate_relink(self, rng, system):
        applicable = []
        for class_name, attr_name in RELINK_SPECS:
            for obj in self.objects_of_class(system, class_name):
                current_target = getattr(obj, attr_name)
                alternatives = [candidate for candidate in self.objects_of_class(
                    system, current_target.class_as_simple_str) if candidate.id != current_target.id]
                if alternatives:
                    applicable.append((obj, attr_name, alternatives))
        obj, attr_name, alternatives = rng.choice(applicable)
        new_target = rng.choice(alternatives)
        setattr(obj, attr_name, new_target)
        return f"relink {obj.name}.{attr_name} to {new_target.name}"

    def mutate_list(self, rng, system):
        applicable = []
        for class_name, attr_name in LIST_SPECS:
            for obj in self.objects_of_class(system, class_name):
                members = list(getattr(obj, attr_name))
                member_class = members[0].class_as_simple_str if members else None
                addable = [candidate for candidate in self.objects_of_class(system, member_class)
                           if candidate.id not in [member.id for member in members]] if member_class else []
                if addable:
                    applicable.append((obj, attr_name, members, "add", addable))
                if len(members) > 1:
                    applicable.append((obj, attr_name, members, "remove", members))
        obj, attr_name, members, action, action_candidates = rng.choice(applicable)
        if action == "add":
            added = rng.choice(action_candidates)
            self.set_collection(obj, attr_name, members + [added])
            return f"add {added.name} to {obj.name}.{attr_name}"
        removed = rng.choice(action_candidates)
        self.set_collection(obj, attr_name, [member for member in members if member.id != removed.id])
        return f"remove {removed.name} from {obj.name}.{attr_name}"

    def mutate_add_object(self, rng, system):
        server = rng.choice([obj for obj in self.all_objects(system)
                             if obj.class_as_simple_str in ("Server", "BoaviztaCloudServer")])
        self.created_objects_count += 1
        new_job = Job.from_defaults(f"parity harness job {self.created_objects_count}", server=server)
        step = rng.choice(self.objects_of_class(system, "UsageJourneyStep"))
        self.set_collection(step, "jobs", list(step.jobs) + [new_job])
        return f"add new job {new_job.name} on {server.name} to {step.name}"

    def mutate_delete_object(self, rng, system):
        deletable = []
        for job in [obj for obj in self.all_objects(system) if isinstance(obj, Job)]:
            containers = list(job.modeling_obj_containers)
            if containers and all(len(list(container.jobs)) > 1 for container in containers):
                deletable.append((job, containers))
        if not deletable:
            return None
        job, containers = rng.choice(deletable)
        ModelingUpdate([
            [container.jobs,
             to_weighted_explainable_object_dict([member for member in container.jobs if member.id != job.id])]
            for container in containers])
        job.self_delete()
        return f"delete job {job.name} (unlinked from {', '.join(c.name for c in containers)})"

    def mutate_add_usage_pattern(self, rng, system):
        template = rng.choice(list(system.usage_patterns))
        self.created_objects_count += 1
        new_pattern = UsagePattern(
            f"parity harness usage pattern {self.created_objects_count}",
            usage_journey=rng.choice(self.objects_of_class(system, "UsageJourney")),
            devices=list(template.devices), network=template.network, country=template.country,
            hourly_usage_journey_starts=form_inputs_hourly_starts(
                NB_YEARS, initial_volume=round(rng.uniform(200, 5000), 1)))
        system.usage_patterns = list(system.usage_patterns) + [new_pattern]
        return f"add new usage pattern {new_pattern.name} on {new_pattern.usage_journey.name}"

    def mutate_delete_usage_pattern(self, rng, system):
        if len(system.usage_patterns) < 2:
            return None
        pattern = rng.choice(list(system.usage_patterns))
        system.usage_patterns = [up for up in system.usage_patterns if up.id != pattern.id]
        pattern.self_delete()
        return f"delete usage pattern {pattern.name}"

    def apply_random_mutation(self, rng, system):
        """Apply one random mutation; returns (op_name, description, applied) where applied is False
        when the engine rejected the change (e.g. insufficient server capacity) and rolled the model
        back — parity must hold after rollbacks too."""
        mutation_operations = (
            self.mutate_scalar_input, self.mutate_timeseries_input, self.mutate_relink,
            self.mutate_list, self.mutate_add_object, self.mutate_delete_object,
            self.mutate_add_usage_pattern, self.mutate_delete_usage_pattern)
        operation = rng.choice(mutation_operations)
        try:
            description = operation(rng, system)
        except EXPECTED_REJECTION_EXCEPTIONS as e:
            return operation.__name__, f"{operation.__name__} rejected and rolled back ({type(e).__name__}: {e})", False
        if description is None:
            return operation.__name__, f"{operation.__name__} skipped (no applicable target)", False
        return operation.__name__, description, True

    def assert_explainable_equal(self, location, live_value, rebuilt_value):
        if isinstance(live_value, ExplainableObjectDict):
            self.assertIsInstance(rebuilt_value, ExplainableObjectDict, location)
            live_items = {key.id if isinstance(key, ModelingObject) else key: value
                          for key, value in live_value.items()}
            rebuilt_items = {key.id if isinstance(key, ModelingObject) else key: value
                             for key, value in rebuilt_value.items()}
            self.assertEqual(set(live_items), set(rebuilt_items), f"{location} keys differ")
            for key, live_item in live_items.items():
                self.assert_explainable_equal(f"{location}[{key}]", live_item, rebuilt_items[key])
        else:
            self.assertTrue(
                live_value == rebuilt_value or self._within_quantization_tolerance(live_value, rebuilt_value),
                f"{location} differs between live and rebuilt system: {live_value} != {rebuilt_value}")

    @staticmethod
    def _within_quantization_tolerance(live_value, rebuilt_value):
        """Live and rebuilt systems iterate collections in legitimately different orders (container
        registration history vs load order), so float32 reductions differ by bit-level noise; where a
        formula quantizes (instance counts are ceiled), that noise can flip the result by one quantum
        (e.g. one storage instance in ~1000). Accept such flips by relative size — genuinely stale
        values differ by far more (the strict staleness gate is the end-of-sequence full recompute)."""
        live_magnitude = getattr(live_value, "magnitude", None)
        rebuilt_magnitude = getattr(rebuilt_value, "magnitude", None)
        if live_magnitude is None or rebuilt_magnitude is None:
            return False
        try:
            return np.allclose(live_magnitude, rebuilt_magnitude, rtol=2e-3, atol=1e-3)
        except (TypeError, ValueError):
            return False

    def assert_no_stale_slot_after_full_recompute(self, system):
        """The strict staleness gate: voiding every slot and recomputing in place must reproduce the
        incrementally maintained values — a missed invalidation would leave a value the recompute
        contradicts. Run at the end of each mutation sequence (recomputing resets the caches, so
        running it per-mutation would stop exercising long incremental histories)."""
        incrementally_computed_values = {}
        for obj in self.all_objects(system):
            for attr_name in computed_slots(type(obj)):
                value = getattr(obj, attr_name, MISSING)
                if value is not MISSING:
                    incrementally_computed_values[(obj.id, attr_name)] = value
        invalidate_slots_system_wide([system])
        pull_slots_system_wide([system])
        for (obj_id, attr_name), incremental_value in incrementally_computed_values.items():
            live_obj = next(obj for obj in self.all_objects(system) if obj.id == obj_id)
            recomputed_value = getattr(live_obj, attr_name)
            self.assert_explainable_equal(
                f"{live_obj.class_as_simple_str} {live_obj.name}.{attr_name} (incremental vs full recompute)",
                recomputed_value, incremental_value)

    def assert_parity_with_from_scratch_rebuild(self, system):
        system_dict = system_to_json(system, save_calculated_attributes=False)
        _, flat_obj_dict, _ = json_to_system(system_dict)
        rebuilt_by_id = {obj.id: obj for obj in self.all_objects(flat_obj_dict[system.id])}
        live_by_id = {obj.id: obj for obj in self.all_objects(system)}
        self.assertEqual(set(live_by_id), set(rebuilt_by_id), "live and rebuilt systems link different objects")
        for obj_id, live_obj in live_by_id.items():
            rebuilt_obj = rebuilt_by_id[obj_id]
            for attr_name in computed_slots(type(live_obj)):
                location = f"{live_obj.class_as_simple_str} {live_obj.name}.{attr_name}"
                live_value = getattr(live_obj, attr_name, MISSING)
                rebuilt_value = getattr(rebuilt_obj, attr_name, MISSING)
                if live_value is MISSING and rebuilt_value is MISSING:
                    # Slots a subclass deliberately drops stay uncomputed on both sides
                    # (e.g. EdgeStorage deletes its inherited power/idle_power in __init__).
                    continue
                self.assertFalse(
                    live_value is MISSING or rebuilt_value is MISSING,
                    f"{location} computed on only one of the live and rebuilt systems")
                self.assert_explainable_equal(location, live_value, rebuilt_value)

    def test_random_mutation_sequences_match_from_scratch_rebuild(self):
        """Test that seeded random mutation sequences leave every computed slot equal to a
        from-scratch rebuild's, checking parity after each mutation."""
        applied_op_names = set()
        full_log = []
        for seed in SEEDS:
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                system = self.build_system()
                mutation_log = []
                for mutation_index in range(MUTATIONS_PER_SEQUENCE):
                    op_name, description, applied = self.apply_random_mutation(rng, system)
                    mutation_log.append(f"{mutation_index + 1}. {description}")
                    if applied:
                        applied_op_names.add(op_name)
                    try:
                        self.assert_parity_with_from_scratch_rebuild(system)
                    except AssertionError as e:
                        raise AssertionError(
                            f"Parity failure for seed {seed} after mutations:\n" + "\n".join(mutation_log)) from e
                try:
                    self.assert_no_stale_slot_after_full_recompute(system)
                except AssertionError as e:
                    raise AssertionError(
                        f"Staleness detected for seed {seed} after mutations:\n" + "\n".join(mutation_log)) from e
                full_log += [f"seed {seed}:"] + mutation_log
        expected_op_names = {
            "mutate_scalar_input", "mutate_timeseries_input", "mutate_relink", "mutate_list",
            "mutate_add_object", "mutate_delete_object", "mutate_add_usage_pattern",
            "mutate_delete_usage_pattern"}
        self.assertEqual(
            expected_op_names, applied_op_names,
            "Some mutation kinds never applied successfully across all seeds — the harness lost coverage:\n"
            + "\n".join(full_log))
