import math
from functools import lru_cache
from unittest import TestCase
from unittest.mock import patch

from efootprint.constants.units import u
from efootprint.core.attribution import attribution_sources
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.utils.impact_repartition import ImpactRepartitionSankey


class _EmptySystem:
    """Minimal stand-in for a System with no attribution sources, for presentation-only tests."""

    def __init__(self, name="Test system"):
        self.name = name
        self.id = "test_system"
        self.all_linked_objects = []
        self.render_cache = {}


_FIXTURE_NAMES = ("simple", "simple_edge", "complex", "services", "edge_group")


@lru_cache(maxsize=None)
def fixture_system(name):
    if name == "simple":
        from tests.integration_tests.integration_simple_system_base_class import IntegrationTestSimpleSystemBaseClass
        return IntegrationTestSimpleSystemBaseClass.generate_simple_system()[0]
    if name == "simple_edge":
        from tests.integration_tests.integration_simple_edge_system_base_class import (
            IntegrationTestSimpleEdgeSystemBaseClass)
        return IntegrationTestSimpleEdgeSystemBaseClass.generate_simple_edge_system()[0]
    if name == "complex":
        from tests.integration_tests.integration_complex_system_base_class import (
            IntegrationTestComplexSystemBaseClass)
        return IntegrationTestComplexSystemBaseClass.generate_complex_system()[0]
    if name == "services":
        from tests.integration_tests.integration_services_base_class import IntegrationTestServicesBaseClass
        return IntegrationTestServicesBaseClass.generate_system_with_services()[0]
    if name == "edge_group":
        from tests.integration_tests.integration_edge_device_group_base_class import (
            IntegrationEdgeDeviceGroupBaseClass)
        return IntegrationEdgeDeviceGroupBaseClass.generate_edge_device_group_system()[0]
    raise ValueError(name)


def eager_system_total(system, phases=tuple(LifeCyclePhases)):
    from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
    from tests.core.attribution.conservation import eager_phase_footprint

    total = EmptyExplainableObject()
    for source in attribution_sources(system):
        for phase in phases:
            total = total + eager_phase_footprint(source, phase)
    return 0 * u.kg if isinstance(total, EmptyExplainableObject) else total.sum().value


def build_sankey(system, **kwargs):
    kwargs.setdefault("aggregation_threshold_percent", 0)
    sankey = ImpactRepartitionSankey(system, **kwargs)
    sankey.build()
    return sankey


def incoming_and_outgoing_by_node(sankey):
    incoming, outgoing = {}, {}
    for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values):
        incoming[target] = incoming.get(target, 0 * u.kg) + value
        outgoing[source] = outgoing.get(source, 0 * u.kg) + value
    return incoming, outgoing


def node_totals_by_key(sankey):
    return {key: sankey.node_total_values[idx] for key, idx in sankey.node_indices.items()
            if idx not in sankey._spacer_nodes}


