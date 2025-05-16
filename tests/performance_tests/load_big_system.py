import json

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.utils.tools import time_it


@time_it
def timed_json_to_system(input_filepath, *args, **kwargs):
    with open(input_filepath, "r") as file:
        system_dict = json.load(file)

    return json_to_system(system_dict, *args, **kwargs)

class_obj_dict, flat_obj_dict = timed_json_to_system("big_system.json", launch_system_computations=False)
