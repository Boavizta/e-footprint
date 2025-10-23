import numpy as np
import pytest
from datetime import datetime

from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities


class TestPlotAggregationStconcurrentgy:
    """Test that the plot_aggregation_strategy property returns correct values based on unit type."""

    def test_occurrence_unit_aggregates_by_sum(self):
        """Event units should aggregate by sum."""
        values = np.array([10.0, 20.0, 30.0], dtype=np.float32) * u.occurrence
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test occurrence")
        assert ehq.plot_aggregation_strategy == 'sum'

    def test_concurrent_unit_aggregates_by_mean(self):
        """Rate units should aggregate by mean."""
        values = np.array([1.0, 2.0, 3.0], dtype=np.float32) * u.concurrent
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test concurrent")
        assert ehq.plot_aggregation_strategy == 'mean'

    def test_byte_ram_aggregates_by_mean(self):
        """byte_ram units should aggregate by mean."""
        values = np.array([1e9, 2e9, 3e9], dtype=np.float32) * u.byte_ram
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test RAM")
        assert ehq.plot_aggregation_strategy == 'mean'

    def test_gigabyte_ram_aggregates_by_mean(self):
        """gigabyte_ram units should aggregate by mean."""
        values = np.array([1.0, 2.0, 3.0], dtype=np.float32) * u.GB_ram
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test GB RAM")
        assert ehq.plot_aggregation_strategy == 'mean'

    def test_cpu_core_aggregates_by_mean(self):
        """cpu_core units should aggregate by mean."""
        values = np.array([2.0, 4.0, 6.0], dtype=np.float32) * u.cpu_core
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test CPU")
        assert ehq.plot_aggregation_strategy == 'mean'

    def test_gpu_aggregates_by_mean(self):
        """gpu units should aggregate by mean."""
        values = np.array([1.0, 2.0, 3.0], dtype=np.float32) * u.gpu
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test GPU")
        assert ehq.plot_aggregation_strategy == 'mean'

    def test_energy_aggregates_by_sum(self):
        """Energy units (kWh) should aggregate by sum."""
        values = np.array([0.5, 1.0, 1.5], dtype=np.float32) * u.kWh
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test energy")
        assert ehq.plot_aggregation_strategy == 'sum'

    def test_byte_aggregates_by_sum(self):
        """byte units (data transfer) should aggregate by sum."""
        values = np.array([1e9, 2e9, 3e9], dtype=np.float32) * u.byte
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test data transfer")
        assert ehq.plot_aggregation_strategy == 'sum'

    def test_mass_aggregates_by_sum(self):
        """Mass units (kg) should aggregate by sum."""
        values = np.array([0.1, 0.2, 0.3], dtype=np.float32) * u.kg
        ehq = ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="test mass")
        assert ehq.plot_aggregation_strategy == 'sum'

    def test_recurrent_quantities_occurrence_aggregates_by_sum(self):
        """Event units in ExplainableRecurrentQuantities should aggregate by sum."""
        values = np.array([1.0] * 168, dtype=np.float32) * u.occurrence
        erq = ExplainableRecurrentQuantities(values, label="test recurring occurrence")
        assert erq.plot_aggregation_strategy == 'sum'

    def test_recurrent_quantities_concurrent_aggregates_by_mean(self):
        """Rate units in ExplainableRecurrentQuantities should aggregate by mean."""
        values = np.array([1.0] * 168, dtype=np.float32) * u.concurrent
        erq = ExplainableRecurrentQuantities(values, label="test recurring concurrent")
        assert erq.plot_aggregation_strategy == 'mean'


class TestUnitDistinction:
    """Test that dimensionless, occurrence, and concurrent are distinguishable despite converting 1:1."""

    def test_occurrence_concurrent_and_dimensionless_have_different_string_representations(self):
        """Event, concurrent, and dimensionless should have different string representations."""
        occurrence_unit = u.occurrence
        concurrent_unit = u.concurrent
        dimensionless_unit = u.dimensionless

        assert str(occurrence_unit) == 'occurrence'
        assert str(concurrent_unit) == 'concurrent'
        assert str(dimensionless_unit) == 'dimensionless'

        # They should not be equal
        assert occurrence_unit != concurrent_unit
        assert occurrence_unit != dimensionless_unit
        assert concurrent_unit != dimensionless_unit

    def test_occurrence_and_concurrent_can_be_identified_in_hourly_quantities(self):
        """ExplainableHourlyQuantities with occurrence vs concurrent should be distinguishable."""
        occurrence_values = np.array([10.0, 20.0], dtype=np.float32) * u.occurrence
        concurrent_values = np.array([10.0, 20.0], dtype=np.float32) * u.concurrent

        ehq_occurrence = ExplainableHourlyQuantities(occurrence_values, start_date=datetime(2024, 1, 1), label="occurrence")
        ehq_concurrent = ExplainableHourlyQuantities(concurrent_values, start_date=datetime(2024, 1, 1), label="concurrent")

        assert str(ehq_occurrence.unit) == 'occurrence'
        assert str(ehq_concurrent.unit) == 'concurrent'
        assert ehq_occurrence.unit != ehq_concurrent.unit

    def test_byte_and_byte_ram_are_distinguishable(self):
        """byte and byte_ram should be distinguishable."""
        byte_unit = u.byte
        byte_ram_unit = u.byte_ram

        assert str(byte_unit) == 'byte'
        assert str(byte_ram_unit) == 'byte_ram'
        assert byte_unit != byte_ram_unit

        # Test prefixed versions
        gb_unit = u.GB
        gb_ram_unit = u.GB_ram

        assert 'gigabyte' in str(gb_unit)
        assert 'gigabyte_ram' in str(gb_ram_unit)
        assert gb_unit != gb_ram_unit


class TestDimensionlessBan:
    """Test that dimensionless unit is properly rejected in timeseries classes."""

    def test_hourly_quantities_rejects_dimensionless(self):
        """ExplainableHourlyQuantities should reject dimensionless units."""
        values = np.array([1.0, 2.0], dtype=np.float32) * u.dimensionless

        with pytest.raises(ValueError, match="cannot use dimensionless unit"):
            ExplainableHourlyQuantities(values, start_date=datetime(2024, 1, 1), label="invalid")

    def test_recurrent_quantities_rejects_dimensionless(self):
        """ExplainableRecurrentQuantities should reject dimensionless units."""
        values = np.array([1.0] * 168, dtype=np.float32) * u.dimensionless

        with pytest.raises(ValueError, match="cannot use dimensionless unit"):
            ExplainableRecurrentQuantities(values, label="invalid")

    def test_conversion_to_dimensionless_raises_value_error(self):
        values = np.array([1.0] * 168, dtype=np.float32) * u.concurrent
        erq = ExplainableRecurrentQuantities(values, label="valid")

        with pytest.raises(ValueError, match="cannot use dimensionless unit"):
            erq.to(u.dimensionless)
