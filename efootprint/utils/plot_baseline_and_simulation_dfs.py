from datetime import datetime
from typing import Optional

import numpy as np
from pandas import DataFrame
from pint import Quantity


def plot_baseline_and_simulation_dfs(baseline_df: DataFrame, simulated_values_df: DataFrame=None,
                                     figsize=(10, 4), xlims=None):
    from matplotlib import pyplot as plt
    import matplotlib.dates as mdates

    if simulated_values_df is not None:
        simulated_values_df["value"] = simulated_values_df["value"].pint.to(baseline_df.dtypes.value.units)

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)

    if xlims is not None:
        start, end = xlims
        filtered_df = baseline_df[(baseline_df.index >= start)
                                  & (baseline_df.index <= end)]
        ax.set_xlim(xlims)
        max_val = filtered_df["value"].max().magnitude
        min_val = filtered_df["value"].min().magnitude
        if simulated_values_df is not None:
            simulated_filtered_df = simulated_values_df[(simulated_values_df.index >= start)
                                                       & (simulated_values_df.index <= end)]
            max_val = max(max_val, simulated_filtered_df["value"].max().magnitude)
            min_val = min(min_val, simulated_filtered_df["value"].min().magnitude)
        offset = (max_val - min_val) * 0.1
        ax.set_ylim([min_val - offset, max_val + offset])

    ax.plot(baseline_df.index.values, baseline_df["value"].values.data, label="baseline")

    if simulated_values_df is not None:
            ax.plot(simulated_values_df.index.values,
                    simulated_values_df["value"].values.data, label="simulated")
        
    ax.legend()
    plt.ylabel(f"{baseline_df.dtypes.value.units:~}")

    locator = mdates.AutoDateLocator(minticks=3, maxticks=12)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    return ax


def plot_baseline_and_simulation_data(
    baseline_q: Quantity, time_baseline: np.ndarray, simulated_q: Optional[Quantity] = None,
    time_sim: Optional[np.ndarray] = None, figsize=(10, 4), xlims: Optional[tuple[datetime, datetime]] = None):
    from matplotlib import pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=figsize)

    if simulated_q is not None:
        simulated_q = simulated_q.to(baseline_q.units)

    if xlims is not None:
        start, end = xlims
        baseline_mask = (time_baseline >= start) & (time_baseline <= end)
        time_baseline_plot = time_baseline[baseline_mask]
        baseline_plot_q = baseline_q[baseline_mask]

        if simulated_q is not None and time_sim is not None:
            sim_mask = (time_sim >= start) & (time_sim <= end)
            time_sim_plot = time_sim[sim_mask]
            simulated_plot_q = simulated_q[sim_mask]
        else:
            time_sim_plot = None
            simulated_plot_q = None

        # Y-axis autoscaling with margin
        all_vals = [baseline_plot_q.magnitude]
        if simulated_q is not None:
            all_vals.append(simulated_plot_q.magnitude)

        min_val = np.min([v.min() for v in all_vals])
        max_val = np.max([v.max() for v in all_vals])
        offset = (max_val - min_val) * 0.1 if max_val != min_val else 1
        ax.set_ylim(min_val - offset, max_val + offset)
        ax.set_xlim(start, end)
    else:
        # Use full data
        time_baseline_plot = time_baseline
        baseline_plot_q = baseline_q
        time_sim_plot = time_sim
        simulated_plot_q = simulated_q

    ax.plot(time_baseline_plot, baseline_plot_q.magnitude, label="baseline")

    if simulated_q is not None and time_sim_plot is not None:
        ax.plot(time_sim_plot, simulated_plot_q.magnitude, label="simulated")

    ax.legend()
    plt.ylabel(f"{baseline_q.units:~}")

    locator = mdates.AutoDateLocator(minticks=3, maxticks=12)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    return fig, ax
