import json
import os
from time import time, sleep
from unittest import TestCase
import gc
from collections import Counter

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.builders.time_builders import create_random_source_hourly_values
from efootprint.logger import logger
from efootprint.constants.units import u

root_dir = os.path.dirname(os.path.abspath(__file__))


def log_number_of_live_objects(sleep_duration=0.5):
    gc.collect()
    all_objects = gc.get_objects()
    logger.info(f"# ModelingObjects after GC: {sum(1 for o in all_objects if isinstance(o, ModelingObject))}")
    logger.info(
        f"# ExplainableObjects after GC: {sum(1 for o in all_objects if isinstance(o, ExplainableObject))}")
    logger.info(
        f"# ObjectLinkedToModelingObj after GC: "
        f"{sum(1 for o in all_objects if isinstance(o, ObjectLinkedToModelingObj))}")

    type_counts = Counter(type(obj) for obj in all_objects)
    for obj_type, count in type_counts.most_common(5):
        logger.info(f"# {obj_type.__name__} after GC: {count}")

    sleep(sleep_duration)


def update_on_system(
        nb_system_loadings: 10, system_dict: dict, object_type: str, attr_to_change: str, new_value: ExplainableObject):
    start = time()
    system_to_json_duration = 0
    for i in range(nb_system_loadings):
        class_obj_dict_computed, flat_obj_dict_computed = json_to_system(
            system_dict, launch_system_computations=False)
        first_object = next(iter(class_obj_dict_computed[object_type].values()))
        first_object.__setattr__(attr_to_change, new_value)
        system_to_json_start = time()
        system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                       output_filepath=None)
        system_to_json_duration += time() - system_to_json_start
    avg_loading_editing_writing_time = round(1000 * (time() - start) / nb_system_loadings, 1)
    avg_system_to_json_time = round(1000 * system_to_json_duration / nb_system_loadings, 1)
    avg_system_to_json_time_percentage = round(100 * avg_system_to_json_time / avg_loading_editing_writing_time, 1)
    logger.info(
        f"deserializing system then editing {attr_to_change} in first {object_type} then reserializing system took\n"
        f"{avg_loading_editing_writing_time} ms on average for {nb_system_loadings} times, including "
        f"{avg_system_to_json_time} ms of system_to_json ({avg_system_to_json_time_percentage}% of total time)")

    return avg_loading_editing_writing_time


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
        self.assertLess(avg_loading_time, 0.075)

        start = time()
        for i in range(nb_system_loadings):
            system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                                 output_filepath=None)
        avg_writing_time = (time() - start) / nb_system_loadings
        logger.info(
            f"serializing system took {round(avg_writing_time, 3)} seconds on average for {nb_system_loadings} times")
        self.assertLess(avg_writing_time, 0.075)

        nb_system_loadings = 10
        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "UsagePattern","hourly_usage_journey_starts",
            create_random_source_hourly_values(timespan=3 * u.year))
        self.assertLess(avg_loading_editing_writing_time, 800)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "Job", "data_transferred",
            SourceValue(100 * u.MB))
        self.assertLess(avg_loading_editing_writing_time, 200)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "Storage", "data_storage_duration",
            SourceValue(3 * u.year))
        self.assertLess(avg_loading_editing_writing_time, 200)


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
