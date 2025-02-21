import time

from efootprint.logger import logger


def round_dict(my_dict, round_level):
    for key in my_dict:
        my_dict[key] = round(my_dict[key], round_level)

    return my_dict


def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        diff = end_time - start_time
        if diff > 0.001:
            logger.info(f"Function {func.__name__} took {diff:.5f} seconds to execute.")
        return result
    return wrapper


def format_co2_amount(co2_amount_in_kg: int, rounding_value=1):
    if co2_amount_in_kg < 501:
        unit = "kg"
        dividing_number = 1
    else:
        unit = "tonne"
        dividing_number = 1000
    rounded_total__new = round(co2_amount_in_kg / dividing_number, rounding_value)
    if rounding_value == 0:
        rounded_total__new = int(rounded_total__new)

    return rounded_total__new, unit


def display_co2_amount(num_value_and_unit_tuple):
    num_value, unit = num_value_and_unit_tuple

    return f"{num_value} {unit}s"
