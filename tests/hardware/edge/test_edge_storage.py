import unittest
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.source_objects import SourceValue, SourceHourlyValues
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.hardware.edge.edge_storage import EdgeStorage, NegativeCumulativeStorageNeedError
from efootprint.core.hardware.hardware_base import InsufficientCapacityError
from efootprint.core.usage.edge.edge_usage_pattern import EdgeUsagePattern
from efootprint.core.usage.edge.recurrent_edge_component_need import RecurrentEdgeComponentNeed
from efootprint.core.usage.edge.recurrent_edge_storage_need import RecurrentEdgeStorageNeed
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestEdgeStorage(TestCase):
    def setUp(self):
        self.edge_storage = EdgeStorage(
            name="Test EdgeStorage",
            storage_capacity_per_unit=SourceValue(1 * u.TB_stored),
            carbon_footprint_fabrication_per_storage_capacity=SourceValue(160 * u.kg / u.TB_stored),
            base_storage_need=SourceValue(0 * u.TB_stored),
            lifespan=SourceValue(6 * u.years)
        )
        self.edge_storage.trigger_modeling_updates = False
        self.edge_storage.update_storage_capacity()
        self.edge_storage.update_carbon_footprint_fabrication()

    def test_init(self):
        """Test EdgeStorage initialization."""
        self.assertEqual("Test EdgeStorage", self.edge_storage.name)
        self.assertEqual(1 * u.TB_stored, self.edge_storage.storage_capacity_per_unit.value)
        self.assertEqual(1 * u.TB_stored, self.edge_storage.storage_capacity.value)
        self.assertEqual(
            160 * u.kg / u.TB_stored,
            self.edge_storage.carbon_footprint_fabrication_per_storage_capacity.value,
        )
        self.assertEqual(0 * u.TB_stored, self.edge_storage.base_storage_need.value)
        self.assertEqual(6 * u.years, self.edge_storage.lifespan.value)
        self.assertEqual(1 * u.dimensionless, self.edge_storage.nb_of_units.value)
        self.assertIsInstance(self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern, dict)

    def test_ssd_classmethod(self):
        """Test SSD factory method."""
        ssd = EdgeStorage.ssd(name="Custom SSD")
        ssd.update_storage_capacity()
        self.assertEqual("Custom SSD", ssd.name)
        self.assertEqual(
            160 * u.kg / u.TB_stored,
            ssd.carbon_footprint_fabrication_per_storage_capacity.value,
        )
        self.assertEqual(6 * u.years, ssd.lifespan.value)
        self.assertEqual(1 * u.TB_stored, ssd.storage_capacity.value)
        self.assertEqual(0 * u.TB_stored, ssd.base_storage_need.value)

    def test_ssd_classmethod_with_kwargs(self):
        """Test SSD factory method with custom parameters."""
        ssd = EdgeStorage.ssd(name="Custom SSD with kwargs", storage_capacity_per_unit=SourceValue(2 * u.TB_stored),
                              lifespan=SourceValue(8 * u.years))
        ssd.update_storage_capacity()
        self.assertEqual(2 * u.TB_stored, ssd.storage_capacity.value)
        self.assertEqual(8 * u.years, ssd.lifespan.value)
        self.assertEqual(
            160 * u.kg / u.TB_stored,
            ssd.carbon_footprint_fabrication_per_storage_capacity.value,
        )

    def test_hdd_classmethod(self):
        """Test HDD factory method."""
        hdd = EdgeStorage.hdd(name="Custom HDD")
        hdd.update_storage_capacity()
        self.assertEqual("Custom HDD", hdd.name)
        self.assertEqual(
            20 * u.kg / u.TB_stored,
            hdd.carbon_footprint_fabrication_per_storage_capacity.value,
        )
        self.assertEqual(4 * u.years, hdd.lifespan.value)
        self.assertEqual(1 * u.TB_stored, hdd.storage_capacity.value)
        self.assertEqual(0 * u.TB_stored, hdd.base_storage_need.value)

    def test_hdd_classmethod_with_kwargs(self):
        """Test HDD factory method with custom parameters."""
        hdd = EdgeStorage.hdd(name="Custom HDD with kwargs", storage_capacity_per_unit=SourceValue(4 * u.TB_stored))
        hdd.update_storage_capacity()
        self.assertEqual(4 * u.TB_stored, hdd.storage_capacity.value)
        self.assertEqual(
            20 * u.kg / u.TB_stored,
            hdd.carbon_footprint_fabrication_per_storage_capacity.value,
        )

    def test_archetypes(self):
        """Test archetypes method returns both factory methods."""
        archetypes = EdgeStorage.archetypes()
        self.assertEqual(2, len(archetypes))
        self.assertIn(EdgeStorage.ssd, archetypes)
        self.assertIn(EdgeStorage.hdd, archetypes)

    def test_update_carbon_footprint_fabrication(self):
        """Test update_carbon_footprint_fabrication calculation."""
        with patch.object(
            self.edge_storage,
            "carbon_footprint_fabrication_per_storage_capacity",
            SourceValue(100 * u.kg / u.TB_stored),
        ), patch.object(self.edge_storage, "storage_capacity", SourceValue(2 * u.TB_stored)):
            self.edge_storage.update_carbon_footprint_fabrication()

            # Formula: 100 kg/TB * 2 TB = 200 kg
            self.assertAlmostEqual(200, self.edge_storage.carbon_footprint_fabrication.value.magnitude, places=5)
            self.assertEqual(u.kg, self.edge_storage.carbon_footprint_fabrication.value.units)
            self.assertEqual("Carbon footprint",
                             self.edge_storage.carbon_footprint_fabrication.label)

    def test_update_carbon_footprint_fabrication_with_nb_of_units(self):
        """Test update_carbon_footprint_fabrication multiplies by nb_of_units."""
        self.edge_storage.carbon_footprint_fabrication_per_storage_capacity = SourceValue(100 * u.kg / u.TB_stored)
        self.edge_storage.storage_capacity_per_unit = SourceValue(2 * u.TB_stored)
        self.edge_storage.nb_of_units = SourceValue(3 * u.dimensionless)
        self.edge_storage.update_storage_capacity()

        self.edge_storage.update_carbon_footprint_fabrication()

        self.assertAlmostEqual(600, self.edge_storage.carbon_footprint_fabrication.value.magnitude, places=5)

    def test_recurrent_edge_storage_needs_raises_for_non_storage_component_need(self):
        """Test recurrent_edge_storage_needs raises when a non-storage component need is linked."""
        invalid_need = create_mod_obj_mock(RecurrentEdgeComponentNeed, name="Invalid need", id="invalid_need_id")
        valid_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Valid storage need", id="valid_storage_need_id")
        set_modeling_obj_containers(self.edge_storage, [invalid_need, valid_need])

        with self.assertRaises(ValueError) as ctx:
            _ = self.edge_storage.recurrent_edge_storage_needs

        self.assertIn("Invalid need", str(ctx.exception))
        self.assertIn("not RecurrentEdgeStorageNeed objects", str(ctx.exception))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_cumulative_unitary_storage_need_per_usage_pattern_empty(self):
        """Test cumulative storage dict stays empty when no recurrent needs."""
        set_modeling_obj_containers(self.edge_storage, [])
        self.edge_storage.update_cumulative_unitary_storage_need_per_usage_pattern()
        self.assertEqual({}, self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern)

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_with_data(self):
        """Test storage cumulative need is computed independently for one usage pattern."""
        usage_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern full", id="pattern_full_id")
        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Need full", id="need_full_id")
        mock_need.cumulative_unitary_storage_need_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([10, 30, 60], pint_unit=u.GB_stored)
        }
        set_modeling_obj_containers(self.edge_storage, [mock_need])

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB_stored)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB_stored)):
            self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

        # Expected: [10+5, 30+5, 60+5] = [15, 35, 65]
        self.assertTrue(np.allclose(
            [15, 35, 65], self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern].value_as_float_list
        ))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_negative_cumulative_error(self):
        """Test NegativeCumulativeStorageNeedError raised when one usage pattern goes negative."""
        usage_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern negative", id="pattern_negative_id")
        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Negative need", id="negative_need_id")
        mock_need.cumulative_unitary_storage_need_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([-10, -20, -5], pint_unit=u.GB_stored)
        }
        set_modeling_obj_containers(self.edge_storage, [mock_need])

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB_stored)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(100 * u.GB_stored)):
            with self.assertRaises(NegativeCumulativeStorageNeedError) as ctx:
                self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

        self.assertEqual(self.edge_storage, ctx.exception.storage_obj)
        self.assertIn("negative cumulative storage need detected", str(ctx.exception))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_insufficient_capacity_error(self):
        """Test InsufficientCapacityError raised when one usage pattern exceeds storage_capacity."""
        usage_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern large", id="pattern_large_id")
        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Large need", id="large_need_id")
        mock_need.cumulative_unitary_storage_need_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([40, 80], pint_unit=u.GB_stored)
        }
        set_modeling_obj_containers(self.edge_storage, [mock_need])

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(10 * u.GB_stored)), \
             patch.object(self.edge_storage, "storage_capacity", SourceValue(50 * u.GB_stored)):
            with self.assertRaises(InsufficientCapacityError) as ctx:
                self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

        self.assertEqual("storage capacity", ctx.exception.capacity_type)
        self.assertEqual(self.edge_storage, ctx.exception.overloaded_object)
        self.assertEqual(90 * u.GB_stored, ctx.exception.requested_capacity.value)
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern_with_nb_of_units(self):
        """Test storage capacity validation multiplies storage capacity by nb_of_units."""
        usage_pattern = create_mod_obj_mock(EdgeUsagePattern, name="Pattern capacity units", id="pattern_capacity_units")
        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Need capacity units", id="need_capacity_units")
        mock_need.cumulative_unitary_storage_need_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([80, 120], pint_unit=u.GB_stored)
        }
        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.base_storage_need = SourceValue(0 * u.GB_stored)
        self.edge_storage.storage_capacity_per_unit = SourceValue(50 * u.GB_stored)
        self.edge_storage.nb_of_units = SourceValue(3 * u.dimensionless)
        self.edge_storage.update_storage_capacity()

        self.edge_storage.update_dict_element_in_cumulative_unitary_storage_need_per_usage_pattern(usage_pattern)

        self.assertTrue(np.allclose(
            [80, 120],
            self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[usage_pattern].value_as_float_list,
        ))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_cumulative_unitary_storage_need_per_usage_pattern_with_two_deployments(self):
        """Test two usage patterns are kept separate instead of being summed together."""
        pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 1", id="pattern_1_id")
        pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern 2", id="pattern_2_id")
        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Need multi", id="need_multi_id")
        mock_need.edge_usage_patterns = [pattern_1, pattern_2]
        mock_need.cumulative_unitary_storage_need_per_usage_pattern = {
            pattern_1: create_source_hourly_values_from_list([10, 30], pint_unit=u.GB_stored),
            pattern_2: create_source_hourly_values_from_list([40, 50], pint_unit=u.GB_stored),
        }
        set_modeling_obj_containers(self.edge_storage, [mock_need])

        with patch.object(self.edge_storage, "base_storage_need", SourceValue(5 * u.GB_stored)), \
             patch.object(EdgeStorage, "edge_usage_patterns", new_callable=PropertyMock, return_value=[pattern_1, pattern_2]):
            self.edge_storage.update_cumulative_unitary_storage_need_per_usage_pattern()

        self.assertTrue(np.allclose(
            [15, 35], self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[pattern_1].value_as_float_list
        ))
        self.assertTrue(np.allclose(
            [45, 55], self.edge_storage.cumulative_unitary_storage_need_per_usage_pattern[pattern_2].value_as_float_list
        ))
        set_modeling_obj_containers(self.edge_storage, [])

    def test_update_unitary_power_per_usage_pattern_returns_empty(self):
        """Test that energy is neglected: all usage patterns get EmptyExplainableObject power."""
        mock_pattern_1 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern power 1", id="pattern_power_1_id")
        mock_pattern_2 = create_mod_obj_mock(EdgeUsagePattern, name="Pattern power 2", id="pattern_power_2_id")

        mock_need = create_mod_obj_mock(RecurrentEdgeStorageNeed, name="Power need", id="power_need_id")
        mock_need.edge_usage_patterns = [mock_pattern_1, mock_pattern_2]

        set_modeling_obj_containers(self.edge_storage, [mock_need])
        self.edge_storage.update_unitary_power_per_usage_pattern()

        self.assertIsInstance(self.edge_storage.unitary_power_per_usage_pattern[mock_pattern_1], EmptyExplainableObject)
        self.assertIsInstance(self.edge_storage.unitary_power_per_usage_pattern[mock_pattern_2], EmptyExplainableObject)

        set_modeling_obj_containers(self.edge_storage, [])

    def test_negative_cumulative_storage_need_error_message(self):
        """Test NegativeCumulativeStorageNeedError message formatting."""
        cumulative_quantity = SourceHourlyValues(np.array([-5, -10, -2]) * u.GB_stored,
                                                          start_date=datetime(2020, 1, 1))
        error = NegativeCumulativeStorageNeedError(self.edge_storage, cumulative_quantity)

        message = str(error)
        self.assertIn("Test EdgeStorage", message)
        self.assertIn("negative cumulative storage need detected", message)
        self.assertIn("-10.0 GB", message)
        self.assertIn("base_storage_need", message)


if __name__ == "__main__":
    unittest.main()