class TestImpactRepartitionSankeyConservation(TestCase):
    """Conservation regressions on every fixture model: the renderer is a pure presentation of the
    attribution fold, so per-node link balance and per-column totals are structural and must never drift."""

    def assert_kg_equal(self, expected, actual, msg=None):
        expected_kg = expected.to(u.kg).magnitude
        actual_kg = actual.to(u.kg).magnitude
        scale = max(abs(expected_kg), 1.0)
        self.assertAlmostEqual(0, (expected_kg - actual_kg) / scale, places=4, msg=msg)

    def test_per_node_link_balance_on_every_fixture(self):
        """Test that on every fixture model, Σ incoming == node total at every linked node and
        Σ outgoing == node total at every pass-through (non-leaf, non-breakdown) node."""
        for name in _FIXTURE_NAMES:
            with self.subTest(fixture=name):
                sankey = build_sankey(fixture_system(name))
                incoming, outgoing = incoming_and_outgoing_by_node(sankey)
                terminal_nodes = sankey._leaf_node_indices | sankey._breakdown_node_indices
                for idx in range(len(sankey.node_labels)):
                    if idx in incoming:
                        self.assert_kg_equal(
                            sankey.node_total_values[idx], incoming[idx],
                            msg=f"Σ incoming != total at {sankey.full_node_labels[idx]} ({name})")
                    if idx in outgoing and idx not in terminal_nodes:
                        self.assert_kg_equal(
                            sankey.node_total_values[idx], outgoing[idx],
                            msg=f"Σ outgoing != total at {sankey.full_node_labels[idx]} ({name})")

    def test_column_sums_equal_system_total_on_every_fixture(self):
        """Test that on every fixture model the root total matches the eager system total and every
        container column, the category column and the leaf nodes each sum back to it."""
        for name in _FIXTURE_NAMES:
            with self.subTest(fixture=name):
                system = fixture_system(name)
                sankey = build_sankey(system)
                self.assert_kg_equal(eager_system_total(system), sankey.total_system_value)

                root_idx = sankey.node_indices[("root", "total")]
                self.assert_kg_equal(sankey.total_system_value, sankey.node_total_values[root_idx])

                # Every column strictly between the root and the leaves carries the full total: each flow
                # crosses it either in a real node or in a pure-geometry spacer (a Device atom has no Job
                # node, so its flow crosses the Job column in a spacer — values untouched).
                leaf_columns = {sankey._node_columns[idx] for idx in sankey._leaf_node_indices}
                last_full_column = min(leaf_columns) - 1 if leaf_columns else max(sankey._node_columns.values())
                column_totals = {}
                for idx, column in sankey._node_columns.items():
                    if idx in sankey._breakdown_node_indices:
                        continue
                    column_totals.setdefault(column, 0 * u.kg)
                    column_totals[column] += sankey.node_total_values[idx]
                for column in range(sankey._node_columns[root_idx] + 1, last_full_column + 1):
                    self.assert_kg_equal(
                        sankey.total_system_value, column_totals[column],
                        msg=f"Column {column} doesn't conserve the system total ({name})")

                leaf_total = sum(
                    (sankey.node_total_values[idx] for idx in sankey._leaf_node_indices), start=0 * u.kg)
                self.assert_kg_equal(sankey.total_system_value, leaf_total,
                                     msg=f"Leaf nodes don't conserve the system total ({name})")

    def test_lifecycle_phase_filter_restricts_to_phase_total(self):
        """Test that filtering on the manufacturing phase yields exactly the eager fabrication total."""
        system = fixture_system("simple")
        sankey = build_sankey(system, lifecycle_phase_filter=LifeCyclePhases.MANUFACTURING)
        self.assert_kg_equal(
            eager_system_total(system, phases=(LifeCyclePhases.MANUFACTURING,)), sankey.total_system_value)

    def test_skip_column_preserves_surviving_node_totals_and_links_across(self):
        """Test that skipping the UsageJourney column removes its nodes, keeps every surviving node total
        identical to the full build, and links steps directly under usage patterns."""
        system = fixture_system("simple")
        baseline = build_sankey(system)
        skipped = build_sankey(system, skipped_impact_repartition_classes=[UsageJourney])

        baseline_totals = node_totals_by_key(baseline)
        skipped_totals = node_totals_by_key(skipped)
        journey = system.usage_patterns[0].usage_journey
        self.assertIn((journey.id, "Usage"), baseline_totals)
        self.assertNotIn((journey.id, "Usage"), skipped_totals)
        for key, value in skipped_totals.items():
            self.assert_kg_equal(baseline_totals[key], value, msg=f"Node {key} changed when skipping UsageJourney")

        usage_pattern = system.usage_patterns[0]
        step = list(journey.uj_steps)[0]
        for phase_context in ("Manufacturing", "Usage"):
            up_idx = skipped.node_indices[(usage_pattern.id, phase_context)]
            step_idx = skipped.node_indices[(step.id, phase_context)]
            direct_links = [
                value for source, target, value in zip(
                    skipped.link_sources, skipped.link_targets, skipped.link_values)
                if source == up_idx and target == step_idx]
            self.assertTrue(direct_links, f"No direct UP → step link in {phase_context} when UJ is skipped")

    def test_exclude_source_filters_without_rescaling(self):
        """Test that excluding the Device class drops exactly its footprint from the total and leaves every
        other leaf's total untouched (filter, no rescale)."""
        system = fixture_system("simple")
        device = system.usage_patterns[0].devices[0]
        baseline = build_sankey(system)
        excluded = build_sankey(system, excluded_object_types=["Device"])

        device_total = (device.instances_fabrication_footprint.sum() + device.energy_footprint.sum()).value
        self.assert_kg_equal(baseline.total_system_value - device_total, excluded.total_system_value)

        baseline_totals = node_totals_by_key(baseline)
        excluded_totals = node_totals_by_key(excluded)
        self.assertIn((device.id, "Usage"), baseline_totals)
        self.assertNotIn((device.id, "Usage"), excluded_totals)
        for idx in excluded._leaf_node_indices:
            key = next(k for k, v in excluded.node_indices.items() if v == idx)
            self.assert_kg_equal(
                baseline_totals[key], excluded_totals[key],
                msg=f"Leaf {key} was rescaled by the exclusion")

    def test_aggressive_skip_routes_bare_chain_remainders_to_leaves(self):
        """Test that with only the recurrent-need column visible on the complex (dual-side) fixture, leaf
        totals still conserve the system total: a dual-side server's web atoms have no visible container, so
        their value reaches the leaf as a remainder routed from the phase parent."""
        system = fixture_system("complex")
        skipped = [
            "Country", "UsagePattern", "EdgeUsagePattern", "UsageJourney", "EdgeUsageJourney",
            "EdgeFunction", "UsageJourneyStep", "JobBase", "RecurrentEdgeComponentNeed"]
        sankey = build_sankey(system, skipped_impact_repartition_classes=skipped)

        self.assert_kg_equal(eager_system_total(system), sankey.total_system_value)
        leaf_total = sum((sankey.node_total_values[idx] for idx in sankey._leaf_node_indices), start=0 * u.kg)
        self.assert_kg_equal(sankey.total_system_value, leaf_total,
                             msg="Leaf nodes don't conserve the system total under aggressive column skipping")

    def test_exclude_external_api_drops_exactly_its_server_footprint(self):
        """Test that excluding the ExternalAPI display class filters the paired server class's atoms: the
        total shrinks by exactly the API server's footprint and the API leaf disappears."""
        system = fixture_system("services")
        api_server = next(
            obj for obj in attribution_sources(system)
            if obj.class_as_simple_str == "EcoLogitsGenAIExternalAPIServer")
        baseline = build_sankey(system)
        excluded = build_sankey(system, excluded_object_types=["ExternalAPI"])

        api_total = (api_server.instances_fabrication_footprint.sum() + api_server.energy_footprint.sum()).value
        self.assert_kg_equal(baseline.total_system_value - api_total, excluded.total_system_value)
        self.assertIn((api_server.external_api.id, "Usage"), node_totals_by_key(baseline))
        self.assertNotIn((api_server.external_api.id, "Usage"), node_totals_by_key(excluded))

    def test_exclude_edge_storage_removes_only_breakdown_children(self):
        """Test that excluding EdgeStorage (a breakdown-only component, not an atom source) keeps the system
        total and every surviving node identical and drops only the storage breakdown children."""
        system = fixture_system("simple_edge")
        edge_storage = next(
            obj for obj in system.all_linked_objects if obj.class_as_simple_str == "EdgeStorage")
        baseline = build_sankey(system)
        excluded = build_sankey(system, excluded_object_types=["EdgeStorage"])

        self.assert_kg_equal(baseline.total_system_value, excluded.total_system_value)
        baseline_totals = node_totals_by_key(baseline)
        excluded_totals = node_totals_by_key(excluded)
        self.assertIn((edge_storage.id, "Manufacturing"), baseline_totals)
        self.assertNotIn((edge_storage.id, "Manufacturing"), excluded_totals)
        for key, value in excluded_totals.items():
            self.assert_kg_equal(baseline_totals[key], value, msg=f"Node {key} changed when excluding EdgeStorage")

    def test_unknown_class_name_in_skip_or_exclude_raises(self):
        """Test that a misspelled class name in skipped or excluded classes raises instead of silently
        rendering the full unfiltered Sankey."""
        system = fixture_system("simple")
        for kwargs in ({"skipped_impact_repartition_classes": ["Sever"]}, {"excluded_object_types": ["Devcie"]}):
            with self.subTest(**kwargs), self.assertRaises(ValueError) as context:
                build_sankey(system, **kwargs)
            self.assertIn("Unknown e-footprint class name(s)", str(context.exception))

    def test_external_api_server_sources_are_normalized_to_external_api(self):
        """Test that ExternalAPIServer atoms display as their ExternalAPI with its category node."""
        system = fixture_system("services")
        sankey = build_sankey(system)
        api_server = next(
            obj for obj in attribution_sources(system)
            if obj.class_as_simple_str == "EcoLogitsGenAIExternalAPIServer")
        self.assertIn((api_server.external_api.id, "Usage"), sankey.node_indices)
        self.assertNotIn((api_server.id, "Usage"), sankey.node_indices)
        self.assertIn(("ExternalAPIs", "Usage"), sankey.node_indices)

    def test_edge_device_breakdown_decoration_sums_to_device_totals(self):
        """Test that EdgeDevice leaf nodes carry their EdgeComponent breakdown children and the children sum
        to the device's leaf total per phase (full-coverage fixture)."""
        system = fixture_system("simple_edge")
        sankey = build_sankey(system)
        self.assertTrue(sankey._breakdown_node_indices)
        incoming, _ = incoming_and_outgoing_by_node(sankey)
        edge_device = next(
            obj for obj in attribution_sources(system) if obj.class_as_simple_str == "EdgeComputer")
        for phase in LifeCyclePhases:
            device_idx = sankey.node_indices[(edge_device.id, phase.value)]
            breakdown_total = sum(
                (value for source, target, value in zip(
                    sankey.link_sources, sankey.link_targets, sankey.link_values)
                 if source == device_idx and target in sankey._breakdown_node_indices), start=0 * u.kg)
            self.assertGreater(breakdown_total.magnitude, 0)
            self.assertAlmostEqual(
                1, (breakdown_total / sankey.node_total_values[device_idx]).to(u.dimensionless).magnitude,
                places=4)

    def test_skipped_source_classes_keep_totals_and_drop_leaves(self):
        """Test that skipping every hardware class hides the leaf and category columns but conserves the
        system total and the container node totals (skip = hide, never rescale)."""
        system = fixture_system("simple")
        hardware = ["Device", "EdgeDevice", "Network", "ExternalAPI", "ServerBase", "ExternalAPIServer", "Storage"]
        baseline = build_sankey(system)
        skipped = build_sankey(
            system, skipped_impact_repartition_classes=hardware, skip_object_footprint_split=True)

        self.assert_kg_equal(baseline.total_system_value, skipped.total_system_value)
        self.assertEqual(set(), skipped._leaf_node_indices)
        baseline_totals = node_totals_by_key(baseline)
        for key, value in node_totals_by_key(skipped).items():
            self.assert_kg_equal(baseline_totals[key], value, msg=f"Node {key} changed when skipping hardware")

    def test_interface_smoke_with_exact_sankey_views_kwargs(self):
        """Test the renderer instantiates and builds with the exact kwargs e-footprint-interface's
        sankey_views.py passes (default chips: columns 2, 5, 6 skipped as class-name strings), and exposes
        every attribute the view reads."""
        system = fixture_system("simple_edge")
        skipped_classes = [
            "UsagePattern", "EdgeUsagePattern", "RecurrentEdgeDeviceNeed", "RecurrentServerNeed",
            "JobBase", "RecurrentEdgeComponentNeed"]
        sankey = ImpactRepartitionSankey(
            system,
            aggregation_threshold_percent=1.0,
            node_label_max_length=15,
            skipped_impact_repartition_classes=skipped_classes,
            skip_phase_footprint_split=False,
            skip_object_category_footprint_split=False,
            skip_object_footprint_split=False,
            excluded_object_types=None,
            lifecycle_phase_filter=None,
            display_column_information=False,
        )
        sankey.build()

        node_colors = sankey._compute_node_colors()
        self.assertEqual(len(node_colors), len(sankey.node_labels))
        self.assertEqual(len(sankey.node_labels), len(sankey.full_node_labels))
        self.assertEqual(len(sankey.link_sources), len(sankey.link_values))
        for collection in (sankey._node_columns, sankey._spacer_nodes, sankey._category_node_indices,
                           sankey._leaf_node_indices, sankey._breakdown_node_indices,
                           sankey.aggregated_node_members):
            self.assertIsNotNone(collection)
        self.assertIsInstance(sankey.format_value_in_root_unit(sankey.total_system_value), str)
        self.assertIsInstance(sankey.get_percentage_of_total(sankey.total_system_value), float)
        self.assertIsInstance(sankey.get_column_information(), list)
        self.assertIsInstance(sankey.get_column_header_x_shift_px(), int)
        self.assertIsNotNone(sankey.get_root_display_unit())
        self.assert_kg_equal(eager_system_total(system), sankey.total_system_value)


