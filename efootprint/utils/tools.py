from time import perf_counter

from functools import lru_cache
from inspect import signature
from typing import get_type_hints

from efootprint.logger import logger


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
