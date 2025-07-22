from functools import lru_cache

import pint
from pint import UnitRegistry

from efootprint.constants.files import CUSTOM_UNITS_PATH

u = UnitRegistry(CUSTOM_UNITS_PATH)
u.default_locale = 'en_EN'
pint.set_application_registry(u)


@lru_cache(maxsize=None)
def get_unit(unit_str):
    return u(unit_str)
