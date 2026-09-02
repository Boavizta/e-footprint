"""Deterministic scaling gates for the native multi-journey topology."""

from unittest import TestCase

from efootprint.abstract_modeling_classes.reactive_core import computed_structures, peek_instance_slot_registry
from efootprint.core.system import System
from performance.memory.inspection import cached_sub_slot_count, linked_objects, materialized_state
from performance.memory.topology import TopologyConfig, build_synthetic_topology


class TestMultiJourneyScaling(TestCase):
    def test_shared_topology_reuses_children_without_reselecting_journeys(self):
        """Test journeys stay distinct and selected once while their lower-level children are shared."""
        topology = build_synthetic_topology(
            TopologyConfig(modeled_hours=24, pattern_count=2, journeys_per_pattern=4, shared_children=True)
        )

        self.assertEqual(4, len(set(topology.web_journeys)))
        self.assertEqual(4, len(set(topology.edge_journeys)))
        self.assertEqual(1, len(topology.web_steps))
        self.assertEqual(1, len(topology.jobs))
        self.assertEqual(1, len(topology.edge_functions))
        self.assertEqual(1, len(topology.edge_processes))
        for pattern in topology.system.usage_patterns:
            self.assertEqual(list(topology.web_journeys), list(pattern.usage_journeys))
        for pattern in topology.system.edge_usage_patterns:
            self.assertEqual(list(topology.edge_journeys), list(pattern.edge_usage_journeys))

    def test_hourly_caches_follow_paths_and_distinct_pattern_need_pairs(self):
        """Test web arrays follow actual paths while shared edge arrays ignore bundle path multiplicity."""
        pattern_count = 2
        journeys_per_pattern = 4
        topology = build_synthetic_topology(
            TopologyConfig(
                modeled_hours=24,
                pattern_count=pattern_count,
                journeys_per_pattern=journeys_per_pattern,
                shared_children=True,
            )
        )
        system = topology.system

        system.impact_repartition_matrix

        expected_web_paths = pattern_count * journeys_per_pattern
        expected_component_pairs = pattern_count * len(topology.recurrent_component_needs)
        expected_server_pairs = pattern_count * len(topology.recurrent_server_needs)
        self.assertEqual(
            expected_web_paths, cached_sub_slot_count(system, "hourly_avg_occurrences_per_usage_coordinate")
        )
        self.assertEqual(
            expected_web_paths + expected_server_pairs,
            cached_sub_slot_count(system, "hourly_avg_occurrences_per_coordinate"),
        )
        self.assertEqual(
            expected_web_paths + expected_server_pairs,
            cached_sub_slot_count(system, "hourly_data_transferred_per_coordinate"),
        )
        self.assertEqual(
            expected_component_pairs, cached_sub_slot_count(system, "unitary_hourly_need_per_usage_pattern")
        )
        self.assertEqual(
            expected_server_pairs, cached_sub_slot_count(system, "unitary_hourly_volume_per_usage_pattern")
        )

        component_path_count = sum(
            len(pattern.containment_inventory.component_need_paths) for pattern in system.edge_usage_patterns
        )
        server_path_count = sum(
            len(pattern.containment_inventory.server_need_paths) for pattern in system.edge_usage_patterns
        )
        self.assertEqual(expected_component_pairs * journeys_per_pattern, component_path_count)
        self.assertEqual(expected_server_pairs * journeys_per_pattern, server_path_count)
        self.assertLess(expected_component_pairs, component_path_count)

    def test_hourly_caches_follow_partially_overlapping_relationships_not_global_cartesian_products(self):
        """Test caches follow overlapping selections rather than every globally available journey and need."""
        topology = build_synthetic_topology(
            TopologyConfig(
                modeled_hours=24,
                pattern_count=2,
                journeys_per_pattern=2,
                shared_children=False,
                overlapping_pattern_subsets=True,
            )
        )
        system = topology.system

        system.impact_repartition_matrix

        expected_web_paths = sum(len(pattern.usage_journeys) for pattern in system.usage_patterns)
        expected_component_pairs = sum(
            len({path.recurrent_edge_component_need for path in pattern.containment_inventory.component_need_paths})
            for pattern in system.edge_usage_patterns
        )
        expected_server_pairs = sum(
            len({path.recurrent_server_need for path in pattern.containment_inventory.server_need_paths})
            for pattern in system.edge_usage_patterns
        )
        self.assertEqual(4, expected_web_paths)
        self.assertEqual(12, expected_component_pairs)
        self.assertEqual(4, expected_server_pairs)
        self.assertLess(expected_web_paths, len(system.usage_patterns) * len(topology.web_journeys))
        self.assertLess(
            expected_component_pairs, len(system.edge_usage_patterns) * len(topology.recurrent_component_needs)
        )
        self.assertEqual(
            expected_web_paths, cached_sub_slot_count(system, "hourly_avg_occurrences_per_usage_coordinate")
        )
        self.assertEqual(
            expected_web_paths + expected_server_pairs,
            cached_sub_slot_count(system, "hourly_avg_occurrences_per_coordinate"),
        )
        self.assertEqual(
            expected_web_paths + expected_server_pairs,
            cached_sub_slot_count(system, "hourly_data_transferred_per_coordinate"),
        )
        self.assertEqual(
            expected_component_pairs, cached_sub_slot_count(system, "unitary_hourly_need_per_usage_pattern")
        )
        self.assertEqual(
            expected_server_pairs, cached_sub_slot_count(system, "unitary_hourly_volume_per_usage_pattern")
        )

    def test_scalar_rows_grow_with_paths_without_retaining_source_helpers(self):
        """Test attribution rows represent added paths while transient source structures are released."""
        one_journey = build_synthetic_topology(
            TopologyConfig(modeled_hours=24, pattern_count=2, journeys_per_pattern=1, shared_children=True)
        ).system
        four_journeys = build_synthetic_topology(
            TopologyConfig(modeled_hours=24, pattern_count=2, journeys_per_pattern=4, shared_children=True)
        ).system

        one_journey.impact_repartition_matrix
        four_journeys.impact_repartition_matrix
        one_state = materialized_state(one_journey)
        four_state = materialized_state(four_journeys)

        self.assertEqual(40, one_state["attribution_matrix_rows"])
        self.assertEqual(160, four_state["attribution_matrix_rows"])
        self.assertEqual(4 * one_state["attribution_matrix_rows"], four_state["attribution_matrix_rows"])
        self.assertEqual(0, one_state["cached_transient_structures"])
        self.assertEqual(0, four_state["cached_transient_structures"])
        for system in (one_journey, four_journeys):
            for obj in linked_objects(system):
                registry = peek_instance_slot_registry(obj)
                for name, descriptor in computed_structures(obj.efootprint_class).items():
                    if descriptor.transient and name in registry:
                        self.assertFalse(registry[name].has_cached_value)
        self.assertIsNotNone(computed_structures(System)["impact_repartition_matrix"].peek(four_journeys))
