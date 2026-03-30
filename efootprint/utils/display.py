import math
from collections.abc import Sequence

import numpy as np
from pint import Quantity, Unit

from efootprint.constants.units import u

UNIT_FAMILIES: list[Sequence[Unit]] = [
    [u.mg, u.g, u.kg, u.tonne],
    [u.mWh, u.Wh, u.kWh, u.MWh, u.GWh],
    [u.mW, u.W, u.kW, u.MW, u.GW],
    [u.occurrence, u.koccurrence, u.Moccurrence, u.Goccurrence],
    [u.concurrent, u.kconcurrent, u.Mconcurrent, u.Gconcurrent],
    [u.byte, u.kB, u.MB, u.GB, u.TB],
    [u.byte_ram, u.kB_ram, u.MB_ram, u.GB_ram, u.TB_ram],
    [u.byte_stored, u.kB_stored, u.MB_stored, u.GB_stored, u.TB_stored],
]


def _get_unit_family(quantity: Quantity) -> Sequence[Unit] | None:
    if quantity.units == u.dimensionless:
        return None
    for family in UNIT_FAMILIES:
        if (1 * family[0]).is_compatible_with(u.dimensionless):
            if any(quantity.units == unit for unit in family):
                return family
        elif quantity.is_compatible_with(family[0]):
            return family
    return None


def _get_representative_magnitude(quantity: Quantity) -> float:
    magnitude = quantity.magnitude
    if isinstance(magnitude, np.ndarray):
        return float(np.mean(np.abs(magnitude)))
    return abs(float(magnitude))


def best_display_unit(quantity: Quantity) -> Unit:
    representative = _get_representative_magnitude(quantity)

    family = _get_unit_family(quantity)
    if family is None:
        return quantity.units
    if representative == 0:
        return family[0]

    representative_quantity = representative * quantity.units
    for unit in reversed(family):
        if representative_quantity.to(unit).magnitude >= 1:
            return unit
    return family[0]


def _round_to_sig_figs(value: float, sig_figs: int = 3) -> float:
    if value == 0:
        return 0.0
    digits = sig_figs - int(math.floor(math.log10(abs(value)))) - 1
    return round(value, digits)


def _round_array_to_sig_figs(values: np.ndarray, sig_figs: int = 3) -> np.ndarray:
    rounded = np.zeros_like(values)
    nonzero_mask = values != 0
    if not np.any(nonzero_mask):
        return rounded

    nonzero_values = values[nonzero_mask].astype(np.float64, copy=False)
    digits = sig_figs - np.floor(np.log10(np.abs(nonzero_values))).astype(np.int64) - 1
    scale = np.power(10.0, digits)
    rounded[nonzero_mask] = np.round(nonzero_values * scale) / scale
    return rounded


def format_quantity_for_display(quantity: Quantity, sig_figs: int = 3) -> Quantity:
    display_unit = best_display_unit(quantity)
    converted = quantity.to(display_unit)
    magnitude = converted.magnitude
    if isinstance(magnitude, np.ndarray):
        rounded = _round_array_to_sig_figs(magnitude, sig_figs)
    else:
        rounded = _round_to_sig_figs(float(magnitude), sig_figs)
    return rounded * display_unit


def human_readable_unit(unit: Unit) -> str:
    output = f"{unit:~P}"
    for special_dimensionless_unit in ["occurrence", "concurrent"]:
        if special_dimensionless_unit in output:
            output = output.replace(special_dimensionless_unit, "")
            if output == "G":
                output = "B"
            break
    return output


def format_display_number(value: float) -> str:
    return np.format_float_positional(value, trim="-")

def display_quantity_as_str(quantity: Quantity, sig_figs: int = 3) -> str:
    formatted_quantity = format_quantity_for_display(quantity, sig_figs)
    return f"{format_display_number(formatted_quantity.magnitude)} {human_readable_unit(formatted_quantity.units)}"
