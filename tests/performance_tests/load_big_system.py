import json
from time import time

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.logger import logger
from efootprint.utils.tools import time_it


@time_it
def timed_json_to_system(input_filepath, *args, **kwargs):
    start = time()
    with open(input_filepath, "r") as file:
        system_dict = json.load(file)
    logger.info(f"Finished loading JSON file in {round((time() - start), 3)} seconds")

    return json_to_system(system_dict, *args, **kwargs)


@time_it
def timed_system_to_json(system, *args, **kwargs):
    system_to_json(system, *args, **kwargs)


# class_obj_dict, flat_obj_dict = timed_json_to_system("big_system.json", launch_system_computations=False)

class_obj_dict_computed, flat_obj_dict_computed = timed_json_to_system(
    "big_system_with_calc_attr.json", launch_system_computations=False)

timed_system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                     output_filepath="big_system_with_calc_attr_2.json")

with open("big_system_with_calc_attr.json") as f1, open("big_system_with_calc_attr_2.json") as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)

print(data1 == data2)