from unittest import TestCase
from unittest.mock import MagicMock

from efootprint.utils.impact_repartition_sankey import ImpactRepartitionSankey


class TestImpactRepartitionSankey(TestCase):
    def _make_object(self, name):
        obj = MagicMock()
        obj.name = name
        obj.id = name.lower().replace(" ", "_")
        return obj

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
