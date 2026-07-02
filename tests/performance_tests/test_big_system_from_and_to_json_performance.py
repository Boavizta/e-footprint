from time import perf_counter, sleep
from unittest import TestCase
import gc
from collections import Counter

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.object_linked_to_modeling_obj import ObjectLinkedToModelingObj
from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.api_utils.json_to_system import json_to_system
from efootprint.api_utils.system_to_json import system_to_json
from efootprint.logger import logger
from efootprint.constants.units import u
from tests.performance_tests.generate_big_system import (
    BIG_SYSTEM_STANDARD_PARAMS, generate_big_system, form_inputs_hourly_starts, root_dir)


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
    start = perf_counter()
    json_to_system_duration = 0
    system_to_json_duration = 0
    for i in range(nb_system_loadings):
        json_to_system_start = perf_counter()
        class_obj_dict_computed, flat_obj_dict_computed, _ = json_to_system(
            system_dict, launch_system_computations=False)
        json_to_system_duration += perf_counter() - json_to_system_start
        first_object = next(iter(class_obj_dict_computed[object_type].values()))
        first_object.__setattr__(attr_to_change, new_value)
        system_to_json_start = perf_counter()
        system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                       output_filepath=None)
        system_to_json_duration += perf_counter() - system_to_json_start
    avg_loading_editing_writing_time = round(1000 * (perf_counter() - start) / nb_system_loadings, 1)
    avg_json_to_system_time = round(1000 * json_to_system_duration / nb_system_loadings, 1)
    avg_json_to_system_time_percentage = round(100 * avg_json_to_system_time / avg_loading_editing_writing_time, 1)
    avg_system_to_json_time = round(1000 * system_to_json_duration / nb_system_loadings, 1)
    avg_system_to_json_time_percentage = round(100 * avg_system_to_json_time / avg_loading_editing_writing_time, 1)
    logger.info(
        f"deserializing system then editing {attr_to_change} in first {object_type} then reserializing system took\n"
        f"{avg_loading_editing_writing_time} ms on average for {nb_system_loadings} times, including "
        f"{avg_system_to_json_time} ms of system_to_json ({avg_system_to_json_time_percentage}%) "
        f"and {avg_json_to_system_time} ms of json_to_system ({avg_json_to_system_time_percentage}%) ")

    return avg_loading_editing_writing_time


class TestBigSystemFromAndToJsonPerformance(TestCase):
    def test_big_system_from_and_to_json_performance(self):
        big_system = generate_big_system(**BIG_SYSTEM_STANDARD_PARAMS)
        start = perf_counter()
        system_dict = system_to_json(big_system, save_calculated_attributes=True, output_filepath=None)
        logger.info(f"Initial serialization of system to dict took {round((perf_counter() - start), 3)} seconds")

        start = perf_counter()
        nb_system_loadings = 2
        for i in range(nb_system_loadings):
            class_obj_dict_computed, flat_obj_dict_computed, _ = json_to_system(
                system_dict, launch_system_computations=False)
        avg_loading_time = (perf_counter() - start) / nb_system_loadings
        logger.info(
            f"deserializing system took {round(avg_loading_time, 3)} seconds on average for {nb_system_loadings} times")
        self.assertLess(avg_loading_time, 0.2)

        start = perf_counter()
        for i in range(nb_system_loadings):
            system_to_json(next(iter(class_obj_dict_computed["System"].values())), save_calculated_attributes=True,
                                 output_filepath=None)
        avg_writing_time = (perf_counter() - start) / nb_system_loadings
        logger.info(
            f"serializing system took {round(avg_writing_time, 3)} seconds on average for {nb_system_loadings} times")
        self.assertLess(avg_writing_time, 0.2)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "UsagePattern","hourly_usage_journey_starts",
            form_inputs_hourly_starts(nb_years=5, initial_volume=2000))
        self.assertLess(avg_loading_editing_writing_time, 700)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "EdgeUsagePattern", "hourly_edge_usage_journey_starts",
            form_inputs_hourly_starts(nb_years=5, initial_volume=2000))
        self.assertLess(avg_loading_editing_writing_time, 700)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "Job", "data_transferred",
            SourceValue(100 * u.MB))
        self.assertLess(avg_loading_editing_writing_time, 700)

        avg_loading_editing_writing_time = update_on_system(
            nb_system_loadings, system_dict, "Storage", "data_storage_duration",
            SourceValue(3 * u.year))
        self.assertLess(avg_loading_editing_writing_time, 700)
