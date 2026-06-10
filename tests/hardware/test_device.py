from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytz

from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.builders.time_builders import create_source_hourly_values_from_list
from efootprint.constants.units import u
from efootprint.core.attribution import atoms_of
from efootprint.core.country import Country
from efootprint.core.hardware.device import Device
from efootprint.core.hardware.network import Network
from efootprint.core.lifecycle_phases import LifeCyclePhases
from efootprint.core.system import System
from efootprint.core.usage.usage_journey import UsageJourney
from efootprint.core.usage.usage_journey_step import UsageJourneyStep
from efootprint.core.usage.usage_pattern import UsagePattern
from tests.core.attribution.conservation import (
    assert_hourly_quantities_equal, assert_source_atoms_conserve, sum_atom_values)
from tests.utils import create_mod_obj_mock, set_modeling_obj_containers


class TestDevice(TestCase):
    def test_update_energy_footprint_sums_over_usage_patterns(self):
        """Test energy footprint sums precomputed per-usage-pattern values."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(1 * u.kg),
            power=SourceValue(1000 * u.W),  # 1 kWh over 1 hour
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(1 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_pattern_1 = MagicMock()
        usage_pattern_1.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_2 = MagicMock()
        usage_pattern_2.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)

        usage_journey = MagicMock()
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([1, 2, 3]),
            usage_pattern_2: create_source_hourly_values_from_list([0, 1, 0]),
        }
        usage_pattern_1.usage_journey = usage_journey
        usage_pattern_2.usage_journey = usage_journey

        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_energy_footprint_per_usage_pattern()
        device.update_energy_footprint()

        self.assertEqual(u.kg, device.energy_footprint.unit)
        self.assertTrue(np.allclose([0.1, 0.4, 0.3], device.energy_footprint.magnitude))

    def test_update_instances_fabrication_footprint_sums_over_usage_patterns(self):
        """Test fabrication footprint distributes fabrication over lifespan and usage time."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(365.25 * 24 * u.kg),
            power=SourceValue(1 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(12 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_pattern_1 = MagicMock()
        usage_pattern_2 = MagicMock()

        usage_journey = MagicMock()
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([1, 2, 3]),
            usage_pattern_2: create_source_hourly_values_from_list([0, 1, 0]),
        }
        usage_pattern_1.usage_journey = usage_journey
        usage_pattern_2.usage_journey = usage_journey

        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_instances_fabrication_footprint_per_usage_pattern()
        device.update_instances_fabrication_footprint()

        self.assertEqual(u.kg, device.instances_fabrication_footprint_per_usage_pattern[usage_pattern_1].unit)
        self.assertTrue(np.allclose(
            [2, 4, 6], device.instances_fabrication_footprint_per_usage_pattern[usage_pattern_1].magnitude))
        self.assertTrue(np.allclose(
            [0, 2, 0], device.instances_fabrication_footprint_per_usage_pattern[usage_pattern_2].magnitude))
        self.assertEqual(u.kg, device.instances_fabrication_footprint.unit)
        self.assertTrue(np.allclose([2, 6, 6], device.instances_fabrication_footprint.magnitude))

    @patch("efootprint.core.hardware.device.Device.usage_journey_steps", new_callable=PropertyMock)
    def test_update_usage_impact_repartition_weights_scales_steps_by_time_spent_and_carbon_intensity(
            self, mock_usage_journey_steps):
        """Test device usage weights follow direct step weights and usage-pattern carbon intensity."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(1 * u.kg),
            power=SourceValue(10 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(1 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_journey = MagicMock()
        usage_journey.duration = SourceValue(40 * u.min)
        step_1 = create_mod_obj_mock(UsageJourneyStep, "Step 1", user_time_spent=SourceValue(10 * u.min))
        step_2 = create_mod_obj_mock(UsageJourneyStep, "Step 2", user_time_spent=SourceValue(30 * u.min))
        step_1.nb_of_occurrences_per_container = {usage_journey: SourceValue(1 * u.dimensionless)}
        step_2.nb_of_occurrences_per_container = {usage_journey: SourceValue(1 * u.dimensionless)}

        usage_pattern_1 = create_mod_obj_mock(UsagePattern, "Pattern 1", usage_journey=usage_journey)
        usage_pattern_1.country = MagicMock()
        usage_pattern_1.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_pattern_1.utc_hourly_usage_journey_starts = create_source_hourly_values_from_list([2], pint_unit=u.occurrence)
        usage_pattern_2 = create_mod_obj_mock(UsagePattern, "Pattern 2", usage_journey=usage_journey)
        usage_pattern_2.country = MagicMock()
        usage_pattern_2.country.average_carbon_intensity = SourceValue(200 * u.g / u.kWh)
        usage_pattern_2.utc_hourly_usage_journey_starts = create_source_hourly_values_from_list([1], pint_unit=u.occurrence)
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern_1: create_source_hourly_values_from_list([2], pint_unit=u.concurrent),
            usage_pattern_2: create_source_hourly_values_from_list([1], pint_unit=u.concurrent),
        }

        step_1.usage_patterns = [usage_pattern_1, usage_pattern_2]
        step_2.usage_patterns = [usage_pattern_1]
        mock_usage_journey_steps.return_value = [step_1, step_2]
        set_modeling_obj_containers(device, [usage_pattern_1, usage_pattern_2])

        device.update_energy_footprint_per_usage_pattern()
        device.update_usage_impact_repartition_weights()

        self.assertEqual(u.kg * u.min, device.usage_impact_repartition_weights[step_1].unit)
        self.assertEqual(u.kg * u.min, device.usage_impact_repartition_weights[step_2].unit)
        self.assertTrue(np.allclose([0.04], device.usage_impact_repartition_weights[step_1].magnitude))
        self.assertTrue(np.allclose([0.06], device.usage_impact_repartition_weights[step_2].magnitude))

    @patch("efootprint.core.hardware.device.Device.usage_journey_steps", new_callable=PropertyMock)
    def test_update_usage_impact_repartition_weights_handles_zero_usage_journey_duration(self, mock_usage_journey_steps):
        """Test device usage weights do not depend on usage-journey duration."""
        device = Device(
            "Test device",
            carbon_footprint_fabrication=SourceValue(1 * u.kg),
            power=SourceValue(10 * u.W),
            lifespan=SourceValue(1 * u.year),
            fraction_of_usage_time=SourceValue(1 * u.hour / u.day),
        )
        device.trigger_modeling_updates = False

        usage_journey = MagicMock()
        usage_journey.duration = SourceValue(0 * u.min)
        step = create_mod_obj_mock(UsageJourneyStep, "Step 1", user_time_spent=SourceValue(10 * u.min))
        step.nb_of_occurrences_per_container = {usage_journey: SourceValue(1 * u.dimensionless)}

        usage_pattern = create_mod_obj_mock(UsagePattern, "Pattern 1", usage_journey=usage_journey)
        usage_pattern.country = MagicMock()
        usage_pattern.country.average_carbon_intensity = SourceValue(100 * u.g / u.kWh)
        usage_journey.nb_usage_journeys_in_parallel_per_usage_pattern = {
            usage_pattern: create_source_hourly_values_from_list([2], pint_unit=u.concurrent),
        }

        step.usage_patterns = [usage_pattern]
        mock_usage_journey_steps.return_value = [step]
        set_modeling_obj_containers(device, [usage_pattern])

        device.update_energy_footprint_per_usage_pattern()
        device.update_usage_impact_repartition_weights()

        self.assertEqual(u.kg * u.min, device.usage_impact_repartition_weights[step].unit)
        self.assertTrue(np.allclose([0.02], device.usage_impact_repartition_weights[step].magnitude))


class TestDeviceAttributionAtoms(TestCase):
    """Device atom builder on a real multi-pattern, multi-country model: conservation per phase and per cell,
    with CI[up] carried inside each usage cell (the double-count / smear fix)."""

    @classmethod
    def setUpClass(cls):
        cls.step_short = UsageJourneyStep("device atoms short step", SourceValue(15 * u.min), [])
        cls.step_long = UsageJourneyStep("device atoms long step", SourceValue(45 * u.min), [])
        cls.journey = UsageJourney("device atoms journey", [cls.step_short, cls.step_long])
        cls.device = Device(
            "device atoms laptop",
            carbon_footprint_fabrication=SourceValue(150 * u.kg),
            power=SourceValue(50 * u.W),
            lifespan=SourceValue(6 * u.year),
            fraction_of_usage_time=SourceValue(7 * u.hour / u.day))
        network = Network("device atoms network", SourceValue(0.05 * u.kWh / u.GB))
        start_date = datetime(2026, 1, 1)
        cls.low_ci_up = UsagePattern(
            "device atoms low ci pattern", cls.journey, [cls.device], network,
            Country("device atoms low ci country", "DLC", SourceValue(50 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([8, 0, 4], start_date))
        cls.high_ci_up = UsagePattern(
            "device atoms high ci pattern", cls.journey, [cls.device], network,
            Country("device atoms high ci country", "DHC", SourceValue(500 * u.g / u.kWh),
                    ExplainableTimezone(pytz.utc, "UTC timezone")),
            create_source_hourly_values_from_list([3, 6], start_date))
        cls.system = System("device atoms system", [cls.low_ci_up, cls.high_ci_up], edge_usage_patterns=[])

    def test_device_atoms_conserve_both_phases(self):
        """Test that Σ atoms recovers the eager phase totals on a multi-pattern, multi-country model."""
        assert_source_atoms_conserve(self, self.device)

    def test_device_atoms_conserve_per_usage_pattern(self):
        """Test that Σ atoms over a pattern's steps recovers the per-pattern eager dicts, both phases."""
        for usage_pattern in (self.low_ci_up, self.high_ci_up):
            usage_atoms = [a for a in atoms_of(self.device, LifeCyclePhases.USAGE) if a.up == usage_pattern]
            assert_hourly_quantities_equal(
                self, self.device.energy_footprint_per_usage_pattern[usage_pattern],
                sum_atom_values(usage_atoms))
            fabrication_atoms = [
                a for a in atoms_of(self.device, LifeCyclePhases.MANUFACTURING) if a.up == usage_pattern]
            assert_hourly_quantities_equal(
                self, self.device.instances_fabrication_footprint_per_usage_pattern[usage_pattern],
                sum_atom_values(fabrication_atoms))

    def test_device_usage_atoms_carry_per_pattern_carbon_intensity(self):
        """Test that each usage cell is occupancy × power × its own pattern's CI — never a blend."""
        for atom in atoms_of(self.device, LifeCyclePhases.USAGE):
            occupancy = atom.step.hourly_avg_occurrences_per_usage_pattern[atom.up]
            expected = (occupancy * self.device.power
                        * ExplainableQuantity(1 * u.hour, "one hour")
                        * atom.up.country.average_carbon_intensity).to(u.kg)
            assert_hourly_quantities_equal(self, expected, atom.value)

    def test_device_atoms_enumerate_one_cell_per_step_and_pattern(self):
        """Test the cell enumeration: one atom per (step, up), step coordinate set, no job/edge coordinates."""
        usage_atoms = list(atoms_of(self.device, LifeCyclePhases.USAGE))
        self.assertEqual(
            {(self.step_short.id, self.low_ci_up.id), (self.step_short.id, self.high_ci_up.id),
             (self.step_long.id, self.low_ci_up.id), (self.step_long.id, self.high_ci_up.id)},
            {(atom.step.id, atom.up.id) for atom in usage_atoms})
        for atom in usage_atoms:
            self.assertIsNone(atom.job)
            self.assertIsNone(atom.rsn)
            self.assertEqual("single", atom.stream)
