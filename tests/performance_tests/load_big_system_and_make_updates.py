import gc
from copy import deepcopy
from time import time, sleep

from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

start = time()
import json
import os

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.builders.time_builders import create_random_source_hourly_values
from efootprint.logger import logger
from tests.performance_tests.test_big_system_from_and_to_json_performance import root_dir, update_on_system
logger.info(f"Finished importing modules in {round((time() - start), 3)} seconds")


# System loaded from json edition benchmarking
with open(os.path.join(root_dir, "big_system_with_calc_attr.json"), "r") as file:
    system_dict = json.load(file)

nb_system_loadings = 10
update_on_system(
    nb_system_loadings, deepcopy(system_dict), "UsagePattern", "hourly_usage_journey_starts",
    create_random_source_hourly_values(timespan=3 * u.year))

update_on_system(
    nb_system_loadings, deepcopy(system_dict), "Storage", "data_storage_duration", SourceValue(3 * u.year))

sleep(2)
gc.collect()
logger.info(f"After GC: {sum(1 for o in gc.get_objects() if isinstance(o, ModelingObject))}")
