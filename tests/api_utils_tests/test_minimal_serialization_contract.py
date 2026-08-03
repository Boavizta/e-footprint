"""Tests of the minimal persistence contract and version-aware loading.

The canonical format stores inputs, serialize-flagged slot values (system total, impact sources'
footprint pairs, the impact-repartition matrix and edge-device breakdown summaries) and the
values-free calculation graph. Loading attaches stored values as trusted caches only on an exact
version match; any mismatch demotes them to an in-memory baseline and recomputes on read.
"""
import json
from unittest import TestCase
from unittest.mock import patch

import efootprint
from efootprint.abstract_modeling_classes.reactive_core import ReactiveSlot, computed_slots, serialized_slots
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system, upgrade_system_dict_to_current_version
from efootprint.api_utils.system_to_json import materialize_serialized_state, system_to_json
from efootprint.api_utils.version_upgrade_handlers import upgrade_version_22_to_23
from efootprint.constants.units import u
from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass


class ComputeCounter:
    """Patches ReactiveSlot._compute to record the name of every slot computed while active."""

    def __init__(self):
        self.computed_slot_names = []

    def __enter__(self):
        original_compute = ReactiveSlot._compute

        def counting_compute(slot):
            self.computed_slot_names.append(slot.name)
            return original_compute(slot)

        self._patcher = patch.object(ReactiveSlot, "_compute", counting_compute)
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._patcher.stop()


