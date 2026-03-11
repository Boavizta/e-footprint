from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.utils.impact_repartition_sankey import ImpactRepartitionSankey


class _DummyQuantity:
    def __init__(self, magnitude):
        self.magnitude = magnitude


class _DummyObject:
    def __init__(self, name, object_id):
        self.name = name
        self.id = object_id
        self.class_as_simple_str = self.__class__.__name__.lstrip("_")
        self.impact_repartition = {}

    def __hash__(self):
        return hash(self.id)


class TestImpactRepartitionSankey(TestCase):
    def _make_object(self, name):
        obj = MagicMock()
        obj.name = name
        obj.id = name.lower().replace(" ", "_")
        return obj

    def test_all_canonical_classes_are_in_sankey_columns(self):
        from efootprint.all_classes_in_order import ALL_CANONICAL_CLASSES_DICT, SANKEY_COLUMNS

        excluded_classes = ["System", "Service"]
        canonical_classes_dict_without_excluded = {
            name: cls for name, cls in ALL_CANONICAL_CLASSES_DICT.items() if name not in excluded_classes}

        sankey_column_classes = set()
        for column_list in SANKEY_COLUMNS:
            sankey_column_classes.update(column_list)

        missing_classes = set(canonical_classes_dict_without_excluded.values()) - sankey_column_classes
        self.assertFalse(missing_classes,
                         f"The following canonical classes are missing from sankey columns: {missing_classes}")

    def _build_sankey(self, aggregation_threshold_percent):
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=aggregation_threshold_percent)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_idx = sankey._add_node("Parent", ("parent", "energy"), color_key="parent", obj=self._make_object("Parent"))
        small_a_idx = sankey._add_node("Small A", ("small_a", "energy"), color_key="small_a", obj=self._make_object("Small A"))
        small_b_idx = sankey._add_node("Small B", ("small_b", "energy"), color_key="small_b", obj=self._make_object("Small B"))
        child_big_idx = sankey._add_node("Child Big", ("child_big", "energy"), color_key="child_big", obj=self._make_object("Child Big"))
        child_small_a_idx = sankey._add_node(
            "Child Small A", ("child_small_a", "energy"), color_key="child_small_a", obj=self._make_object("Child Small A"))
        child_small_b_idx = sankey._add_node(
            "Child Small B", ("child_small_b", "energy"), color_key="child_small_b", obj=self._make_object("Child Small B"))

        sankey._total_system_kg = 1000
        sankey.node_total_kg[total_idx] = 1000
        sankey._node_columns = {
            total_idx: 1, parent_idx: 2, small_a_idx: 2, small_b_idx: 2,
            child_big_idx: 3, child_small_a_idx: 3, child_small_b_idx: 3,
        }
        sankey._add_link(total_idx, parent_idx, 0.72)
        sankey._add_link(total_idx, small_a_idx, 0.10)
        sankey._add_link(total_idx, small_b_idx, 0.08)
        sankey._add_link(parent_idx, child_big_idx, 0.54)
        sankey._add_link(parent_idx, child_small_a_idx, 0.10)
        sankey._add_link(parent_idx, child_small_b_idx, 0.08)
        return sankey

    def test_aggregate_small_nodes_by_column_groups_only_same_column(self):
        """Test small nodes are aggregated per column and listed in hover text."""
        sankey = self._build_sankey(aggregation_threshold_percent=15)

        sankey._aggregate_small_nodes_by_column()
        hover_labels = sankey._build_hover_labels()

        self.assertEqual(2, sankey.node_labels.count("Other (2)"))
        self.assertEqual(2, len(sankey.aggregated_node_members))
        links_to_aggregates = sorted(
            round(value, 2)
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

    def test_aggregate_small_nodes_by_column_keeps_different_parents_separate(self):
        """Test small nodes are aggregated separately when they do not share the same parent."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=15)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_a_idx = sankey._add_node("Parent A", ("parent_a", "energy"), obj=self._make_object("Parent A"))
        parent_b_idx = sankey._add_node("Parent B", ("parent_b", "energy"), obj=self._make_object("Parent B"))
        small_a1_idx = sankey._add_node("Small A1", ("small_a1", "energy"), obj=self._make_object("Small A1"))
        small_a2_idx = sankey._add_node("Small A2", ("small_a2", "energy"), obj=self._make_object("Small A2"))
        small_b1_idx = sankey._add_node("Small B1", ("small_b1", "energy"), obj=self._make_object("Small B1"))
        small_b2_idx = sankey._add_node("Small B2", ("small_b2", "energy"), obj=self._make_object("Small B2"))

        sankey._total_system_kg = 1000
        sankey.node_total_kg[total_idx] = 1000
        sankey._node_columns = {
            total_idx: 1, parent_a_idx: 2, parent_b_idx: 2,
            small_a1_idx: 3, small_a2_idx: 3, small_b1_idx: 3, small_b2_idx: 3,
        }
        sankey._add_link(total_idx, parent_a_idx, 0.36)
        sankey._add_link(total_idx, parent_b_idx, 0.36)
        sankey._add_link(parent_a_idx, small_a1_idx, 0.10)
        sankey._add_link(parent_a_idx, small_a2_idx, 0.08)
        sankey._add_link(parent_b_idx, small_b1_idx, 0.10)
        sankey._add_link(parent_b_idx, small_b2_idx, 0.08)

        sankey._aggregate_small_nodes_by_column()
        hover_labels = [label for label in sankey._build_hover_labels() if label.startswith("Other (2)<br>")]

        self.assertNotIn("Other (4)", sankey.node_labels)
        self.assertEqual(2, sankey.node_labels.count("Other (2)"))
        self.assertEqual(2, len(sankey.aggregated_node_members))
        self.assertEqual(2, len(hover_labels))
        self.assertTrue(any("Small A1" in label and "Small A2" in label for label in hover_labels))
        self.assertTrue(any("Small B1" in label and "Small B2" in label for label in hover_labels))
        self.assertFalse(any("Small A1" in label and "Small B1" in label for label in hover_labels))

    def test_aggregate_small_nodes_by_column_recomputes_children_after_parent_aggregation(self):
        """Test child columns are re-aggregated after their parents collapse into an aggregated node."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=15)

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        parent_a_idx = sankey._add_node("Parent A", ("parent_a", "energy"), obj=self._make_object("Parent A"))
        parent_b_idx = sankey._add_node("Parent B", ("parent_b", "energy"), obj=self._make_object("Parent B"))
        child_a_idx = sankey._add_node("Child A", ("child_a", "energy"), obj=self._make_object("Child A"))
        child_b_idx = sankey._add_node("Child B", ("child_b", "energy"), obj=self._make_object("Child B"))

        sankey._total_system_kg = 1000
        sankey.node_total_kg[total_idx] = 1000
        sankey._node_columns = {
            total_idx: 1, parent_a_idx: 2, parent_b_idx: 2, child_a_idx: 3, child_b_idx: 3,
        }
        sankey._add_link(total_idx, parent_a_idx, 0.08)
        sankey._add_link(total_idx, parent_b_idx, 0.07)
        sankey._add_link(parent_a_idx, child_a_idx, 0.08)
        sankey._add_link(parent_b_idx, child_b_idx, 0.07)

        sankey._aggregate_small_nodes_by_column()
        hover_labels = [label for label in sankey._build_hover_labels() if label.startswith("Other (2)<br>")]

        self.assertEqual(2, sankey.node_labels.count("Other (2)"))
        self.assertEqual(2, len(hover_labels))
        self.assertTrue(any("Parent A" in label and "Parent B" in label for label in hover_labels))
        self.assertTrue(any("Child A" in label and "Child B" in label for label in hover_labels))

    def test_build_merges_recursive_repartition_contributions_on_same_edge(self):
        """Test recursive repartition contributions sharing an edge are merged into one flow."""
        grandchild = _DummyObject("Grandchild", "grandchild")
        child = _DummyObject("Child", "child")
        parent = _DummyObject("Parent", "parent")
        child.impact_repartition = {grandchild: _DummyQuantity(1)}
        parent.impact_repartition = {child: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(200)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100), parent: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)

        sankey.build()

        child_idx = sankey.node_indices[("child", "fabrication")]
        grandchild_idx = sankey.node_indices[("grandchild", "fabrication")]
        incoming_to_grandchild = [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == child_idx and target == grandchild_idx
        ]

        self.assertEqual([0.2], incoming_to_grandchild)
        self.assertEqual(200, sankey.node_total_kg[grandchild_idx])

    def test_skip_object_footprint_split_merges_identical_child_edges(self):
        """Test skipping object nodes keeps a single outbound flow per parent-child pair."""
        shared_child = _DummyObject("Shared child", "shared_child")
        parent_a = _DummyObject("Parent A", "parent_a")
        parent_b = _DummyObject("Parent B", "parent_b")
        parent_a.impact_repartition = {shared_child: _DummyQuantity(1)}
        parent_b.impact_repartition = {shared_child: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(180)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {
            parent_a: _DummyQuantity(100), parent_b: _DummyQuantity(80),
        }}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_footprint_split=True)

        sankey.build()

        edge_idx = sankey.node_indices[("edge", "fabrication")]
        shared_child_idx = sankey.node_indices[("shared_child", "fabrication")]
        shared_child_links = [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == edge_idx and target == shared_child_idx
        ]

        self.assertEqual([0.18], shared_child_links)

    def test_node_labels_are_truncated_but_hover_keeps_full_name(self):
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)

        node_idx = sankey._add_node("12345678901234", ("long_name", "energy"))
        sankey._total_system_kg = 1
        sankey.node_total_kg[node_idx] = 1

        self.assertEqual("1234567890123...", sankey.node_labels[node_idx])
        self.assertEqual("12345678901234", sankey.full_node_labels[node_idx])
        self.assertTrue(sankey._build_hover_labels()[node_idx].startswith("12345678901234<br>"))

    def test_node_label_max_length_is_configurable(self):
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0, node_label_max_length=5)

        node_idx = sankey._add_node("123456", ("custom_length", "energy"))

        self.assertEqual("12345...", sankey.node_labels[node_idx])
        self.assertEqual("123456", sankey.full_node_labels[node_idx])

    def test_get_column_metadata_returns_unique_class_names_and_positions(self):
        """Test column metadata from explicitly assigned columns."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
        sankey._built = True

        total_idx = sankey._add_node("Test system", ("system", "total"), color_key="__system__")
        server = _DummyObject("Server", "server")
        server.class_as_simple_str = "Server"
        device = _DummyObject("Device", "device")
        device.class_as_simple_str = "Device"
        router = _DummyObject("Router", "router")
        router.class_as_simple_str = "Router"
        server_idx = sankey._add_node("Server", ("server", "energy"), obj=server)
        device_idx = sankey._add_node("Device", ("device", "energy"), obj=device)
        router_idx = sankey._add_node("Router", ("router", "energy"), obj=router)
        sankey._total_system_kg = 1000
        sankey.node_total_kg[total_idx] = 1000
        sankey._node_columns = {total_idx: 1, server_idx: 2, device_idx: 2, router_idx: 3}
        sankey._add_link(total_idx, server_idx, 0.4)
        sankey._add_link(total_idx, device_idx, 0.3)
        sankey._add_link(server_idx, router_idx, 0.2)

        self.assertEqual([
            {"column_index": 2, "x_center": 0.625, "class_names": ["Device", "Server"]},
            {"column_index": 3, "x_center": 0.875, "class_names": ["Router"]},
        ], sankey.get_column_metadata())

    def test_get_column_metadata_includes_aggregated_member_classes(self):
        sankey = self._build_sankey(aggregation_threshold_percent=15)
        sankey._built = True
        for node in sankey.node_objects.values():
            node.class_as_simple_str = node.name.replace(" ", "")
        sankey._aggregate_small_nodes_by_column()

        self.assertEqual([
            {"column_index": 2, "x_center": 0.625, "class_names": ["Parent", "SmallA", "SmallB"]},
            {"column_index": 3, "x_center": 0.875, "class_names": ["ChildBig", "ChildSmallA", "ChildSmallB"]},
        ], sankey.get_column_metadata())

    def test_get_column_information_distinguishes_manual_and_impact_columns(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        grandchild.class_as_simple_str = "Grandchild"
        child = _DummyObject("Child", "child")
        child.class_as_simple_str = "Child"
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)

        self.assertEqual([
            {"column_index": 1, "column_type": "manual_split", "description": "Fabrication / energy footprint"},
            {"column_index": 2, "column_type": "manual_split", "description": "Per object category footprint"},
            {"column_index": 3, "column_type": "impact_repartition", "class_names": ["Child"]},
            {"column_index": 4, "column_type": "impact_repartition", "class_names": ["Grandchild"]},
        ], sankey.get_column_information())

    def test_figure_displays_column_information_by_default(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        grandchild.class_as_simple_str = "Grandchild"
        child = _DummyObject("Child", "child")
        child.class_as_simple_str = "Child"
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        fig = ImpactRepartitionSankey(system, aggregation_threshold_percent=0).figure()

        self.assertEqual(1, len(fig.layout.annotations))
        self.assertIn("Column 1: Fabrication / energy footprint", fig.layout.annotations[0]["text"])
        self.assertIn("Column 2: Per object category footprint", fig.layout.annotations[0]["text"])
        self.assertIn("Column 3: Child", fig.layout.annotations[0]["text"])
        self.assertIn("Column 4: Grandchild", fig.layout.annotations[0]["text"])

    def test_figure_can_hide_column_information(self):
        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {}
        system.energy_footprint_sum_over_period = {}

        fig = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, display_column_information=False).figure()

        self.assertEqual((), fig.layout.annotations)

    def test_build_skips_configured_impact_repartition_classes(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        skipped_child = _DummyObject("Skipped child", "skipped_child")
        skipped_child.class_as_simple_str = "SkippedClass"
        parent = _DummyObject("Parent", "parent")
        skipped_child.impact_repartition = {grandchild: _DummyQuantity(1)}
        parent.impact_repartition = {skipped_child: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {parent: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skipped_impact_repartition_classes=["SkippedClass"])

        sankey.build()

        self.assertNotIn(("skipped_child", "fabrication"), sankey.node_indices)
        parent_idx = sankey.node_indices[("parent", "fabrication")]
        grandchild_idx = sankey.node_indices[("grandchild", "fabrication")]
        self.assertEqual([0.1], [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == parent_idx and target == grandchild_idx
        ])

    def test_skip_total_footprint_split_removes_system_node_only(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        child = _DummyObject("Child", "child")
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_total_footprint_split=True)

        sankey.build()

        self.assertNotIn(("system", "total"), sankey.node_indices)
        fab_idx = sankey.node_indices[("phase", "fabrication")]
        edge_idx = sankey.node_indices[("edge", "fabrication")]
        self.assertEqual([0.1], [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == fab_idx and target == edge_idx
        ])

    def test_skip_phase_footprint_split_removes_fabrication_energy_nodes_only(self):
        """Test with skip_total=False so system node exists, and skip_phase=True removes phase nodes."""
        grandchild = _DummyObject("Grandchild", "grandchild")
        child = _DummyObject("Child", "child")
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0,
            skip_total_footprint_split=False, skip_phase_footprint_split=True)

        sankey.build()

        self.assertIn(("system", "total"), sankey.node_indices)
        self.assertNotIn(("phase", "fabrication"), sankey.node_indices)
        system_idx = sankey.node_indices[("system", "total")]
        edge_idx = sankey.node_indices[("edge", "fabrication")]
        self.assertEqual([0.1], [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == system_idx and target == edge_idx
        ])

    def test_skip_object_category_footprint_split_removes_category_nodes_only(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        child = _DummyObject("Child", "child")
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_category_footprint_split=True)

        sankey.build()

        fab_idx = sankey.node_indices[("phase", "fabrication")]
        self.assertNotIn(("edge", "fabrication"), sankey.node_indices)
        child_idx = sankey.node_indices[("child", "fabrication")]
        self.assertEqual([0.1], [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if source == fab_idx and target == child_idx
        ])

    def test_build_can_skip_all_manual_split_layers(self):
        grandchild = _DummyObject("Grandchild", "grandchild")
        child = _DummyObject("Child", "child")
        child.impact_repartition = {grandchild: _DummyQuantity(1)}

        system = MagicMock()
        system.name = "Test system"
        system.total_fabrication_footprint_sum_over_period = {"edge": _DummyQuantity(100)}
        system.total_energy_footprint_sum_over_period = {}
        system.fabrication_footprint_sum_over_period = {"edge": {child: _DummyQuantity(100)}}
        system.energy_footprint_sum_over_period = {}

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_total_footprint_split=True,
            skip_phase_footprint_split=True, skip_object_category_footprint_split=True,
            skip_object_footprint_split=True)

        sankey.build()

        self.assertNotIn(("system", "total"), sankey.node_indices)
        self.assertNotIn(("phase", "fabrication"), sankey.node_indices)
        self.assertNotIn(("edge", "fabrication"), sankey.node_indices)
        self.assertNotIn(("child", "fabrication"), sankey.node_indices)
        grandchild_idx = sankey.node_indices[("grandchild", "fabrication")]
        self.assertEqual([0.1], [
            value
            for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
            if target == grandchild_idx
        ])
