import json
import os
from time import time
from unittest import TestCase

from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.logger import logger

root_dir = os.path.dirname(os.path.abspath(__file__))


class TestBigSystemFromAndToJsonPerformance(TestCase):
    def test_big_system_from_and_to_json_performance(self):
        start = time()
        with open(os.path.join(root_dir, "big_system_with_calc_attr.json"), "r") as file:
            system_dict = json.load(file)
        logger.info(f"Finished loading JSON file in {round((time() - start), 3)} seconds")


        start = time()
        nb_system_loadings = 50
        for i in range(nb_system_loadings):
            class_obj_dict_computed, flat_obj_dict_computed = json_to_system(
                system_dict, launch_system_computations=False)
        avg_loading_time = (time() - start) / nb_system_loadings
        logger.info(
            f"deserializing system took {round(avg_loading_time, 3)} seconds on average for {nb_system_loadings} times")
        self.assertLess(avg_loading_time, 0.05)

        start = time()
        for i in range(nb_system_loadings):
            system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                                 output_filepath=None)
        avg_writing_time = (time() - start) / nb_system_loadings
        logger.info(
            f"serializing system took {round(avg_writing_time, 3)} seconds on average for {nb_system_loadings} times")
        self.assertLess(avg_writing_time, 0.05)


if __name__ == "__main__":
    start = time()
    with open("big_system_with_calc_attr.json", "r") as file:
        system_dict = json.load(file)
    logger.info(f"Finished loading JSON file in {round((time() - start), 3)} seconds")

    start = time()
    nb_system_loadings = 100
    for i in range(nb_system_loadings):
        class_obj_dict_computed, flat_obj_dict_computed = json_to_system(system_dict, launch_system_computations=False)
    avg_loading_time = (time() - start) / nb_system_loadings
    logger.info(
        f"deserializing system took {round(avg_loading_time, 3)} seconds on average for {nb_system_loadings} times")

    start = time()
    for i in range(nb_system_loadings):
        system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                       output_filepath=None)
    avg_writing_time = (time() - start) / nb_system_loadings
    logger.info(
        f"serializing system took {round(avg_writing_time, 3)} seconds on average for {nb_system_loadings} times")

    with open("big_system_with_calc_attr.json") as f1, open("big_system_with_calc_attr_2.json") as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    print(data1 == data2)

    run_cprofile = False

    if run_cprofile:
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

        # 🔥 Call the function you want to profile
        system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                                 output_filepath=None)

        pr.disable()

        # 👇 This keeps full paths instead of just __init__.py
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats("cumtime").print_stats(30)  # Adjust number of lines as needed

        print(s.getvalue())
