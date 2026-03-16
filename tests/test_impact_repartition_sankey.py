from unittest import TestCase
from unittest.mock import MagicMock
import re

from efootprint.builders.external_apis.external_api_base_class import ExternalAPI, ExternalAPIServer
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.utils.sankey import ImpactRepartitionSankey
from tests.utils import set_modeling_obj_containers


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


class _SkippedObject(_DummyObject):
    pass


class _DummySystemObject(_DummyObject):
    pass


class _TypeAObject(_DummyObject):
    pass


class _TypeBObject(_DummyObject):
    pass


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
    @staticmethod
    def _make_object_id(name):
        normalized_name = name.replace(" ", "_")
        return re.sub(r"(?<!^)(?=[A-Z])", "_", normalized_name).lower()

    def _make_object(self, name, is_impact_source=False, class_name=None, obj_cls=_DummyObject):
        obj = obj_cls(name, self._make_object_id(name), is_impact_source=is_impact_source)
        if class_name is not None:
            obj.class_as_simple_str = class_name
        return obj

    def _make_leaf(self, name, manufacturing_kg=0, usage_kg=0, class_name=None, obj_cls=_DummyObject):
        leaf = self._make_object(name, is_impact_source=True, class_name=class_name, obj_cls=obj_cls)
        leaf.instances_fabrication_footprint = _DummyQuantity(manufacturing_kg)
        leaf.energy_footprint = _DummyQuantity(usage_kg)
        leaf._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {leaf: _DummyQuantity(manufacturing_kg)} if manufacturing_kg else {},
            LifeCyclePhases.USAGE: {leaf: _DummyQuantity(usage_kg)} if usage_kg else {},
        }
        leaf.footprint_breakdown_by_source = {
            LifeCyclePhases.MANUFACTURING: {},
            LifeCyclePhases.USAGE: {},
        }
        return leaf

    def _make_breakdown_leaf(
            self, name, manufacturing_kg=0, usage_kg=0, manufacturing_breakdown=None, usage_breakdown=None,
            class_name=None, obj_cls=_DummyObject):
        leaf = self._make_leaf(
            name, manufacturing_kg=manufacturing_kg, usage_kg=usage_kg, class_name=class_name, obj_cls=obj_cls)
        leaf.footprint_breakdown_by_source = {
            LifeCyclePhases.MANUFACTURING: {
                source: _DummyQuantity(value) for source, value in (manufacturing_breakdown or {}).items()
            },
            LifeCyclePhases.USAGE: {
                source: _DummyQuantity(value) for source, value in (usage_breakdown or {}).items()
            },
        }
        return leaf

    def _make_intermediate(self, name, manufacturing_sources=None, usage_sources=None, class_name=None, obj_cls=_DummyObject):
        intermediate = self._make_object(name, class_name=class_name, obj_cls=obj_cls)
        intermediate._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {
                source: _DummyQuantity(value) for source, value in (manufacturing_sources or {}).items()
            },
            LifeCyclePhases.USAGE: {
                source: _DummyQuantity(value) for source, value in (usage_sources or {}).items()
            },
        }
        return intermediate

    def _make_simple_system_with_attributed_footprint(self, fab_sources=None, energy_sources=None, system_cls=_DummyObject):
        system = system_cls("Test system", "test_system")
        system._attributed_footprint_per_source = {
            LifeCyclePhases.MANUFACTURING: {s: _DummyQuantity(v) for s, v in (fab_sources or {}).items()},
            LifeCyclePhases.USAGE: {s: _DummyQuantity(v) for s, v in (energy_sources or {}).items()},
        }
        return system

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

    def test_build_traverses_attributed_footprint_per_source(self):
        """Test basic traversal from root through intermediate to leaf objects."""
        leaf = self._make_leaf("Leaf", manufacturing_kg=100)
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={leaf: 100})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
        sankey.build()

        self.assertIn(("root", "total"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_build_skips_configured_impact_repartition_classes(self):
        """Test that objects matching skipped classes are passed through."""
        leaf = self._make_leaf("Leaf", manufacturing_kg=100)
        skipped = self._make_intermediate("Skipped", manufacturing_sources={leaf: 100}, obj_cls=_SkippedObject)
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={skipped: 100})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skipped_impact_repartition_classes=[_SkippedObject])
        sankey.build()

        self.assertNotIn(("skipped", "Manufacturing"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_system_in_skipped_classes_removes_system_node(self):
        """Test that putting root's class in skipped_impact_repartition_classes removes the root node."""
        leaf = self._make_leaf("Leaf", manufacturing_kg=100)
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={leaf: 100}, class_name="Intermediate")
        system = self._make_simple_system_with_attributed_footprint(
            fab_sources={intermediate: 100}, system_cls=_DummySystemObject)

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skipped_impact_repartition_classes=[_DummySystemObject])
        sankey.build()

        self.assertNotIn(("root", "total"), sankey.node_indices)
        self.assertIn(("intermediate", "Manufacturing"), sankey.node_indices)

    def test_skip_phase_footprint_split_removes_phase_nodes(self):
        """Test that skip_phase_footprint_split=True omits phase nodes."""
        leaf = self._make_leaf("Leaf", manufacturing_kg=100)
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
        leaf = self._make_leaf("Leaf", manufacturing_kg=60, usage_kg=40)
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
        leaf = self._make_leaf("Leaf", manufacturing_kg=60, usage_kg=40)
        system = self._make_simple_system_with_attributed_footprint(
            fab_sources={leaf: 60}, energy_sources={leaf: 40}, system_cls=_DummySystemObject)

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_phase_footprint_split=True,
            skip_object_category_footprint_split=True, skipped_impact_repartition_classes=[_DummySystemObject])
        sankey.build()

        leaf_idx = sankey.node_indices[("leaf", None)]
        self.assertEqual(100, sankey.node_total_kg[leaf_idx])
        self.assertEqual([], sankey.link_sources)
        self.assertEqual([], sankey.link_targets)
        self.assertEqual([], sankey.link_values)

    def test_phase_split_creates_phase_nodes_for_both_phases(self):
        """Test that with both phases, phase split creates Manufacturing and Usage nodes."""
        fab_leaf = self._make_leaf("FabLeaf", manufacturing_kg=60)
        energy_leaf = self._make_leaf("EnergyLeaf", usage_kg=40)
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
        leaf = self._make_leaf("Leaf", manufacturing_kg=100)
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

    def test_build_link_labels_keeps_visible_endpoints_across_spacer_nodes(self):
        """Test spacer-segmented links keep the original visible source and target in hover labels."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)

        source_idx = sankey._add_node("Source", ("source", "energy"))
        target_idx = sankey._add_node("Target", ("target", "energy"))
        sankey._total_system_kg = 100
        sankey.node_total_kg[source_idx] = 100
        sankey._node_columns = {source_idx: 1, target_idx: 4}
        sankey._add_link(source_idx, target_idx, 0.1)

        sankey._insert_spacer_nodes()
        link_labels = sankey._build_link_labels()

        self.assertEqual(3, len(link_labels))
        self.assertEqual(1, len(set(link_labels)))
        self.assertTrue(all(label.startswith("Source → Target<br>") for label in link_labels))
        self.assertTrue(all(label.endswith("CO2eq (100.0%)") for label in link_labels))

    def test_get_column_information_distinguishes_manual_and_impact_columns(self):
        """Test column information reports both manual split and impact repartition columns."""
        leaf = self._make_leaf("Leaf", manufacturing_kg=100, class_name="Leaf")
        intermediate = self._make_intermediate(
            "Intermediate", manufacturing_sources={leaf: 100}, class_name="Intermediate")
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

    def test_figure_displays_column_information_as_top_annotations(self):
        """Test figure places column information above the Sankey at the matching x positions."""
        system = MagicMock()
        system.name = "Test system"
        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
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
        sankey._total_system_kg = 100
        sankey.node_total_kg[total_idx] = 100
        sankey.node_total_kg[aggregate_idx] = 60

        fig = sankey.figure()

        self.assertEqual(2, len(fig.layout.annotations))
        annotation_by_text = {annotation.text: annotation for annotation in fig.layout.annotations}
        self.assertIn("Manufacturing / usage footprint", annotation_by_text)
        self.assertIn("Device<br>Storage", annotation_by_text)
        self.assertAlmostEqual(sankey._column_x_center(2), annotation_by_text["Manufacturing / usage footprint"].x)
        self.assertAlmostEqual(sankey._column_x_center(3), annotation_by_text["Device<br>Storage"].x)
        self.assertTrue(all(annotation.y > 1 for annotation in fig.layout.annotations))

    def test_lifecycle_phase_filter_shows_only_filtered_phase(self):
        """Test that lifecycle_phase_filter limits to one phase."""
        fab_leaf = self._make_leaf("FabLeaf", manufacturing_kg=60)
        energy_leaf = self._make_leaf("EnergyLeaf", usage_kg=40)
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
        leaf_a = self._make_leaf("LeafA", manufacturing_kg=60, obj_cls=_TypeAObject)
        leaf_b = self._make_leaf("LeafB", manufacturing_kg=40, obj_cls=_TypeBObject)
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={leaf_a: 60, leaf_b: 40})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, excluded_object_types=[_TypeBObject],
            skip_object_category_footprint_split=True)
        sankey.build()

        # Total should exclude TypeB's 40kg
        self.assertEqual(60, sankey._total_system_kg)
        intermediate_idx = sankey.node_indices[("intermediate", "Manufacturing")]
        phase_idx = sankey.node_indices[("phase", "Manufacturing")]
        root_idx = sankey.node_indices[("root", "total")]
        self.assertEqual(60, sankey.node_total_kg[phase_idx])
        self.assertEqual(60, sankey.node_total_kg[intermediate_idx])
        link_values_by_edge = {
            (source, target): value for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
        }
        self.assertEqual(0.06, link_values_by_edge[(root_idx, phase_idx)])
        self.assertEqual(0.06, link_values_by_edge[(phase_idx, intermediate_idx)])
        self.assertEqual(0.06, link_values_by_edge[(intermediate_idx, sankey.node_indices[("leaf_a", "Manufacturing")])])

    def test_external_api_server_sources_are_normalized_to_external_api(self):
        """Test ExternalAPIServer impact sources are displayed as ExternalAPI category and leaf."""
        external_api = _DummyExternalAPI("External API")
        set_modeling_obj_containers(external_api.server, [external_api])
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={external_api.server: 100})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(system, aggregation_threshold_percent=0)
        sankey.build()

        self.assertIn(("ExternalAPIs", "Manufacturing"), sankey.node_indices)
        self.assertIn((external_api.id, "Manufacturing"), sankey.node_indices)
        self.assertNotIn((external_api.server.id, "Manufacturing"), sankey.node_indices)

    def test_impact_source_breakdown_scales_child_flows_from_leaf_share(self):
        """Test impact-source breakdown is expanded generically and scaled to the attributed leaf flow."""
        child_a = self._make_leaf("Child A", manufacturing_kg=25)
        child_b = self._make_leaf("Child B", manufacturing_kg=75)
        breakdown_leaf = self._make_breakdown_leaf(
            "Breakdown source",
            manufacturing_kg=100,
            manufacturing_breakdown={child_a: 25, child_b: 75},
        )
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={breakdown_leaf: 40})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 40})

        sankey = ImpactRepartitionSankey(
            system, aggregation_threshold_percent=0, skip_object_category_footprint_split=True)
        sankey.build()

        breakdown_leaf_idx = sankey.node_indices[(breakdown_leaf.id, "Manufacturing")]
        child_a_idx = sankey.node_indices[(child_a.id, "Manufacturing")]
        child_b_idx = sankey.node_indices[(child_b.id, "Manufacturing")]
        link_values_by_edge = {
            (source, target): value for source, target, value in zip(sankey.link_sources, sankey.link_targets, sankey.link_values)
        }
        self.assertEqual(0.01, link_values_by_edge[(breakdown_leaf_idx, child_a_idx)])
        self.assertEqual(0.03, link_values_by_edge[(breakdown_leaf_idx, child_b_idx)])
        self.assertEqual(sankey._node_columns[breakdown_leaf_idx] + 1, sankey._node_columns[child_a_idx])
        self.assertEqual(sankey._node_columns[child_a_idx], sankey._node_columns[child_b_idx])

    def test_skipped_impact_repartition_classes_skip_breakdown_children(self):
        """Test skipped classes remove matching breakdown children while keeping the parent impact source."""
        child_a = self._make_leaf("Child A", manufacturing_kg=25)
        child_b = self._make_leaf("Child B", manufacturing_kg=75, obj_cls=_SkippedObject)
        breakdown_leaf = self._make_breakdown_leaf(
            "Breakdown source",
            manufacturing_kg=100,
            manufacturing_breakdown={child_a: 25, child_b: 75},
        )
        intermediate = self._make_intermediate("Intermediate", manufacturing_sources={breakdown_leaf: 100})
        system = self._make_simple_system_with_attributed_footprint(fab_sources={intermediate: 100})

        sankey = ImpactRepartitionSankey(
            system,
            aggregation_threshold_percent=0,
            skip_object_category_footprint_split=True,
            skipped_impact_repartition_classes=[_SkippedObject],
        )
        sankey.build()

        self.assertIn((breakdown_leaf.id, "Manufacturing"), sankey.node_indices)
        self.assertIn((child_a.id, "Manufacturing"), sankey.node_indices)
        self.assertNotIn((child_b.id, "Manufacturing"), sankey.node_indices)
