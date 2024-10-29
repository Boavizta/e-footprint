from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd
import pint
from dateutil.relativedelta import relativedelta

from efootprint.constants.units import u
from efootprint.abstract_modeling_classes.source_objects import SourceHourlyValues


def create_random_hourly_usage_df(
        nb_days: int = 1, min_val: int = 1, max_val: int = 10,
        start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
        pint_unit: pint.Unit = u.dimensionless):
    end_date = start_date + timedelta(days=nb_days)
    period_index = pd.period_range(start=start_date, end=end_date, freq='h')

    data = np.random.randint(min_val, max_val, size=len(period_index))
    df = pd.DataFrame(data, index=period_index, columns=['value'], dtype=f"pint[{str(pint_unit)}]")

    return df


def create_hourly_usage_df_from_list(
        input_list: List[float], start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
        pint_unit: pint.Unit = u.dimensionless):
    end_date = start_date + timedelta(hours=len(input_list) - 1)
    period_index = pd.period_range(start=start_date, end=end_date, freq='h')

    df = pd.DataFrame(input_list, index=period_index, columns=['value'], dtype=f"pint[{str(pint_unit)}]")

    return df


def linear_growth_hourly_values(
        nb_of_hours: int, start_value: int, end_value: int,
        start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
        pint_unit: pint.Unit = u.dimensionless):
    linear_growth = np.linspace(start_value, end_value, nb_of_hours)

    df = create_hourly_usage_df_from_list(linear_growth, start_date, pint_unit)

    return SourceHourlyValues(df)


def sinusoidal_fluct_hourly_values(
        nb_of_hours: int, sin_fluct_amplitude: int, sin_fluct_period_in_hours: int,
        start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
        pint_unit: pint.Unit = u.dimensionless):
    time = np.arange(nb_of_hours)
    sinusoidal_fluctuation = sin_fluct_amplitude * np.sin(2 * np.pi * time / sin_fluct_period_in_hours)

    df = create_hourly_usage_df_from_list(sinusoidal_fluctuation, start_date, pint_unit)

    return SourceHourlyValues(df)


def daily_fluct_hourly_values(nb_of_hours: int, fluct_scale: float, hour_of_day_for_min_value: int = 4,
                              start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
                              pint_unit: pint.Unit = u.dimensionless):
    assert fluct_scale > 0
    assert fluct_scale <= 1
    time = np.arange(nb_of_hours)
    hour_of_day = [(start_date.hour + x) % 24 for x in time]

    daily_fluctuation = (
            np.full(shape=len(hour_of_day), fill_value=1)
            + fluct_scale * np.sin(
                (3 * np.pi / 2)
                + (2 * np.pi
                    * (hour_of_day - np.full(shape=len(hour_of_day), fill_value=hour_of_day_for_min_value, dtype=int))
                    / 24
                )
            )
        )

    df = create_hourly_usage_df_from_list(daily_fluctuation, start_date, pint_unit)

    return SourceHourlyValues(df)


def create_hourly_usage_from_volume_and_list_of_hour(input_volume: float, start_date: datetime, pint_unit: pint.Unit,
                                                     list_hour: List[int], duration: int):
    if start_date is None:
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
    if pint_unit is None:
        pint_unit = pint.Unit(u.dimensionless)
    if duration is None:
        duration = 365*24

    volume_per_hour = round(input_volume / len(set(list_hour)),0)

    date_range = pd.period_range(start=start_date, periods=duration, freq='h')
    df = pd.DataFrame(0, index=date_range, columns=['value'], dtype=f"pint[{str(pint_unit)}]")

    for index_hour in range(0, duration):
        current_hour = start_date + timedelta(hours=index_hour)
        if current_hour.hour in list_hour:
            df.at[current_hour, 'value'] = volume_per_hour
    return SourceHourlyValues(df, label="Hourly usage")


def create_hourly_usage_from_frequency(
        input_volume: float, duration: pint.Quantity, frequency: str, active_days: list = None,
        launch_hours: list = None, start_date: datetime = datetime.strptime("2025-01-01", "%Y-%m-%d"),
        pint_unit: pint.Unit = u.dimensionless):
    if frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
        raise ValueError(f"frequency must be one of 'daily', 'weekly', 'monthly', or 'yearly', got {frequency}.")

    if frequency == 'daily' and active_days is not None:
        raise ValueError(f"active_days must be None for daily frequency, got {active_days}.")

    end_date = start_date + timedelta(days=duration.to(u.day).magnitude)

    if active_days is None:
        if frequency == "weekly":
            active_days = [0]  # default to midnight or Monday
        else:
            active_days = [1]  # default to first day of month or first day of year

    if launch_hours is None:
        launch_hours = [0]  # default to midnight

    period_index = pd.period_range(start=start_date, end=end_date, freq='h')
    values = np.full(shape=len(period_index), fill_value=0)

    for i, period in enumerate(period_index):
        hour_of_day = period.hour  # Hour of the day, 0 to 23
        day_of_week = period.day_of_week  # Day of the week, 0 to 6
        day_of_month = period.day  # Day of the month, 1 to 31
        day_of_year = period.day_of_year  # Day of the year, 1 to 365/366
        if frequency == 'daily':
            if hour_of_day in launch_hours:
                values[i] = input_volume
        elif frequency == 'weekly':
            if day_of_week in active_days and hour_of_day in launch_hours:
                values[i] = input_volume
        elif frequency == 'monthly':
            if day_of_month in active_days and hour_of_day in launch_hours:
                values[i] = input_volume
        elif frequency == 'yearly':
            if day_of_year in active_days and hour_of_day in launch_hours:
                values[i] = input_volume

    df = pd.DataFrame(values, index=period_index, columns=['value'], dtype=f"pint[{str(pint_unit)}]")

    return SourceHourlyValues(df, label="Hourly usage")
