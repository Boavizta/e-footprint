from time import perf_counter

from dataclasses import dataclass
from functools import lru_cache
from inspect import signature
from typing import Annotated, get_args, get_origin, get_type_hints

from pint import Unit

from efootprint.logger import logger


@dataclass(frozen=True)
class InputUnit:
    """Expected unit for a quantity input without a quantity class default."""
    unit: Unit


def get_expected_input_unit(cls, param_name):
    """Resolve a quantity default's unit, then quantity-member annotation metadata."""
    from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity

    default_value = cls.default_values.get(param_name)
    if isinstance(default_value, ExplainableQuantity):
        return default_value.value.units

    annotation = get_type_hints(cls.__init__, include_extras=True).get(param_name)
    members = (annotation,) if get_origin(annotation) is Annotated else get_args(annotation)
    for member in members:
        if get_origin(member) is Annotated:
            quantity_type, *metadata = get_args(member)
            if isinstance(quantity_type, type) and issubclass(quantity_type, ExplainableQuantity):
                for item in metadata:
                    if isinstance(item, InputUnit):
                        return item.unit
    raise TypeError(f"No expected unit declared for {cls.__name__}.{param_name}: "
                    "provide a quantity default or InputUnit annotation metadata")


@lru_cache(maxsize=None)
def get_init_signature_params(cls):
    """Return constructor parameters with runtime-resolved type annotations."""
    init_signature = signature(cls.__init__)
    try:
        type_hints = get_type_hints(cls.__init__)
    except Exception as error:
        raise TypeError(f"Could not resolve {cls.__name__}.__init__ type annotations: {error}") from error

    resolved_params = [
        param.replace(annotation=type_hints.get(name, param.annotation))
        for name, param in init_signature.parameters.items()
    ]
    return init_signature.replace(parameters=resolved_params).parameters


def round_dict(my_dict, round_level):
    for key in my_dict:
        my_dict[key] = round(my_dict[key], round_level)

    return my_dict


def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        diff = end_time - start_time
        if diff > 0.000001:
            logger.info(f"Function {func.__name__} took {diff*1000:.1f} ms to execute.")
        return result
    return wrapper
