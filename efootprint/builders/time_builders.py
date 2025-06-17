from datetime import datetime, timedelta
from typing import List

import numpy as np
from pint import Quantity, Unit
import ciso8601

from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues


def create_random_source_hourly_values(
        timespan: Quantity = 1 * u.day, min_val: int = 1, max_val: int = 10,
        start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    nb_days = timespan.to(u.day).magnitude
    data = Quantity(
        np.random.randint(min_val, max_val, size=int(nb_days * 24)).astype(np.float32, copy=False), pint_unit)
    shv = SourceHourlyValues(data, start_date=start_date)

    return shv


def create_source_hourly_values_from_list(
        input_list: List[float], start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    return SourceHourlyValues(Quantity(np.array(input_list, dtype=np.float32), pint_unit), start_date)


def linear_growth_hourly_values(
        timespan: Quantity, start_value: int, end_value: int,
        start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    nb_of_hours = int(timespan.to(u.hour).magnitude)
    linear_growth = np.linspace(start_value, end_value, nb_of_hours, dtype=np.float32)

    return create_source_hourly_values_from_list(linear_growth, start_date, pint_unit)


def sinusoidal_fluct_hourly_values(
        timespan: Quantity, sin_fluct_amplitude: int, sin_fluct_period_in_hours: int,
        start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    nb_of_hours = int(timespan.to(u.hour).magnitude)
    time = np.arange(nb_of_hours, dtype=np.float32)
    sinusoidal_fluctuation = (
            sin_fluct_amplitude * np.sin(2 * np.pi * time / sin_fluct_period_in_hours, dtype=np.float32))

    return create_source_hourly_values_from_list(sinusoidal_fluctuation, start_date, pint_unit)


def daily_fluct_hourly_values(
        timespan: Quantity, fluct_scale: float, hour_of_day_for_min_value: int = 4,
        start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    assert fluct_scale > 0
    assert fluct_scale <= 1
    nb_of_hours = int(timespan.to(u.hour).magnitude)
    time = np.arange(nb_of_hours, dtype=np.float32)
    hour_of_day = [(start_date.hour + x) % 24 for x in time]

    daily_fluctuation = (
            np.full(shape=len(hour_of_day), fill_value=1.0, dtype=np.float32)
            + fluct_scale * np.sin(
                (3 * np.pi / 2)
                + (2 * np.pi
                    * (hour_of_day - np.full(
                            shape=len(hour_of_day), fill_value=float(hour_of_day_for_min_value), dtype=np.float32))
                    / 24
                ), dtype=np.float32
            )
        )

    return create_source_hourly_values_from_list(daily_fluctuation, start_date, pint_unit)


def create_hourly_usage_from_frequency(
        timespan: Quantity, input_volume: float, frequency: str, active_days: list = None,
        hours: list = None, start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    if frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
        raise ValueError(f"frequency must be one of 'daily', 'weekly', 'monthly', or 'yearly', got {frequency}.")

    if frequency == 'daily' and active_days is not None:
        raise ValueError(f"active_days must be None for daily frequency, got {active_days}.")

    if active_days is None:
        if frequency == "weekly":
            active_days = [0]  # default to midnight or Monday
        else:
            active_days = [1]  # default to first day of month or first day of year

    if hours is None:
        hours = [0]  # default to midnight

    period_index = [start_date + timedelta(hours=i) for i in range(int(timespan.to(u.hour).magnitude) + 1)]
    # Important to have fill_value be 0.0 otherwise values will be cast to int
    values = np.full(shape=len(period_index), fill_value=0.0, dtype=np.float32)

    for i, period in enumerate(period_index):
        hour_of_day = period.hour  # Hour of the day, 0 to 23
        day_of_week = period.weekday()  # Day of the week, 0 to 6
        day_of_month = period.day  # Day of the month, 1 to 31
        day_of_year = period.timetuple().tm_yday  # Day of the year, 1 to 365/366
        if frequency == 'daily':
            if hour_of_day in hours:
                values[i] = input_volume
        elif frequency == 'weekly':
            if day_of_week in active_days and hour_of_day in hours:
                values[i] = input_volume
        elif frequency == 'monthly':
            if day_of_month in active_days and hour_of_day in hours:
                values[i] = input_volume
        elif frequency == 'yearly':
            if day_of_year in active_days and hour_of_day in hours:
                values[i] = input_volume

    return SourceHourlyValues(Quantity(values, pint_unit), start_date, label="Hourly usage")


def create_hourly_usage_from_daily_volume_and_list_of_hours(
        timespan: Quantity, daily_volume: float, hours: List[int],
        start_date: datetime = ciso8601.parse_datetime("2025-01-01"),
        pint_unit: Unit = u.dimensionless):
    volume_per_hour = daily_volume / len(hours)

    return create_hourly_usage_from_frequency(
        timespan, volume_per_hour, frequency='daily', active_days=None, hours=hours,
        start_date=start_date, pint_unit=pint_unit)
