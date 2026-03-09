import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_storage import EdgeStorage, NegativeCumulativeStorageNeedError
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeStorage(TestCase):
    def setUp(self):
        self.edge_storage = EdgeStorage(
            name="Test EdgeStorage",
            storage_capacity=SourceValue(1 * u.TB),
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB),
            base_storage_need=SourceValue(0 * u.TB),
            lifespan=SourceValue(6 * u.years)
        )
        self.edge_storage.trigger_modeling_updates = False

    def test_init(self):
        """Test EdgeStorage initialization."""
        self.assertEqual("Test EdgeStorage", self.edge_storage.name)
        self.assertEqual(1 * u.TB, self.edge_storage.storage_capacity.value)
        self.assertEqual(160 * u.kg / u.TB, self.edge_storage.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(0 * u.TB, self.edge_storage.base_storage_need.value)
        self.assertEqual(6 * u.years, self.edge_storage.lifespan.value)
        self.assertIsInstance(self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need, ExplainableObjectDict)
        self.assertIsInstance(self.edge_storage.full_cumulative_storage_need, EmptyExplainableObject)

    def test_ssd_classmethod(self):
        """Test SSD factory method."""
        ssd = EdgeStorage.ssd(name="Custom SSD")
        self.assertEqual("Custom SSD", ssd.name)
        self.assertEqual(160 * u.kg / u.TB, ssd.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(6 * u.years, ssd.lifespan.value)
        self.assertEqual(1 * u.TB, ssd.storage_capacity.value)
        self.assertEqual(0 * u.TB, ssd.base_storage_need.value)

    def test_ssd_classmethod_with_kwargs(self):
        """Test SSD factory method with custom parameters."""
        ssd = EdgeStorage.ssd(name="Custom SSD with kwargs", storage_capacity=SourceValue(2 * u.TB),
                              lifespan=SourceValue(8 * u.years))
        self.assertEqual(2 * u.TB, ssd.storage_capacity.value)
        self.assertEqual(8 * u.years, ssd.lifespan.value)
        self.assertEqual(160 * u.kg / u.TB, ssd.carbon_footprint_fabrication_per_storage_capacity.value)

    def test_hdd_classmethod(self):
        """Test HDD factory method."""
        hdd = EdgeStorage.hdd(name="Custom HDD")
        self.assertEqual("Custom HDD", hdd.name)
        self.assertEqual(20 * u.kg / u.TB, hdd.carbon_footprint_fabrication_per_storage_capacity.value)
        self.assertEqual(4 * u.years, hdd.lifespan.value)
        self.assertEqual(1 * u.TB, hdd.storage_capacity.value)
        self.assertEqual(0 * u.TB, hdd.base_storage_need.value)

    def test_hdd_classmethod_with_kwargs(self):
        """Test HDD factory method with custom parameters."""
        hdd = EdgeStorage.hdd(name="Custom HDD with kwargs", storage_capacity=SourceValue(4 * u.TB))
        self.assertEqual(4 * u.TB, hdd.storage_capacity.value)
        self.assertEqual(20 * u.kg / u.TB, hdd.carbon_footprint_fabrication_per_storage_capacity.value)

    def test_archetypes(self):
        """Test archetypes method returns both factory methods."""
        archetypes = EdgeStorage.archetypes()
        self.assertEqual(2, len(archetypes))
        self.assertIn(EdgeStorage.ssd, archetypes)
        self.assertIn(EdgeStorage.hdd, archetypes)

    def test_update_carbon_footprint_fabrication(self):
        """Test update_carbon_footprint_fabrication calculation."""
        with patch.object(self.edge_storage, "carbon_footprint_fabrication_per_storage_capacity",
                          SourceValue(100 * u.kg / u.TB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(2 * u.TB)):
            self.edge_storage.update_carbon_footprint_fabrication()

            # Formula: 100 kg/TB * 2 TB = 200 kg
            self.assertAlmostEqual(200, self.edge_storage.carbon_footprint_fabrication.value.magnitude, places=5)
            self.assertEqual(u.kg, self.edge_storage.carbon_footprint_fabrication.value.units)
            self.assertEqual("Carbon footprint of Test EdgeStorage",
                             self.edge_storage.carbon_footprint_fabrication.label)

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need_empty(self):
        """Test cumulative storage is EmptyExplainableObject when recurrent need has no usage patterns."""
        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Empty need", id="empty_need_id")
        mock_need.edge_usage_patterns = []

        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need(mock_need)

        result = self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need[mock_need]
        self.assertIsInstance(result, EmptyExplainableObject)
        self.assertIn("Cumulative storage for Empty need in Test EdgeStorage", result.label)

        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need_single_pattern(self):
        """Test cumulative storage is the cumsum of the unitary hourly need."""
        mock_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern A", id="pattern_a_id")

        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Storage need A", id="storage_need_a_id")
        mock_need.edge_usage_patterns = [mock_pattern]
        # Unitary hourly storage delta: [10, 20, 30] GB per hour
        mock_need.unitary_hourly_need_per_usage_pattern = {
            mock_pattern: create_source_hourly_values_from_list([10, 20, 30], pint_unit=u.GB)}

        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need(mock_need)

        result = self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need[mock_need]
        # cumsum([10, 20, 30]) = [10, 30, 60]
        self.assertTrue(np.allclose([10, 30, 60], result.value_as_float_list))
        self.assertEqual(u.GB, result.unit)
        self.assertIn("Cumulative storage for Storage need A in Test EdgeStorage", result.label)

        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need_multiple_patterns(self):
        """Test cumulative storage sums unitary rates across usage patterns before taking cumsum."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1_id")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2_id")

        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Storage need multi",
                                        id="storage_need_multi_id")
        mock_need.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]
        mock_need.unitary_hourly_need_per_usage_pattern = {
            mock_pattern_1: create_source_hourly_values_from_list([10, 0, 5], pint_unit=u.GB),
            mock_pattern_2: create_source_hourly_values_from_list([0, 20, 5], pint_unit=u.GB),
        }

        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need(mock_need)

        result = self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need[mock_need]
        # Rate sum: [10+0, 0+20, 5+5] = [10, 20, 10], cumsum = [10, 30, 40]
        self.assertTrue(np.allclose([10, 30, 40], result.value_as_float_list))

        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_cumulative_unitary_storage_need_per_recurrent_need(self):
        """Test update method resets the dict and iterates over all recurrent needs."""
        mock_need_1 = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Need 1", id="need_1_id")
        mock_need_2 = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Need 2", id="need_2_id")

        set_modeling_obj_containers(self.edge_storage, [mock_need_1, mock_need_2])

        with patch.object(EdgeStorage,
                          "update_dict_element_in_cumulative_unitary_storage_need_per_recurrent_need") as mock_update:
            self.edge_storage.update_cumulative_unitary_storage_need_per_recurrent_need()

            self.assertEqual(2, mock_update.call_count)
            mock_update.assert_any_call(mock_need_1)
            mock_update.assert_any_call(mock_need_2)

        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_full_cumulative_storage_need_empty(self):
        """Test full_cumulative_storage_need is EmptyExplainableObject when no recurrent needs."""
        self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need = ExplainableObjectDict()
        self.edge_storage.update_full_cumulative_storage_need()
        self.assertIsInstance(self.edge_storage.full_cumulative_storage_need, EmptyExplainableObject)

    def test_update_full_cumulative_storage_need_with_data(self):
        """Test full_cumulative_storage_need sums per-need cumulatives and adds base_storage_need."""
        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Need full", id="need_full_id")
        # Per-need cumulative already computed: [10, 30, 60] GB
        self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need = {
            mock_need: create_source_hourly_values_from_list([10, 30, 60], pint_unit=u.GB)}

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB)):
            self.edge_storage.update_full_cumulative_storage_need()

        # Expected: [10+5, 30+5, 60+5] = [15, 35, 65]
        self.assertTrue(np.allclose([15, 35, 65], self.edge_storage.full_cumulative_storage_need.value_as_float_list))

    def test_update_full_cumulative_storage_need_negative_cumulative_error(self):
        """Test NegativeCumulativeStorageNeedError raised when total goes negative."""
        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Negative need", id="negative_need_id")
        # base_storage_need (5 GB) + [-10, -20, -5] GB = [-5, -15, 0] GB — negative
        self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need = {
            mock_need: create_source_hourly_values_from_list([-10, -20, -5], pint_unit=u.GB)}

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB)):
            with self.assertRaises(NegativeCumulativeStorageNeedError) as ctx:
                self.edge_storage.update_full_cumulative_storage_need()

        self.assertEqual(self.edge_storage, ctx.exception.storage_obj)
        self.assertIn("negative cumulative storage need detected", str(ctx.exception))

    def test_update_full_cumulative_storage_need_insufficient_capacity_error(self):
        """Test InsufficientCapacityError raised when total cumulative exceeds storage_capacity."""
        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Large need", id="large_need_id")
        # base_storage_need (10 GB) + max(cumulative) [80 GB] = 90 GB > 50 GB capacity
        self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need = {
            mock_need: create_source_hourly_values_from_list([40, 80], pint_unit=u.GB)}

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(10 * u.GB)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(50 * u.GB)):
            with self.assertRaises(InsufficientCapacityError) as ctx:
                self.edge_storage.update_full_cumulative_storage_need()

        self.assertEqual("storage capacity", ctx.exception.capacity_type)
        self.assertEqual(self.edge_storage, ctx.exception.overloaded_object)
        self.assertEqual(90 * u.GB, ctx.exception.requested_capacity.value)

    def test_update_unitary_power_per_usage_pattern_returns_empty(self):
        """Test that energy is neglected: all usage patterns get EmptyExplainableObject power."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern power 1", id="pattern_power_1_id")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern power 2", id="pattern_power_2_id")

        mock_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Power need", id="power_need_id")
        mock_need.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.update_unitary_power_per_usage_pattern()

        self.assertIsInstance(self.edge_storage.unitary_power_per_usage_pattern[mock_pattern_1], EmptyExplainableObject)
        self.assertIsInstance(self.edge_storage.unitary_power_per_usage_pattern[mock_pattern_2], EmptyExplainableObject)

        set_modeling_obj_containers(self.edge_storage, [])

    def test_impact_repartition_weights_returns_cumulative_per_recurrent_need(self):
        """Test impact_repartition_weights property returns cumulative_unitary_storage_need_per_recurrent_need."""
        self.assertIs(self.edge_storage.cumulative_unitary_storage_need_per_recurrent_need,
                      self.edge_storage.impact_repartition_weights)

    def test_negative_cumulative_storage_need_error_message(self):
        """Test NegativeCumulativeStorageNeedError message formatting."""
        cumulative_quantity = SourceHourlyValues(np.array([-5, -10, -2]) * u.GB,
                                                          start_date=datetime(2020, 1, 1))
        error = NegativeCumulativeStorageNeedError(self.edge_storage, cumulative_quantity)

        message = str(error)
        self.assertIn("Test EdgeStorage", message)
        self.assertIn("negative cumulative storage need detected", message)
        self.assertIn("-10.0 GB", message)
        self.assertIn("base_storage_need", message)


if __name__ == "__main__":
    unittest.main()
