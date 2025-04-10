from pandas import DataFrame


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