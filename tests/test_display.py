import unittest

import numpy as np

from efootprint.constants.units import u
from efootprint.utils.display import best_display_unit, format_display_number, format_quantity_for_display, human_readable_unit


class TestDisplayUtils(unittest.TestCase):
    def test_best_display_unit_for_scalar_quantities(self):
        """Test best display unit picks the most readable scalar unit."""
        self.assertEqual(u.tonne, best_display_unit(22000 * u.kg))
        self.assertEqual(u.g, best_display_unit(300 * u.g))
        self.assertEqual(u.MWh, best_display_unit(4500 * u.kWh))

    def test_best_display_unit_for_zero_and_unknown_units(self):
        """Test zero values and unknown unit families keep their current unit."""
        self.assertEqual(u.kg, best_display_unit(0 * u.kg))
        self.assertEqual(u.cpu_core, best_display_unit(42 * u.cpu_core))

    def test_best_display_unit_for_boundaries_and_arrays(self):
        """Test best display unit handles thresholds and array representatives."""
        self.assertEqual(u.g, best_display_unit(0.005 * u.kg))
        self.assertEqual(u.tonne, best_display_unit(1000 * u.kg))
        self.assertEqual(u.kg, best_display_unit(999 * u.kg))
        self.assertEqual(u.tonne, best_display_unit(np.array([100, 200, 50000], dtype=np.float32) * u.kg))
        self.assertEqual(u.kg, best_display_unit(np.array([1, 2, 3], dtype=np.float32) * u.kg))
        self.assertEqual(u.kg, best_display_unit(np.zeros(10, dtype=np.float32) * u.kg))

    def test_format_quantity_for_display_for_scalars(self):
        """Test display formatting converts and rounds scalar quantities."""
        self.assertEqual(22.0 * u.tonne, format_quantity_for_display(22000 * u.kg))
        self.assertEqual(123.0 * u.tonne, format_quantity_for_display(123456 * u.kg))
        self.assertEqual(300.0 * u.g, format_quantity_for_display(300 * u.g))
        self.assertEqual(4.5 * u.MWh, format_quantity_for_display(4500 * u.kWh))
        self.assertEqual(1.23 * u.kg, format_quantity_for_display(1.2345 * u.kg))

    def test_format_quantity_for_display_for_arrays(self):
        """Test display formatting converts and rounds array quantities."""
        formatted = format_quantity_for_display(np.array([1000, 2000, 3000], dtype=np.float32) * u.kg)

        self.assertEqual(u.tonne, formatted.units)
        np.testing.assert_allclose(np.array([1.0, 2.0, 3.0], dtype=np.float32), formatted.magnitude)

    def test_format_quantity_for_display_for_arrays_with_zero_and_negative_values(self):
        """Test array display formatting preserves zero values and rounds negatives correctly."""
        formatted = format_quantity_for_display(np.array([0.0, -0.012345, -12345.6], dtype=np.float32) * u.kg)

        self.assertEqual(u.tonne, formatted.units)
        np.testing.assert_allclose(np.array([0.0, -1.23e-5, -12.3], dtype=np.float32), formatted.magnitude)

    def test_format_quantity_for_display_does_not_mutate_input_quantity(self):
        """Test display formatting returns a new quantity without mutating the input."""
        quantity = 123456 * u.kg

        formatted = format_quantity_for_display(quantity)

        self.assertEqual(123456 * u.kg, quantity)
        self.assertEqual(123.0 * u.tonne, formatted)
        self.assertIsNot(quantity, formatted)

    def test_human_readable_unit_strips_occurrence_and_concurrent(self):
        """Test occurrence and concurrent units display as SI prefix only."""
        self.assertEqual("", human_readable_unit(u.occurrence))
        self.assertEqual("k", human_readable_unit(u.koccurrence))
        self.assertEqual("M", human_readable_unit(u.Moccurrence))
        self.assertEqual("B", human_readable_unit(u.Goccurrence))
        self.assertEqual("", human_readable_unit(u.concurrent))
        self.assertEqual("k", human_readable_unit(u.kconcurrent))
        self.assertEqual("M", human_readable_unit(u.Mconcurrent))
        self.assertEqual("B", human_readable_unit(u.Gconcurrent))

    def test_human_readable_unit_leaves_other_units_unchanged(self):
        """Test non-occurrence/concurrent units are not affected."""
        self.assertEqual("kg", human_readable_unit(u.kg))
        self.assertEqual("kWh", human_readable_unit(u.kWh))
        self.assertEqual("B", human_readable_unit(u.byte))

    def test_format_display_number_preserves_numpy_scalar_formatting(self):
        """Test NumPy scalars do not expand into float precision artifacts when rendered."""
        values = np.array([0.412, 0.825, 1.65, 2.06, 3.3, 4.95], dtype=np.float32)

        formatted = [format_display_number(value) for value in values]

        self.assertEqual(["0.412", "0.825", "1.65", "2.06", "3.3", "4.95"], formatted)


if __name__ == "__main__":
    unittest.main()
