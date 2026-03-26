import math
from collections.abc import Sequence

import numpy as np
from pint import Quantity, Unit

from efootprint.constants.units import u

UNIT_FAMILIES: list[Sequence[Unit]] = [
    [u.mg, u.g, u.kg, u.tonne],
    [u.mWh, u.Wh, u.kWh, u.MWh],
    [u.mW, u.W, u.kW, u.MW],
    [u.byte, u.kB, u.MB, u.GB, u.TB],
    [u.byte_ram, u.kB_ram, u.MB_ram, u.GB_ram, u.TB_ram],
]


def _get_unit_family(quantity: Quantity) -> Sequence[Unit] | None:
    if quantity.units == u.dimensionless:
        return None
    for family in UNIT_FAMILIES:
        if quantity.is_compatible_with(family[0]):
            return family
    return None


def _get_representative_magnitude(quantity: Quantity) -> float:
    magnitude = quantity.magnitude
    if isinstance(magnitude, np.ndarray):
        return float(np.mean(np.abs(magnitude)))
    return abs(float(magnitude))


def best_display_unit(quantity: Quantity) -> Unit:
    representative = _get_representative_magnitude(quantity)
    if representative == 0:
        return quantity.units

    family = _get_unit_family(quantity)
    if family is None:
        return quantity.units

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


def format_quantity_for_display(quantity: Quantity, sig_figs: int = 3) -> Quantity:
    display_unit = best_display_unit(quantity)
    converted = quantity.to(display_unit)
    magnitude = converted.magnitude
    if isinstance(magnitude, np.ndarray):
        rounded = np.vectorize(lambda v: _round_to_sig_figs(float(v), sig_figs))(magnitude)
        rounded = np.asarray(rounded, dtype=magnitude.dtype)
    else:
        rounded = _round_to_sig_figs(float(magnitude), sig_figs)
    return rounded * display_unit


def human_readable_unit(unit: Unit) -> str:
    return f"{unit:~P}"


def format_display_number(value: float) -> str:
    return np.format_float_positional(value, trim="-")