class TestImpactRepartitionSankeyPresentation(TestCase):
    """Presentation mechanics (aggregation, labels, columns, spacers, figure assembly) on manually-built
    graphs — independent of the attribution data layer."""

    @staticmethod
    def _kg(value):
        return value * u.kg

    @staticmethod
    def _tonne(value):
        return value * u.tonne

    @staticmethod
    def _make_object(name):
        cls = type(name.replace(" ", ""), (), {})
        obj = cls()
        obj.name = name
        obj.id = name.lower().replace(" ", "_")
        obj.canonical_class = cls
        return obj

    def test_all_canonical_classes_are_in_sankey_columns_or_breakdown_only(self):
        from efootprint.all_classes_in_order import (
            ALL_CANONICAL_CLASSES_DICT, SANKEY_COLUMNS, SANKEY_BREAKDOWN_ONLY_CLASSES)

        excluded_classes = ["System", "Service", "EdgeDeviceGroup"]
        canonical_classes_dict_without_excluded = {
            name: cls for name, cls in ALL_CANONICAL_CLASSES_DICT.items() if name not in excluded_classes}

        known_classes = set(SANKEY_BREAKDOWN_ONLY_CLASSES)
        for column_list in SANKEY_COLUMNS:
            known_classes.update(column_list)

        missing_classes = set(canonical_classes_dict_without_excluded.values()) - known_classes
        self.assertFalse(missing_classes,
                         f"The following canonical classes are missing from sankey columns: {missing_classes}")

    def _build_sankey(self, aggregation_threshold_percent):
        sankey = ImpactRepartitionSankey(
            _EmptySystem(), aggregation_threshold_percent=aggregation_threshold_percent)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_idx = sankey._add_node("Parent", ("parent", "energy"), color_key="parent", obj=self._make_object("Parent"))
        small_a_idx = sankey._add_node("Small A", ("small_a", "energy"), color_key="small_a", obj=self._make_object("Small A"))
        small_b_idx = sankey._add_node("Small B", ("small_b", "energy"), color_key="small_b", obj=self._make_object("Small B"))
        child_big_idx = sankey._add_node("Child Big", ("child_big", "energy"), color_key="child_big", obj=self._make_object("Child Big"))
        child_small_a_idx = sankey._add_node(
            "Child Small A", ("child_small_a", "energy"), color_key="child_small_a", obj=self._make_object("Child Small A"))
        child_small_b_idx = sankey._add_node(
            "Child Small B", ("child_small_b", "energy"), color_key="child_small_b", obj=self._make_object("Child Small B"))

        sankey._total_system_value = self._kg(1000)
        sankey.node_total_values[total_idx] = self._kg(1000)
        sankey._node_columns = {
            total_idx: 1, parent_idx: 2, small_a_idx: 2, small_b_idx: 2,
            child_big_idx: 3, child_small_a_idx: 3, child_small_b_idx: 3,
        }
        sankey._add_link(total_idx, parent_idx, self._tonne(0.72))
        sankey._add_link(total_idx, small_a_idx, self._tonne(0.10))
        sankey._add_link(total_idx, small_b_idx, self._tonne(0.08))
        sankey._add_link(parent_idx, child_big_idx, self._tonne(0.54))
        sankey._add_link(parent_idx, child_small_a_idx, self._tonne(0.10))
        sankey._add_link(parent_idx, child_small_b_idx, self._tonne(0.08))
        return sankey

    def test_aggregate_small_nodes_by_column_groups_only_same_column(self):
        """Test small nodes are aggregated per column and listed in hover text."""
        sankey = self._build_sankey(aggregation_threshold_percent=15)

        sankey._aggregate_small_nodes_by_column()
        hover_labels = sankey._build_hover_labels()

        self.assertEqual(2, sankey.node_labels.count("Other (2)"))
        self.assertEqual(2, len(sankey.aggregated_node_members))
        links_to_aggregates = sorted(
            round(value.to(u.tonne).magnitude, 2)
            for target, value in zip(sankey.link_targets, sankey.link_values)
            if target in sankey.aggregated_node_members)
        self.assertEqual([0.18, 0.18], links_to_aggregates)
        aggregated_hover = [label for label in hover_labels if label.startswith("Other (2)<br>")]
        self.assertEqual(2, len(aggregated_hover))
        self.assertTrue(any("Small A" in label and "Small B" in label for label in aggregated_hover))
        self.assertTrue(any("Child Small A" in label and "Child Small B" in label for label in aggregated_hover))

    def test_aggregate_small_nodes_by_column_respects_threshold(self):
        """Test aggregation is skipped when nodes are above the configured threshold."""
        sankey = self._build_sankey(aggregation_threshold_percent=5)

        sankey._aggregate_small_nodes_by_column()

        self.assertNotIn("Other (2)", sankey.node_labels)
        self.assertEqual({}, sankey.aggregated_node_members)

    def test_aggregate_small_nodes_by_column_merges_across_parents(self):
        """Test small nodes in the same column are aggregated together regardless of parent."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=15)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_a_idx = sankey._add_node("Parent A", ("parent_a", "energy"), obj=self._make_object("Parent A"))
        parent_b_idx = sankey._add_node("Parent B", ("parent_b", "energy"), obj=self._make_object("Parent B"))
        small_a1_idx = sankey._add_node("Small A1", ("small_a1", "energy"), obj=self._make_object("Small A1"))
        small_a2_idx = sankey._add_node("Small A2", ("small_a2", "energy"), obj=self._make_object("Small A2"))
        small_b1_idx = sankey._add_node("Small B1", ("small_b1", "energy"), obj=self._make_object("Small B1"))
        small_b2_idx = sankey._add_node("Small B2", ("small_b2", "energy"), obj=self._make_object("Small B2"))

        sankey._total_system_value = self._kg(1000)
        sankey.node_total_values[total_idx] = self._kg(1000)
        sankey._node_columns = {
            total_idx: 1, parent_a_idx: 2, parent_b_idx: 2,
            small_a1_idx: 3, small_a2_idx: 3, small_b1_idx: 3, small_b2_idx: 3,
        }
        sankey._add_link(total_idx, parent_a_idx, self._tonne(0.36))
        sankey._add_link(total_idx, parent_b_idx, self._tonne(0.36))
        sankey._add_link(parent_a_idx, small_a1_idx, self._tonne(0.10))
        sankey._add_link(parent_a_idx, small_a2_idx, self._tonne(0.08))
        sankey._add_link(parent_b_idx, small_b1_idx, self._tonne(0.10))
        sankey._add_link(parent_b_idx, small_b2_idx, self._tonne(0.08))

        sankey._aggregate_small_nodes_by_column()
        hover_labels = [label for label in sankey._build_hover_labels() if label.startswith("Other (4)<br>")]

        self.assertEqual(1, sankey.node_labels.count("Other (4)"))
        self.assertEqual(1, len(sankey.aggregated_node_members))
        self.assertEqual(1, len(hover_labels))
        self.assertTrue(any(
            "Small A1" in label and "Small A2" in label and "Small B1" in label and "Small B2" in label
            for label in hover_labels))

    def test_aggregate_small_nodes_by_column_recomputes_children_after_parent_aggregation(self):
        """Test child columns are re-aggregated after their parents collapse into an aggregated node."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=15)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_a_idx = sankey._add_node("Parent A", ("parent_a", "energy"), obj=self._make_object("Parent A"))
        parent_b_idx = sankey._add_node("Parent B", ("parent_b", "energy"), obj=self._make_object("Parent B"))
        child_a_idx = sankey._add_node("Child A", ("child_a", "energy"), obj=self._make_object("Child A"))
        child_b_idx = sankey._add_node("Child B", ("child_b", "energy"), obj=self._make_object("Child B"))

        sankey._total_system_value = self._kg(1000)
        sankey.node_total_values[total_idx] = self._kg(1000)
        sankey._node_columns = {
            total_idx: 1, parent_a_idx: 2, parent_b_idx: 2, child_a_idx: 3, child_b_idx: 3,
        }
        sankey._add_link(total_idx, parent_a_idx, self._tonne(0.08))
        sankey._add_link(total_idx, parent_b_idx, self._tonne(0.07))
        sankey._add_link(parent_a_idx, child_a_idx, self._tonne(0.08))
        sankey._add_link(parent_b_idx, child_b_idx, self._tonne(0.07))

        sankey._aggregate_small_nodes_by_column()
        hover_labels = [label for label in sankey._build_hover_labels() if label.startswith("Other (2)<br>")]

        self.assertEqual(2, sankey.node_labels.count("Other (2)"))
        self.assertEqual(2, len(hover_labels))
        self.assertTrue(any("Parent A" in label and "Parent B" in label for label in hover_labels))
        self.assertTrue(any("Child A" in label and "Child B" in label for label in hover_labels))

    def test_aggregate_small_nodes_preserves_root_node_totals_when_aggregated(self):
        """Test that root nodes (no incoming links, total set directly) have their totals preserved in aggregates."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=15)

        root_a_idx = sankey._add_node("Root A", ("root_a", "energy"), obj=self._make_object("Root A"))
        root_b_idx = sankey._add_node("Root B", ("root_b", "energy"), obj=self._make_object("Root B"))
        child_idx = sankey._add_node("Child", ("child", "energy"), obj=self._make_object("Child"))

        sankey._total_system_value = self._kg(1000)
        sankey.node_total_values[root_a_idx] = self._kg(80)  # Set directly, no incoming link
        sankey.node_total_values[root_b_idx] = self._kg(70)  # Set directly, no incoming link
        sankey._node_columns = {root_a_idx: 1, root_b_idx: 1, child_idx: 2}
        sankey._add_link(root_a_idx, child_idx, self._tonne(0.08))
        sankey._add_link(root_b_idx, child_idx, self._tonne(0.07))

        sankey._aggregate_small_nodes_by_column()

        aggregate_idx = next(idx for idx in sankey.aggregated_node_members)
        self.assertEqual(self._kg(150), sankey.node_total_values[aggregate_idx])

    def test_aggregate_small_nodes_preserves_category_leaf_and_breakdown_markers_for_remaining_nodes(self):
        """Test aggregation keeps node-type markers for nodes that are not aggregated away."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=10)

        root_idx = sankey._add_node("Root", ("root", "total"))
        category_big_idx = sankey._add_node("Devices usage", ("Devices", "usage"))
        category_small_a_idx = sankey._add_node("Servers usage", ("Servers", "usage"))
        category_small_b_idx = sankey._add_node("Network usage", ("Network", "usage"))
        leaf_big_idx = sankey._add_node("Device A", ("device_a", "usage"))
        leaf_small_a_idx = sankey._add_node("Server A", ("server_a", "usage"))
        leaf_small_b_idx = sankey._add_node("Network A", ("network_a", "usage"))
        breakdown_big_idx = sankey._add_node("Component A", ("component_a", "usage"))
        breakdown_small_a_idx = sankey._add_node("Component B", ("component_b", "usage"))
        breakdown_small_b_idx = sankey._add_node("Component C", ("component_c", "usage"))

        sankey._total_system_value = self._kg(100)
        sankey.node_total_values[root_idx] = self._kg(100)
        sankey._node_columns = {
            root_idx: 1,
            category_big_idx: 2,
            category_small_a_idx: 2,
            category_small_b_idx: 2,
            leaf_big_idx: 3,
            leaf_small_a_idx: 3,
            leaf_small_b_idx: 3,
            breakdown_big_idx: 4,
            breakdown_small_a_idx: 4,
            breakdown_small_b_idx: 4,
        }
        sankey._category_node_indices = {category_big_idx, category_small_a_idx, category_small_b_idx}
        sankey._leaf_node_indices = {leaf_big_idx, leaf_small_a_idx, leaf_small_b_idx}
        sankey._breakdown_node_indices = {breakdown_big_idx, breakdown_small_a_idx, breakdown_small_b_idx}

        for source, target, value in [
            (root_idx, category_big_idx, 0.9),
            (root_idx, category_small_a_idx, 0.05),
            (root_idx, category_small_b_idx, 0.05),
            (category_big_idx, leaf_big_idx, 0.9),
            (category_small_a_idx, leaf_small_a_idx, 0.05),
            (category_small_b_idx, leaf_small_b_idx, 0.05),
            (leaf_big_idx, breakdown_big_idx, 0.9),
            (leaf_small_a_idx, breakdown_small_a_idx, 0.05),
            (leaf_small_b_idx, breakdown_small_b_idx, 0.05),
        ]:
            sankey._add_link(source, target, self._tonne(value))

        sankey._aggregate_small_nodes_by_column()

        self.assertIn("Devices usage", sankey.node_labels)
        self.assertIn("Device A", sankey.node_labels)
        self.assertIn("Component A", sankey.node_labels)
        devices_idx = sankey.node_labels.index("Devices usage")
        leaf_idx = sankey.node_labels.index("Device A")
        breakdown_idx = sankey.node_labels.index("Component A")
        self.assertIn(devices_idx, sankey._category_node_indices)
        self.assertIn(leaf_idx, sankey._leaf_node_indices)
        self.assertIn(breakdown_idx, sankey._breakdown_node_indices)

    def test_is_positive_raises_on_nan_to_surface_upstream_attribution_bugs(self):
        """Test _is_positive raises on NaN so attribution bugs don't get silently filtered."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0)
        with self.assertRaises(ValueError) as ctx:
            sankey._is_positive(self._kg(float("nan")))
        self.assertIn("NaN", str(ctx.exception))
        # Positive and non-positive scalars still work normally.
        self.assertTrue(sankey._is_positive(self._kg(1.0)))
        self.assertFalse(sankey._is_positive(self._kg(0.0)))
        self.assertFalse(math.isnan(self._kg(1.0).magnitude))

    def test_node_labels_are_truncated_but_hover_keeps_full_name(self):
        """Test label truncation preserves full name in hover."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0, node_label_max_length=13)

        node_idx = sankey._add_node("12345678901234", ("long_name", "energy"))
        sankey._total_system_value = self._kg(1)
        sankey.node_total_values[node_idx] = self._kg(1)

        self.assertEqual("1234567890123...", sankey.node_labels[node_idx])
        self.assertEqual("12345678901234", sankey.full_node_labels[node_idx])
        self.assertTrue(sankey._build_hover_labels()[node_idx].startswith("12345678901234<br>"))

    def test_node_label_max_length_is_configurable(self):
        """Test custom label max length."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0, node_label_max_length=5)

        node_idx = sankey._add_node("123456", ("custom_length", "energy"))

        self.assertEqual("12345...", sankey.node_labels[node_idx])
        self.assertEqual("123456", sankey.full_node_labels[node_idx])

    def test_get_column_metadata_returns_unique_class_names_and_positions(self):
        """Test column metadata from explicitly assigned columns on a built fixture."""
        sankey = build_sankey(fixture_system("simple"))
        metadata = sankey.get_column_metadata()

        column_indices = [m["column_index"] for m in metadata]
        self.assertEqual(sorted(set(column_indices)), column_indices)
        leaf_column_classes = next(
            m["class_names"] for m in metadata
            if m["column_index"] == max(column_indices))
        self.assertIn("Device", leaf_column_classes)
        for m in metadata:
            self.assertAlmostEqual(sankey._column_x_left(m["column_index"]), m["x_left"])

    def test_get_column_metadata_includes_aggregated_member_classes(self):
        """Test column metadata includes classes from aggregated nodes."""
        sankey = self._build_sankey(aggregation_threshold_percent=15)
        sankey._built = True
        for node in sankey.node_objects.values():
            node.canonical_class = type(node.name.replace(" ", ""), (), {})
        sankey._aggregate_small_nodes_by_column()

        metadata = sankey.get_column_metadata()
        self.assertEqual([2, 3], [m["column_index"] for m in metadata])
        self.assertEqual(
            [["Parent", "SmallA", "SmallB"], ["ChildBig", "ChildSmallA", "ChildSmallB"]],
            [m["class_names"] for m in metadata])
        self.assertAlmostEqual(sankey._column_x_left(2), metadata[0]["x_left"])
        self.assertAlmostEqual(sankey._column_x_left(3), metadata[1]["x_left"])

    def test_build_link_labels_keeps_visible_endpoints_across_spacer_nodes(self):
        """Test spacer-segmented links keep the original visible source and target in hover labels."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0)

        source_idx = sankey._add_node("Source", ("source", "energy"))
        target_idx = sankey._add_node("Target", ("target", "energy"))
        sankey._total_system_value = self._kg(100)
        sankey.node_total_values[source_idx] = self._kg(100)
        sankey._node_columns = {source_idx: 1, target_idx: 4}
        sankey._add_link(source_idx, target_idx, self._tonne(0.1))

        sankey._insert_spacer_nodes()
        link_labels = sankey._build_link_labels()

        self.assertEqual(3, len(link_labels))
        self.assertEqual(1, len(set(link_labels)))
        self.assertTrue(all(label.startswith("Source → Target<br>") for label in link_labels))
        self.assertTrue(all(label.endswith("CO2eq (100.0%)") for label in link_labels))

    def test_format_value_in_root_unit_rounds_before_rendering(self):
        """Test Sankey string formatting keeps display rounding and trims trailing zeros."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0)
        sankey._total_system_value = self._kg(123456)

        self.assertEqual("123 t", sankey.format_value_in_root_unit(self._kg(123456)))
        self.assertEqual("1.23 t", sankey.format_value_in_root_unit(self._kg(1234.56)))

    def test_get_column_information_distinguishes_manual_and_impact_columns(self):
        """Test column information reports both manual split and impact repartition columns."""
        sankey = build_sankey(fixture_system("simple"), skip_object_category_footprint_split=True)
        col_info = sankey.get_column_information()

        manual_cols = [c for c in col_info if c["column_type"] == "manual_split"]
        impact_cols = [c for c in col_info if c["column_type"] == "impact_repartition"]
        self.assertTrue(len(manual_cols) >= 1)
        self.assertTrue(len(impact_cols) >= 1)
        self.assertIn("Total impact", [c["description"] for c in manual_cols])

    def test_get_column_information_includes_total_impact_for_visible_system_root(self):
        """Test visible root column is exposed as a manual Total impact column."""
        sankey = build_sankey(fixture_system("simple"))

        self.assertIn(
            {"column_index": 1, "column_type": "manual_split", "description": "Total impact", "x_left": 0.006},
            sankey.get_column_information(),
        )

    def test_get_column_information_omits_total_impact_when_system_root_is_skipped(self):
        """Test Total impact column is not exposed when the root system node is skipped."""
        sankey = build_sankey(fixture_system("simple"), skipped_impact_repartition_classes=["System"])

        self.assertNotIn(("root", "total"), sankey.node_indices)
        self.assertNotIn(
            "Total impact",
            [c["description"] for c in sankey.get_column_information() if c["column_type"] == "manual_split"],
        )

    def test_skip_phase_footprint_split_merges_phases_into_single_nodes(self):
        """Test disabling the phase split merges manufacturing and usage flows into the same Sankey nodes."""
        system = fixture_system("simple")
        sankey = build_sankey(system, skip_phase_footprint_split=True)
        device = system.usage_patterns[0].devices[0]

        self.assertNotIn(("phase", "Manufacturing"), sankey.node_indices)
        self.assertNotIn(("phase", "Usage"), sankey.node_indices)
        self.assertIn((device.id, None), sankey.node_indices)
        self.assertNotIn((device.id, "Usage"), sankey.node_indices)
        device_total = (device.instances_fabrication_footprint.sum() + device.energy_footprint.sum()).value
        device_idx = sankey.node_indices[(device.id, None)]
        self.assertAlmostEqual(
            device_total.to(u.kg).magnitude, sankey.node_total_values[device_idx].to(u.kg).magnitude, places=2)

    def test_skip_object_category_footprint_split_removes_category_nodes(self):
        """Test that skip_object_category_footprint_split=True omits category grouping."""
        sankey = build_sankey(fixture_system("simple"), skip_object_category_footprint_split=True)
        self.assertEqual(0, len(sankey._category_node_indices))
        self.assertTrue(sankey._leaf_node_indices)

    def test_displayed_column_information_orders_columns_by_index(self):
        """Test displayed column information is ordered by column index."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0)
        sankey._built = True
        sankey._impact_repartition_start_column = 2
        sankey._manual_column_information = [{
            "column_index": 3,
            "column_type": "manual_split",
            "description": "Manual column",
        }]

        aggregate_idx = sankey._add_node("Other (2)", ("__aggregated__", 2))
        sankey._node_columns = {aggregate_idx: 2}
        sankey.aggregated_node_classes[aggregate_idx] = ["Storage", "Device"]

        displayed = sankey._get_displayed_column_information()

        self.assertEqual([2, 3], [info["column_index"] for info in displayed])
        self.assertEqual(["Device", "Storage"], displayed[0]["class_names"])
        self.assertEqual("Manual column", displayed[1]["description"])

    def test_figure_can_hide_column_information(self):
        """Test figure without column information annotations."""
        fig = ImpactRepartitionSankey(
            _EmptySystem(), aggregation_threshold_percent=0, display_column_information=False).figure()

        self.assertEqual((), fig.layout.annotations)

    def test_figure_returns_resized_plotly_figure_when_notebook_false(self):
        """Test figure returns a Plotly figure with the requested size when notebook is disabled."""
        fig = ImpactRepartitionSankey(
            _EmptySystem(), aggregation_threshold_percent=0, display_column_information=False).figure(
                width=1234, height=567, notebook=False)

        self.assertEqual(1234, fig.layout.width)
        self.assertEqual(567, fig.layout.height)

    @patch("plotly.offline.plot")
    def test_figure_exports_html_when_filename_is_provided_calls_plotly(self, plot_mock):
        """Test figure writes the HTML file when filename is provided."""
        fig = ImpactRepartitionSankey(
            _EmptySystem(), aggregation_threshold_percent=0, display_column_information=False).figure(
                filename="impact.html", notebook=False)

        self.assertEqual((), fig.layout.annotations)
        plot_mock.assert_called_once()
        self.assertEqual("impact.html", plot_mock.call_args.kwargs["filename"])
        self.assertFalse(plot_mock.call_args.kwargs["auto_open"])

    def test_figure_exports_default_html_when_notebook_true_and_no_filename(self):
        """Test figure exports the default HTML file when notebook is enabled without filename."""
        with patch("plotly.offline.plot") as plot_mock, patch("IPython.display.HTML") as html_mock:
            html_mock.return_value = "html object"

            result = ImpactRepartitionSankey(
                _EmptySystem(), aggregation_threshold_percent=0, display_column_information=False).figure(
                    notebook=True)

        self.assertEqual("html object", result)
        plot_mock.assert_called_once()
        self.assertEqual("Test system impact repartition.html", plot_mock.call_args.kwargs["filename"])
        self.assertFalse(plot_mock.call_args.kwargs["auto_open"])
        html_mock.assert_called_once_with(filename="Test system impact repartition.html")

    def test_figure_returns_file_backed_html_when_notebook_true_and_filename_is_provided(self):
        """Test figure returns file-backed HTML when notebook is enabled with a filename."""
        with patch("plotly.offline.plot") as plot_mock, patch("IPython.display.HTML") as html_mock:
            html_mock.return_value = "html object"

            result = ImpactRepartitionSankey(
                _EmptySystem(), aggregation_threshold_percent=0, display_column_information=False).figure(
                    filename="impact.html", notebook=True)

        self.assertEqual("html object", result)
        plot_mock.assert_called_once()
        self.assertEqual("impact.html", plot_mock.call_args.kwargs["filename"])
        html_mock.assert_called_once_with(filename="impact.html")

    def test_figure_displays_column_information_as_top_annotations(self):
        """Test figure places left-aligned column information above the matching node columns."""
        sankey = ImpactRepartitionSankey(_EmptySystem(), aggregation_threshold_percent=0)
        sankey._built = True
        sankey._manual_column_information = [{
            "column_index": 2,
            "column_type": "manual_split",
            "description": "Manufacturing / usage footprint",
        }]
        total_idx = sankey._add_node("Test system", ("root", "total"))
        aggregate_idx = sankey._add_node("Other (2)", ("__aggregated__", 3))
        sankey._node_columns = {total_idx: 1, aggregate_idx: 3}
        sankey.aggregated_node_classes[aggregate_idx] = ["Device", "Storage"]
        sankey._total_system_value = self._kg(100)
        sankey.node_total_values[total_idx] = self._kg(100)
        sankey.node_total_values[aggregate_idx] = self._kg(60)

        fig = sankey.figure()

        self.assertEqual(2, len(fig.layout.annotations))
        annotation_by_text = {annotation.text: annotation for annotation in fig.layout.annotations}
        self.assertIn("<b>Manufacturing / usage footprint</b>", annotation_by_text)
        self.assertIn("<b>Device<br>Storage</b>", annotation_by_text)
        self.assertAlmostEqual(sankey._column_x_left(2), annotation_by_text["<b>Manufacturing / usage footprint</b>"].x)
        self.assertAlmostEqual(sankey._column_x_left(3), annotation_by_text["<b>Device<br>Storage</b>"].x)
        self.assertTrue(all(annotation.xanchor == "left" for annotation in fig.layout.annotations))
        self.assertTrue(all(annotation.xshift == sankey.get_column_header_x_shift_px() for annotation in fig.layout.annotations))
        self.assertTrue(all(annotation.font.size == 13 for annotation in fig.layout.annotations))
        self.assertTrue(all(annotation.y > 1 for annotation in fig.layout.annotations))


if __name__ == "__main__":
    import unittest
    unittest.main()
