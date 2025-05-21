import json
from time import time

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.logger import logger
from efootprint.utils.tools import time_it


def timed_json_to_system(input_filepath, *args, **kwargs):
    start = time()
    with open(input_filepath, "r") as file:
        system_dict = json.load(file)
    logger.info(f"Finished loading JSON file in {round((time() - start), 3)} seconds")

    return json_to_system(system_dict, *args, **kwargs)


def timed_system_to_json(system, save_calculated_attributes, output_filepath):
    output_dict = system_to_json(system, save_calculated_attributes, None)

    start = time()
    with open(output_filepath, "w") as file:
        file.write(json.dumps(output_dict))
    logger.info(f"Finished writing JSON file in {round((time() - start), 3)} seconds")


# class_obj_dict, flat_obj_dict = timed_json_to_system("big_system.json", launch_system_computations=False)
start = time()
nb_system_loadings = 10
for i in range(nb_system_loadings):
    class_obj_dict_computed, flat_obj_dict_computed = timed_json_to_system(
        "big_system_with_calc_attr.json", launch_system_computations=False)
avg_loading_time = (time() - start) / nb_system_loadings
logger.info(f"loading system took {round(avg_loading_time, 3)} seconds on average for {nb_system_loadings} times")

start = time()
for i in range(nb_system_loadings):
    timed_system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                         output_filepath="big_system_with_calc_attr_2.json")
avg_writing_time = (time() - start) / nb_system_loadings
logger.info(f"writing system took {round(avg_writing_time, 3)} seconds on average for {nb_system_loadings} times")

with open("big_system_with_calc_attr.json") as f1, open("big_system_with_calc_attr_2.json") as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)

print(data1 == data2)
import cProfile
import pstats
import io

pr = cProfile.Profile()
pr.enable()

# 🔥 Call the function you want to profile
timed_json_to_system(
        "big_system_with_calc_attr.json", launch_system_computations=False)

pr.disable()

# 👇 This keeps full paths instead of just __init__.py
s = io.StringIO()
ps = pstats.Stats(pr, stream=s)
ps.sort_stats("cumtime").print_stats(30)  # Adjust number of lines as needed

print(s.getvalue())
