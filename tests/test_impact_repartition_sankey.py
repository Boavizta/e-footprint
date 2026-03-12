from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.impact_repartition_sankey import ImpactRepartitionSankey


class _DummyQuantity:
    def __init__(self, magnitude):
        self.magnitude = magnitude

    def sum(self):
        return self


class _DummyObject:
    def __init__(self, name, object_id, is_impact_source=False):
        self.name = name
        self.id = object_id
        self.class_as_simple_str = self.__class__.__name__.lstrip("_")
        self._is_impact_source = is_impact_source
        self._attributed_footprint_per_source = {LifeCyclePhases.MANUFACTURING: {}, LifeCyclePhases.USAGE: {}}

    @property
    def is_impact_source(self):
        return self._is_impact_source

    @property
    def attributed_footprint_per_source(self):
        return self._attributed_footprint_per_source

    def __hash__(self):
        return hash(self.id)


class _DummyExternalAPIServer(ExternalAPIServer):
    def update_instances_fabrication_footprint(self) -> None:
        return None

    def update_instances_energy(self) -> None:
        return None

    def update_energy_footprint(self) -> None:
        return None

    def update_dict_element_in_impact_repartition_weights(self, modeling_obj):
        return None

    def update_impact_repartition_weights(self):
        return None


class _DummyExternalAPI(ExternalAPI):
    default_values = {}
    server_class = _DummyExternalAPIServer


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

    def test_aggregate_small_nodes_by_column_merges_across_parents(self):
        """Test small nodes in the same column are aggregated together regardless of parent."""
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
        hover_labels = [label for label in sankey._build_hover_labels() if label.startswith("Other (4)<br>")]

        self.assertEqual(1, sankey.node_labels.count("Other (4)"))
        self.assertEqual(1, len(sankey.aggregated_node_members))
        self.assertEqual(1, len(hover_labels))
        self.assertTrue(any(
            "Small A1" in label and "Small A2" in label and "Small B1" in label and "Small B2" in label
            for label in hover_labels))

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

    def _make_simple_system_with_attributed_footprint(self, fab_sources=None, energy_sources=None):
        """Create a system mock with attributed_footprint_per_source."""
        system = _DummyObject("Test system", "test_system")
        system._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {s: _DummyQuantity(v) for s, v in (fab_sources or {}).items()},
            LifeCyclePhases.USAGE: {s: _DummyQuantity(v) for s, v in (energy_sources or {}).items()},
        }
        return system

    def test_build_traverses_attributed_footprint_per_source(self):
        """Test basic traversal from root through intermediate to leaf objects."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
        sankey.build()

        self.assertIn(("root", "total"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_build_skips_configured_impact_repartition_classes(self):
        """Test that objects matching skipped classes are passed through."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        skipped = _DummyObject("Skipped", "skipped")
        skipped.class_as_simple_str = "SkippedClass"
        skipped._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {skipped: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skipped_impact_repartition_classes=["SkippedClass"])
        sankey.build()

        self.assertNotIn(("skipped", "Manufacturing"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_system_in_skipped_classes_removes_system_node(self):
        """Test that putting root's class in skipped_impact_repartition_classes removes the root node."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate.class_as_simple_str = "Intermediate"
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})
        system.class_as_simple_str = "SystemClass"

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skipped_impact_repartition_classes=["SystemClass"])
        sankey.build()

        self.assertNotIn(("root", "total"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_skip_phase_footprint_split_removes_phase_nodes(self):
        """Test that skip_phase_footprint_split=True omits phase nodes."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={leaf: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_phase_footprint_split=True,
            skip_object_category_footprint_split=True, skip_object_footprint_split=True)
        sankey.build()

        self.assertNotIn(("phase", "Manufacturing"), sankey.node_indices)
        self.assertNotIn(("phase", "Usage"), sankey.node_indices)
        self.assertIn(("root", "total"), sankey.node_indices)

    def test_skip_phase_footprint_split_sums_phase_flows_into_same_nodes(self):
        """Test disabling phase split merges manufacturing and usage flows into the same Sankey nodes."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(60)},
            LifeCyclePhases.USAGE: {leaf: _DummyQuantity(40)},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={leaf: 60}, energy_sources={leaf: 40})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_phase_footprint_split=True,
            skip_object_category_footprint_split=True)
        sankey.build()

        self.assertIn(("leaf", None), sankey.node_indices)
        self.assertNotIn(("leaf", "Manufacturing"), sankey.node_indices)
        self.assertNotIn(("leaf", "Usage"), sankey.node_indices)
        leaf_idx = sankey.node_indices[("leaf", None)]
        root_idx = sankey.node_indices[("root", "total")]
        self.assertEqual(100, sankey.node_total_kg[leaf_idx])
        self.assertEqual(
            [(root_idx, leaf_idx, 0.1)],
            list(zip(sankey.link_sources, sankey.link_targets, sankey.link_values)),
        )

    def test_skip_phase_footprint_split_sums_first_column_nodes_when_root_is_skipped(self):
        """Test merged phase totals accumulate on the first visible column when the root node is skipped."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(60)},
            LifeCyclePhases.USAGE: {leaf: _DummyQuantity(40)},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={leaf: 60}, energy_sources={leaf: 40})
        system.class_as_simple_str = "SystemClass"

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_phase_footprint_split=True,
            skip_object_category_footprint_split=True, skipped_impact_repartition_classes=["SystemClass"])
        sankey.build()

        leaf_idx = sankey.node_indices[("leaf", None)]
        self.assertEqual(100, sankey.node_total_kg[leaf_idx])
        self.assertEqual([], sankey.link_sources)
        self.assertEqual([], sankey.link_targets)
        self.assertEqual([], sankey.link_values)

    def test_phase_split_creates_phase_nodes_for_both_phases(self):
        """Test that with both phases, phase split creates Manufacturing and Usage nodes."""
        fab_leaf = _DummyObject("FabLeaf", "fab_leaf", is_impact_source=True)
        fab_leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {fab_leaf: _DummyQuantity(60)},
            LifeCyclePhases.USAGE: {},
        }
        energy_leaf = _DummyObject("EnergyLeaf", "energy_leaf", is_impact_source=True)
        energy_leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {},
            LifeCyclePhases.USAGE: {energy_leaf: _DummyQuantity(40)},
        }
        system = self._make_simple_system_with_attributed_footprint(
            fab_sources={fab_leaf: 60}, energy_sources={energy_leaf: 40})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_category_footprint_split=True,
            skip_object_footprint_split=True)
        sankey.build()

        self.assertIn(("phase", "Manufacturing"), sankey.node_indices)
        self.assertIn(("phase", "Usage"), sankey.node_indices)

    def test_skip_object_category_footprint_split_removes_category_nodes(self):
        """Test that skip_object_category_footprint_split=True omits category grouping."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={leaf: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_category_footprint_split=True)
        sankey.build()

        # No category nodes should exist
        self.assertEqual(0, len(sankey._category_node_indices))

    def test_node_labels_are_truncated_but_hover_keeps_full_name(self):
        """Test label truncation preserves full name in hover."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0, node_label_max_length=13)

        node_idx = sankey._add_node("12345678901234", ("long_name", "energy"))
        sankey._total_system_kg = 1
        sankey.node_total_kg[node_idx] = 1

        self.assertEqual("1234567890123...", sankey.node_labels[node_idx])
        self.assertEqual("12345678901234", sankey.full_node_labels[node_idx])
        self.assertTrue(sankey._build_hover_labels()[node_idx].startswith("12345678901234<br>"))

    def test_node_label_max_length_is_configurable(self):
        """Test custom label max length."""
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

        metadata = sankey.get_column_metadata()
        self.assertEqual([2, 3], [m["column_index"] for m in metadata])
        self.assertEqual([["Device", "Server"], ["Router"]], [m["class_names"] for m in metadata])
        self.assertAlmostEqual(sankey._column_x_center(2), metadata[0]["x_center"])
        self.assertAlmostEqual(sankey._column_x_center(3), metadata[1]["x_center"])

    def test_get_column_metadata_includes_aggregated_member_classes(self):
        """Test column metadata includes classes from aggregated nodes."""
        sankey = self._build_sankey(aggregation_threshold_percent=15)
        sankey._built = True
        for node in sankey.node_objects.values():
            node.class_as_simple_str = node.name.replace(" ", "")
        sankey._aggregate_small_nodes_by_column()

        metadata = sankey.get_column_metadata()
        self.assertEqual([2, 3], [m["column_index"] for m in metadata])
        self.assertEqual(
            [["Parent", "SmallA", "SmallB"], ["ChildBig", "ChildSmallA", "ChildSmallB"]],
            [m["class_names"] for m in metadata])
        self.assertAlmostEqual(sankey._column_x_center(2), metadata[0]["x_center"])
        self.assertAlmostEqual(sankey._column_x_center(3), metadata[1]["x_center"])

    def test_get_column_information_distinguishes_manual_and_impact_columns(self):
        """Test column information reports both manual split and impact repartition columns."""
        leaf = _DummyObject("Leaf", "leaf", is_impact_source=True)
        leaf.class_as_simple_str = "Leaf"
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate.class_as_simple_str = "Intermediate"
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_category_footprint_split=True)
        col_info = sankey.get_column_information()

        manual_cols = [c for c in col_info if c["column_type"] == "manual_split"]
        impact_cols = [c for c in col_info if c["column_type"] == "impact_repartition"]
        self.assertTrue(len(manual_cols) >= 1)
        self.assertTrue(len(impact_cols) >= 1)

    def test_build_column_information_text_orders_columns_by_index(self):
        """Test displayed column information is ordered by column index."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
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

        column_text = sankey._build_column_information_text()

        self.assertEqual("Column 2: Device, Storage<br>Column 3: Manual column", column_text)

    def test_figure_can_hide_column_information(self):
        """Test figure without column information annotations."""
        system = MagicMock()
        system.name = "Test system"
        system.attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {}, LifeCyclePhases.USAGE: {}}
        system.id = "test_system"
        system.class_as_simple_str = "System"

        fig = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, display_column_information=False).figure()

        self.assertEqual((), fig.layout.annotations)

    def test_lifecycle_phase_filter_shows_only_filtered_phase(self):
        """Test that lifecycle_phase_filter limits to one phase."""
        fab_leaf = _DummyObject("FabLeaf", "fab_leaf", is_impact_source=True)
        fab_leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {fab_leaf: _DummyQuantity(60)},
            LifeCyclePhases.USAGE: {},
        }
        energy_leaf = _DummyObject("EnergyLeaf", "energy_leaf", is_impact_source=True)
        energy_leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {},
            LifeCyclePhases.USAGE: {energy_leaf: _DummyQuantity(40)},
        }
        system = self._make_simple_system_with_attributed_footprint(
            fab_sources={fab_leaf: 60}, energy_sources={energy_leaf: 40})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0,
            lifecycle_phase_filter=LifeCyclePhases.MANUFACTURING,
            skip_object_category_footprint_split=True)
        sankey.build()

        # Only manufacturing phase should appear, total should be 60
        self.assertEqual(60, sankey._total_system_kg)

    def test_excluded_object_types_removes_objects_and_reduces_total(self):
        """Test that excluded_object_types excludes objects and reduces total footprint."""
        leaf_a = _DummyObject("LeafA", "leaf_a", is_impact_source=True)
        leaf_a.class_as_simple_str = "TypeA"
        leaf_a._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf_a: _DummyQuantity(60)},
            LifeCyclePhases.USAGE: {},
        }
        leaf_b = _DummyObject("LeafB", "leaf_b", is_impact_source=True)
        leaf_b.class_as_simple_str = "TypeB"
        leaf_b._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf_b: _DummyQuantity(40)},
            LifeCyclePhases.USAGE: {},
        }
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf_a: _DummyQuantity(60), leaf_b: _DummyQuantity(40)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, excluded_object_types=["TypeB"],
            skip_object_category_footprint_split=True)
        sankey.build()

        # Total should exclude TypeB's 40kg
        self.assertEqual(60, sankey._total_system_kg)
        intermediate_idx = sankey.node_indices[("intermediate", "Manufacturing")]
        phase_idx = sankey.node_indices[("phase", "Manufacturing")]
        self.assertEqual(60, sankey.node_total_kg[intermediate_idx])
        link_values_by_edge = {
            (source, target): value for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
        }
        self.assertEqual(0.06, link_values_by_edge[(phase_idx, intermediate_idx)])
        self.assertEqual(0.06, link_values_by_edge[(intermediate_idx, sankey.node_indices[("leaf_a", "Manufacturing")])])

    def test_external_api_server_sources_are_normalized_to_external_api(self):
        """Test ExternalAPIServer impact sources are displayed as ExternalAPI category and leaf."""
        external_api = _DummyExternalAPI("External API")
        intermediate = _DummyObject("Intermediate", "intermediate")
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {external_api.server: _DummyQuantity(100)},
            LifeCyclePhases.USAGE: {},
        }
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
        sankey.build()

        self.assertIn(("ExternalAPIs", "Manufacturing"), sankey.node_indices)
        self.assertIn((external_api.id, "Manufacturing"), sankey.node_indices)
        self.assertNotIn((external_api.server.id, "Manufacturing"), sankey.node_indices)