class TestMinimalSerializationContract(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system, cls.start_date = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
        # Materialize the stored output roots explicitly, like a session after its first footprint and
        # Sankey reads. Saving only peeks: it must not turn persistence into an implicit computation trigger.
        cls.system.total_footprint
        cls.system.impact_repartition_matrix
        cls.canonical_dict = system_to_json(cls.system)

    def load_canonical(self):
        _, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(self.canonical_dict)))
        return flat_obj_dict[self.system.id]

    def test_trusted_load_attaches_stored_values_with_zero_compute(self):
        """Test that loading a same-version canonical file performs no computation and leaves the
        serialize-flagged slots cached with the stored values."""
        with ComputeCounter() as counter:
            loaded_system = self.load_canonical()

        self.assertEqual([], counter.computed_slot_names)
        self.assertEqual(self.system.total_footprint, loaded_system.total_footprint)
        self.assertEqual(self.system.impact_repartition_matrix, loaded_system.impact_repartition_matrix)
        self.assertEqual([], counter.computed_slot_names)
        for obj in loaded_system.all_linked_objects:
            for attr_name, descriptor in serialized_slots(obj.efootprint_class).items():
                self.assertIsNotNone(
                    descriptor.peek(obj), f"{obj.name}.{attr_name} was not attached from the stored file")

    def test_canonical_round_trip_is_identity(self):
        """Test that loading a canonical file and re-serializing it reproduces the same dict —
        stored values, calculation graph and formulas included."""
        loaded_system = self.load_canonical()
        # json round trip normalizes tuples (formula tuples serialize as JSON arrays) before comparing.
        self.assertEqual(
            json.loads(json.dumps(self.canonical_dict)), json.loads(json.dumps(system_to_json(loaded_system))))

    def test_inputs_only_save_recomputes_on_read_to_same_values(self):
        """Test that a file saved without computed state loads valueless and recomputes to the same
        totals on read."""
        inputs_only_dict = system_to_json(self.system, save_computed_state=False)
        self.assertNotIn("calculation_graph", inputs_only_dict)
        _, flat_obj_dict, _ = json_to_system(inputs_only_dict)
        loaded_system = flat_obj_dict[self.system.id]

        self.assertIsNone(computed_slots(type(loaded_system))["total_footprint"].peek(loaded_system))
        self.assertEqual(self.system.total_footprint, loaded_system.total_footprint)

    def test_materialize_serialized_state_produces_a_complete_snapshot(self):
        """Test explicit snapshot preparation fills every serialize-flagged slot before the passive
        serializer captures their values and dependency topology."""
        fresh_system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
        objects = [fresh_system] + fresh_system.all_linked_objects

        materialize_serialized_state(fresh_system)
        snapshot = system_to_json(fresh_system)

        self.assertIn("calculation_graph", snapshot)
        self.assertIn([fresh_system.id, "total_footprint", None], snapshot["calculation_graph"]["nodes"])
        self.assertTrue(snapshot["calculation_graph"]["edges"])
        for obj in objects:
            for attr_name, descriptor in serialized_slots(obj.efootprint_class).items():
                self.assertIsNotNone(descriptor.peek(obj), f"{obj.name}.{attr_name} was not materialized")
                self.assertIn(attr_name, snapshot[obj.class_as_simple_str][obj.id])

    def test_system_to_json_remains_peek_only(self):
        """Test ordinary serialization does not materialize serialize-flagged slots."""
        fresh_system, _ = IntegrationTestSimpleSystemBaseClass.generate_simple_system()
        total_descriptor = serialized_slots(type(fresh_system))["total_footprint"]
        self.assertIsNone(total_descriptor.peek(fresh_system))

        snapshot = system_to_json(fresh_system)

        self.assertIsNone(total_descriptor.peek(fresh_system))
        self.assertNotIn("total_footprint", snapshot["System"][fresh_system.id])

    def test_edit_after_trusted_load_invalidates_through_serialized_graph(self):
        """Test the partial-reload state: editing an input below valueless intermediates voids the
        cached footprints above it through the serialized calculation graph — the total genuinely
        changes even though every intermediate between input and total was valueless at load."""
        loaded_system = self.load_canonical()
        initial_total = loaded_system.total_footprint
        job = next(obj for obj in loaded_system.all_linked_objects if obj.class_as_simple_str == "Job")

        job.data_transferred = SourceValue(2 * job.data_transferred.value)

        self.assertNotEqual(initial_total, loaded_system.total_footprint)

    def test_relationship_change_after_trusted_load_invalidates_through_serialized_graph(self):
        """Test that structural edges survive serialization: a relationship change (dropping a
        device from a usage pattern) invalidates the loaded cached footprints."""
        loaded_system = self.load_canonical()
        initial_total = loaded_system.total_footprint
        usage_pattern = loaded_system.usage_patterns[0]

        usage_pattern.devices = []

        self.assertNotEqual(initial_total, loaded_system.total_footprint)

    def test_on_demand_auditability_after_load(self):
        """Test that after a trusted load, an intermediate value and its formula are available on
        demand by recomputing only its own ancestor cone, not the whole model."""
        loaded_system = self.load_canonical()
        server = next(obj for obj in loaded_system.all_linked_objects if obj.class_as_simple_str == "Server")
        all_computed_slot_count = sum(
            len(computed_slots(obj.efootprint_class)) for obj in [loaded_system] + loaded_system.all_linked_objects)

        with ComputeCounter() as counter:
            hourly_instances = server.nb_of_instances

        self.assertGreater(len(counter.computed_slot_names), 0)
        self.assertLess(len(counter.computed_slot_names), all_computed_slot_count / 2)
        explanation = hourly_instances.explain()
        self.assertIn("=", explanation)

    def test_stored_total_footprint_formula_resolves_to_stored_ancestors(self):
        """Test that the stored total's formula is displayable without recomputation: its direct
        ancestors are the stored per-source footprint pairs, by construction of the serialize set."""
        loaded_system = self.load_canonical()

        with ComputeCounter() as counter:
            explanation = loaded_system.total_footprint.explain()

        self.assertEqual([], counter.computed_slot_names)
        self.assertNotIn("None", explanation)

    def test_sankey_renders_from_stored_data_without_recompute(self):
        """Test that every Sankey combination input (the repartition matrix fold, per-source phase
        footprints, breakdown summaries) is served from stored data on a loaded system."""
        from efootprint.utils.impact_repartition import ImpactRepartitionSankey

        loaded_system = self.load_canonical()
        with ComputeCounter() as counter:
            ImpactRepartitionSankey(loaded_system).build()

        self.assertEqual([], counter.computed_slot_names)

    def test_version_mismatch_demotes_stored_values_and_recomputes_on_read(self):
        """Test that loading a file saved by another library version does not trust its stored
        values: slots stay void, reads recompute, and the stored values are retained as an in-memory
        baseline exposed through the drift-comparison hook."""
        mismatched_dict = json.loads(json.dumps(self.canonical_dict))
        mismatched_dict["efootprint_version"] = f"{efootprint.__version__}-other"
        _, flat_obj_dict, _ = json_to_system(mismatched_dict)
        loaded_system = flat_obj_dict[self.system.id]

        self.assertTrue(loaded_system.has_version_baseline)
        self.assertIsNone(computed_slots(type(loaded_system))["total_footprint"].peek(loaded_system))
        with ComputeCounter() as counter:
            recomputed_total = loaded_system.total_footprint
        self.assertGreater(len(counter.computed_slot_names), 0)
        self.assertEqual(self.system.total_footprint, recomputed_total)

        comparison = loaded_system.compare_to_version_baseline()
        self.assertIn("-other", comparison.system_a.name)
        # Same code recomputed the same inputs: the baseline-vs-recomputed drift is zero.
        self.assertAlmostEqual(0, comparison.total_delta.absolute, places=3)

    def test_trusted_load_carries_no_version_baseline(self):
        """Test that the drift hook is only available after a mismatched load."""
        loaded_system = self.load_canonical()
        self.assertFalse(loaded_system.has_version_baseline)
        with self.assertRaises(ValueError):
            loaded_system.compare_to_version_baseline()

    def test_pre_contract_file_upgrades_to_inputs_only(self):
        """Test the schema migration: a version-22 file carrying legacy stored computed values loads
        with those entries dropped (inputs honored, everything recomputes on read)."""
        old_format_dict = system_to_json(self.system, save_computed_state=False)
        old_format_dict["efootprint_version"] = "22.3.0"
        server_dict = next(iter(old_format_dict["Server"].values()))
        server_dict["energy_footprint"] = {"label": "Energy footprint", "value": 12.0, "unit": "kilogram"}

        upgraded_dict = upgrade_system_dict_to_current_version(json.loads(json.dumps(old_format_dict)))
        self.assertNotIn("energy_footprint", next(iter(upgraded_dict["Server"].values())))

        _, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(old_format_dict)))
        loaded_system = flat_obj_dict[self.system.id]
        self.assertFalse(loaded_system.has_version_baseline)
        self.assertEqual(self.system.total_footprint, loaded_system.total_footprint)

    def test_upgrade_handler_drops_every_stored_computed_entry(self):
        """Test that the 22-to-23 handler strips computed entries for every class in the dict."""
        legacy_dict = json.loads(json.dumps(self.canonical_dict))
        del legacy_dict["calculation_graph"]
        upgraded_dict = upgrade_version_22_to_23(legacy_dict)

        for class_key, class_dict in upgraded_dict.items():
            if class_key in ("efootprint_version", "Sources") or not isinstance(class_dict, dict):
                continue
            for obj_dict in class_dict.values():
                for attr_key in obj_dict:
                    self.assertNotIn(
                        attr_key,
                        computed_slots(type(next(obj for obj in [self.system] + self.system.all_linked_objects
                                                 if obj.id == obj_dict["id"]))),
                        f"{class_key}.{attr_key} survived the upgrade")

    def test_serialize_set_is_pinned(self):
        """Test the serialize-flag set: the system total and repartition matrix, every impact
        source's footprint pair, and the edge-device breakdown summary — nothing else."""
        from efootprint.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
        from efootprint.core.attribution import AttributionSource
        from efootprint.core.hardware.edge.edge_component import EdgeComponent
        from efootprint.core.hardware.edge.edge_device import EdgeDevice
        from efootprint.core.system import System

        for efootprint_class in ALL_EFOOTPRINT_CLASSES:
            serialized_names = set(serialized_slots(efootprint_class))
            if efootprint_class is System:
                self.assertEqual({"total_footprint", "impact_repartition_matrix"}, serialized_names)
            elif issubclass(efootprint_class, AttributionSource):
                expected = {"energy_footprint", "instances_fabrication_footprint"}
                if issubclass(efootprint_class, EdgeDevice):
                    expected.add("footprint_breakdown_summary")
                self.assertEqual(expected, serialized_names, efootprint_class.__name__)
            elif issubclass(efootprint_class, EdgeComponent):
                self.assertEqual(set(), serialized_names, efootprint_class.__name__)


