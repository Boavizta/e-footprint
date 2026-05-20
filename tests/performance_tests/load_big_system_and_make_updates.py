from copy import deepcopy
from time import perf_counter

start = perf_counter()
import json
import os

from efootprint.abstract_modeling_classes.source_objects import SourceValue
from efootprint.constants.units import u
from efootprint.logger import logger
from tests.performance_tests.generate_big_system import form_inputs_hourly_starts
from tests.performance_tests.test_big_system_from_and_to_json_performance import root_dir, update_on_system, \
    log_number_of_live_objects

logger.info(f"Finished importing modules in {round((perf_counter() - start), 3)} seconds")

# System loaded from json edition benchmarking
with open(os.path.join(root_dir, "big_system_with_calc_attr.json"), "r") as file:
    system_dict = json.load(file)

log_number_of_live_objects()
nb_system_loadings = 10
update_on_system(
    nb_system_loadings, deepcopy(system_dict), "UsagePattern", "hourly_usage_journey_starts",
    form_inputs_hourly_starts(nb_years=3))

log_number_of_live_objects()

update_on_system(
    nb_system_loadings, deepcopy(system_dict), "Storage", "data_storage_duration", SourceValue(3 * u.year))

log_number_of_live_objects()
