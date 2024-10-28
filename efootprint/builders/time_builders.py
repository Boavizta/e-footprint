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
        input_volume: float, start_date: datetime, pint_unit: pint.Unit, type_frequency: str,
        duration, only_work_days: bool, time_list:list = None, launch_hour_list: list = None):

    if start_date is None:
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
    if pint_unit is None:
        pint_unit = pint.Unit(u.dimensionless)
    if type_frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
        raise ValueError("type_frequency must be one of 'daily', 'weekly', 'monthly', or 'yearly'.")

    if isinstance(duration, pint.Quantity):
        if duration.units == u.day:
            end_date = start_date + timedelta(days=duration.magnitude - 1)
        elif duration.units == u.week:
            end_date = start_date + timedelta(weeks=duration.magnitude) - timedelta(days=1)
        elif duration.units == u.month:
            end_date = start_date + relativedelta(months=duration.magnitude) - timedelta(days=1)
        elif duration.units == u.year:
            end_date = start_date + relativedelta(years=duration.magnitude) - timedelta(days=1)
        else:
            raise ValueError("Unsupported unit for duration. Use days, weeks, months, or years.")
        end_date = end_date.replace(hour=23)
    else:
        raise TypeError("duration must be a pint.Quantity with time units like days, weeks, months, or years (e.g., 2*u.month).")

    if time_list is None:
        if type_frequency == 'daily':
            time_list = [0]  # default to midnight
        elif type_frequency == 'weekly':
            time_list = [1]  # default to Monday
        elif type_frequency == 'monthly':
            time_list = [1]  # default to the first day of the month
        elif type_frequency == 'yearly':
            time_list = [1]  # default to the first day of the year
        if launch_hour_list is None:
            launch_hour_list = [0]  # default to midnight

    period_index = pd.period_range(start=start_date, end=end_date, freq='h')
    df = pd.DataFrame(0, index=period_index, columns=['value'], dtype=f"pint[{str(pint_unit)}]")

    for current_hour in df.index:
        hour_of_day = current_hour.hour
        day_of_week = current_hour.to_timestamp().weekday()
        day_of_month = current_hour.day
        day_of_year = current_hour.to_timestamp().timetuple().tm_yday  # Day of the year, 1 to 365/366
        if type_frequency == 'daily':
            if hour_of_day in time_list and (not only_work_days or day_of_week < 5):
                df.at[current_hour, 'value'] = input_volume
        elif type_frequency == 'weekly':
            if day_of_week in time_list and hour_of_day in launch_hour_list:
                df.at[current_hour, 'value'] = input_volume
        elif type_frequency == 'monthly':
            if day_of_month in time_list and hour_of_day in launch_hour_list:
                df.at[current_hour, 'value'] = input_volume
        elif type_frequency == 'yearly':
            if day_of_year in time_list and hour_of_day in launch_hour_list:
                df.at[current_hour, 'value'] = input_volume

    return SourceHourlyValues(df, label="Hourly usage")


