import json
import gc
import psutil
import logging

from efootprint.api_utils.json_to_system import json_to_system
from tests.performance_tests.generate_big_system import generate_big_system
from efootprint.logger import ch

ch.setLevel(logging.WARNING)

# Load test data
nb_years = 5
system = generate_big_system(
    nb_of_servers_of_each_type=2, nb_of_uj_per_each_server_type=2, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3,
    nb_of_edge_usage_patterns=3, nb_of_edge_processes_per_edge_computer=3, nb_years=nb_years)

with open('big_system.json') as f:
    template_data = json.load(f)

process = psutil.Process()

def get_mem():
    return process.memory_info().rss / 1024 / 1024

print(f'Baseline: {get_mem():.0f} MB')


for i in range(20):
    data = json.loads(json.dumps(template_data))
    system = json_to_system(data)

    del system, data
    gc.collect()

    print(f'Iter {i+1}: {get_mem():.0f} MB')