from time import perf_counter

from functools import lru_cache
from inspect import signature

from efootprint.logger import logger


@lru_cache(maxsize=None)
def get_init_signature_params(cls):
    return signature(cls.__init__).parameters


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
