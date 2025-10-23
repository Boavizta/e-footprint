"""Shared utilities for timeseries aggregation strategies."""

from pint import Unit, Quantity


def get_plot_aggregation_strategy(unit: Unit) -> str:
    """
    Determine how to aggregate hourly values into daily values for plotting.

    Args:
        unit: The Pint unit of the timeseries

    Returns:
        'sum' for cumulative metrics (events, energy, data transfer)
        'mean' for concurrent/resource allocation metrics (instances, RAM, CPU)
    """
    unit_str = str(unit)

    # Rate and resource allocation units → mean
    if 'concurrent' in unit_str or '_ram' in unit_str or 'cpu_core' in unit_str or 'gpu' in unit_str:
        return 'mean'

    # Default: sum for events, energy, mass, data transfer
    return 'sum'


def validate_timeseries_unit(value: Quantity, label: str = None):
    """
    Validate that a timeseries value does not use dimensionless unit.

    Args:
        value: The Pint Quantity to validate
        label: Optional label for error message

    Raises:
        ValueError: If the value uses dimensionless unit
    """
    from efootprint.constants.units import u

    # Allow dimensionless for unlabeled intermediate calculations (e.g., during division operations)
    # These will be converted to occurrence/concurrent before being assigned
    if value.units == u.dimensionless and label:
        raise ValueError(
            f"Timeseries cannot use dimensionless unit. "
            f"Use 'occurrence' (for discrete occurrences, aggregated by sum) or "
            f"'concurrent' (for concurrent counts, aggregated by mean). "
            f"Label: {label}"
        )