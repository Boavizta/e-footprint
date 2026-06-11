from functools import lru_cache

import pint
from pint import UnitRegistry

from efootprint.constants.files import CUSTOM_UNITS_PATH

class AttributeCachingUnitRegistry(UnitRegistry):
    """pint resolves every ``u.<unit>`` attribute access through a full unit-string parse (~10 µs each, and
    hot loops do thousands per render). Unit definitions are static after this module loads, so cache each
    resolved Unit in the instance dict — the next access bypasses ``__getattr__`` entirely."""

    def __getattr__(self, item):
        attribute = super().__getattr__(item)
        if not item.startswith("_") and isinstance(attribute, self.Unit):
            self.__dict__[item] = attribute
        return attribute


u = AttributeCachingUnitRegistry(CUSTOM_UNITS_PATH)
u.default_locale = 'en_EN'
pint.set_application_registry(u)


@lru_cache(maxsize=None)
def get_unit(unit_str):
    return u(unit_str)
