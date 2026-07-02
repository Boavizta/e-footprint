from datetime import datetime
from typing import Optional

import numpy as np
from pint import Quantity

from efootprint.utils.display import best_display_unit, human_readable_unit


def get_time_axis(start_date: datetime, length: int) -> np.ndarray:
    naive_start = start_date.replace(tzinfo=None) if start_date.tzinfo is not None else start_date
    return np.datetime64(naive_start) + np.arange(length) * np.timedelta64(1, "h")


def prepare_data(q: Quantity, start: datetime, apply_cumsum=False) -> tuple[np.ndarray, Quantity]:
    magnitudes = np.cumsum(q.magnitude) if apply_cumsum else q.magnitude
    return get_time_axis(start, len(magnitudes)), Quantity(magnitudes, q.units)


def plot_timeseries_data(
    q: Quantity, time_axis: np.ndarray, figsize=(10, 4), xlims: Optional[tuple[datetime, datetime]] = None):
    from matplotlib import pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)
    display_unit = best_display_unit(q)
    q = q.to(display_unit)

    if xlims is not None:
        start, end = xlims
        mask = (time_axis >= start) & (time_axis <= end)
        time_axis_plot = time_axis[mask]
        plot_q = q[mask]

        # Y-axis autoscaling with margin
        min_val = plot_q.magnitude.min()
        max_val = plot_q.magnitude.max()
        offset = (max_val - min_val) * 0.1 if max_val != min_val else 1
        ax.set_ylim(min_val - offset, max_val + offset)
        ax.set_xlim(start, end)
    else:
        time_axis_plot = time_axis
        plot_q = q

    ax.plot(time_axis_plot, plot_q.magnitude)

    plt.ylabel(human_readable_unit(display_unit))

    locator = mdates.AutoDateLocator(minticks=3, maxticks=12)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    return fig, ax