class TestEdgeSystemSerializationContract(TestCase):
    """The simple system carries no edge device: the dict-valued footprint_breakdown_summary
    (a serialize-flagged computed structure holding a plain dict, not explainable values or matrix-style
    list rows) only exists on edge systems, so its persistence is pinned here."""

    @classmethod
    def setUpClass(cls):
        from tests.integration_tests.integration_simple_edge_system_base_class import (
            IntegrationTestSimpleEdgeSystemBaseClass)
        cls.system, _ = IntegrationTestSimpleEdgeSystemBaseClass.generate_simple_edge_system()
        cls.edge_device = next(
            obj for obj in cls.system.all_linked_objects if obj.class_as_simple_str == "EdgeDevice")
        # Materialize footprint outputs and every serialize-flagged computed structure (matrix + summaries),
        # like a session after its first Sankey render.
        cls.system.total_footprint
        from efootprint.abstract_modeling_classes.reactive_core import computed_structures
        for obj in [cls.system] + cls.system.all_linked_objects:
            for structure_name, structure_descriptor in computed_structures(obj.efootprint_class).items():
                if structure_descriptor.serialize:
                    getattr(obj, structure_name)
        cls.live_summary = cls.edge_device.footprint_breakdown_summary
        cls.canonical_dict = system_to_json(cls.system)

    def load_canonical(self):
        _, flat_obj_dict, _ = json_to_system(json.loads(json.dumps(self.canonical_dict)))
        return flat_obj_dict[self.system.id], flat_obj_dict[self.edge_device.id]

    def test_breakdown_summary_round_trips_as_dict(self):
        """Test that the dict-valued breakdown summary serializes with its per-component values and
        attaches unchanged on a trusted load."""
        from efootprint.abstract_modeling_classes.reactive_core import computed_structures

        serialized_summary = self.canonical_dict["EdgeDevice"][self.edge_device.id]["footprint_breakdown_summary"]
        self.assertEqual(json.loads(json.dumps(self.live_summary)), serialized_summary)

        _, loaded_device = self.load_canonical()
        loaded_summary = computed_structures(loaded_device.efootprint_class)["footprint_breakdown_summary"].peek(
            loaded_device)
        self.assertEqual(json.loads(json.dumps(self.live_summary)), loaded_summary)

    def test_canonical_round_trip_is_identity(self):
        """Test that loading an edge-system canonical file and re-serializing reproduces the same
        dict, breakdown summaries included."""
        loaded_system, _ = self.load_canonical()
        self.assertEqual(
            json.loads(json.dumps(self.canonical_dict)), json.loads(json.dumps(system_to_json(loaded_system))))

    def test_sankey_renders_breakdown_from_stored_data_without_recompute(self):
        """Test that a loaded edge session builds its Sankey — per-component breakdown decoration
        included, and non-empty — from stored data only."""
        from efootprint.core.lifecycle_phases import LifeCyclePhases
        from efootprint.utils.impact_repartition import ImpactRepartitionSankey

        loaded_system, loaded_device = self.load_canonical()
        with ComputeCounter() as counter:
            sankey = ImpactRepartitionSankey(loaded_system)
            sankey.build()
            breakdown = sankey._get_footprint_breakdown_by_source(loaded_device, LifeCyclePhases.USAGE)

        self.assertEqual([], counter.computed_slot_names)
        self.assertEqual(len(self.live_summary[LifeCyclePhases.USAGE.value]), len(breakdown))
        self.assertGreater(len(breakdown), 0)
