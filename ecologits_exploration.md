from pprint import pprint
pprint(res)
{'batch_size': 64,
 'datacenter_pue': 1.2,
 'datacenter_wue': 0.569,
 'generation_latency': 1290.0046641974661,
 'gpu_embodied_adpe': 0.0051,
 'gpu_embodied_gwp': 164,
 'gpu_embodied_pe': 1828,
 'gpu_energy': 0.0011569191456103042,
 'gpu_energy_alpha': 1.1665273170451914e-06,
 'gpu_energy_beta': -0.011205921025579175,
 'gpu_energy_gamma': 4.052928146734005e-05,
 'gpu_memory': 80,
 'gpu_required_count': 16,
 'if_electricity_mix_adpe': 9.855e-08,
 'if_electricity_mix_gwp': 0.38355,
 'if_electricity_mix_pe': 9.6884,
 'if_electricity_mix_wue': 3.1321,
 'latency_alpha': 0.0006785088094353663,
 'latency_beta': 0.0003119310311688259,
 'latency_gamma': 0.019473717579473387,
 'model_active_parameter_count': 132,
 'model_quantization_bits': 16,
 'model_required_memory': 1056.0,
 'model_total_parameter_count': 440,
 'output_token_count': 10000,
 'request_embodied_adpe': 1.7504264836625838e-07,
 'request_embodied_gwp': 0.0029878263153461627,
 'request_embodied_pe': 0.03605844468195289,
 'request_energy': 0.03833790589818617,
 'request_latency': inf,
 'request_usage_adpe': 3.778200626266247e-09,
 'request_usage_gwp': 0.014704503807249306,
 'request_usage_pe': 0.37143296750398686,
 'request_usage_wcf': 0.1659080545325186,
 'server_embodied_adpe': 0.37,
 'server_embodied_gwp': 5700,
 'server_embodied_pe': 70000,
 'server_energy': 0.013437548585390272,
 'server_gpu_count': 8,
 'server_gpu_embodied_adpe': 0.8216,
 'server_gpu_embodied_gwp': 14024.0,
 'server_gpu_embodied_pe': 169248.0,
 'server_lifetime': 94608000,
 'server_power': 1.2}
pprint(results)
{'request_embodied_adpe': RangeValue(min=9.402292466222344e-08, max=1.7504264836625838e-07),
 'request_embodied_gwp': RangeValue(min=0.0016048898435528502, max=0.0029878263153461627),
 'request_embodied_pe': RangeValue(min=0.019368539378325212, max=0.03605844468195289),
 'request_energy': RangeValue(min=0.021253491958404765, max=0.03833790589818617),
 'request_usage_adpe': RangeValue(min=2.0945316325007897e-09, max=3.778200626266247e-09),
 'request_usage_gwp': RangeValue(min=0.008151776840646148, max=0.014704503807249306),
 'request_usage_pe': RangeValue(min=0.20591233148980873, max=0.37143296750398686),
 'request_usage_wcf': RangeValue(min=0.09197491151983578, max=0.1659080545325186)}
from ecologits.impacts.llm import dag
dag
<ecologits.impacts.dag.DAG object at 0x1045f3770>

dag._DAG__dependencies
{'gpu_energy': {'batch_size', 'output_token_count', 'gpu_energy_beta', 'model_active_parameter_count', 'gpu_energy_gamma', 'gpu_energy_alpha'}, 'generation_latency': {'batch_size', 'latency_alpha', 'output_token_count', 'latency_gamma', 'request_latency', 'model_active_parameter_count', 'latency_beta'}, 'model_required_memory': {'model_total_parameter_count', 'model_quantization_bits'}, 'gpu_required_count': {'gpu_memory', 'model_required_memory'}, 'server_energy': {'batch_size', 'server_gpu_count', 'generation_latency', 'gpu_required_count', 'server_power'}, 'request_energy': {'gpu_required_count', 'server_energy', 'gpu_energy', 'datacenter_pue'}, 'request_usage_gwp': {'if_electricity_mix_gwp', 'request_energy'}, 'request_usage_adpe': {'if_electricity_mix_adpe', 'request_energy'}, 'request_usage_pe': {'request_energy', 'if_electricity_mix_pe'}, 'request_usage_wcf': {'if_electricity_mix_wue', 'datacenter_wue', 'request_energy', 'datacenter_pue'}, 'server_gpu_embodied_gwp': {'gpu_required_count', 'gpu_embodied_gwp', 'server_gpu_count', 'server_embodied_gwp'}, 'server_gpu_embodied_adpe': {'gpu_embodied_adpe', 'server_embodied_adpe', 'gpu_required_count', 'server_gpu_count'}, 'server_gpu_embodied_pe': {'server_embodied_pe', 'gpu_embodied_pe', 'gpu_required_count', 'server_gpu_count'}, 'request_embodied_gwp': {'batch_size', 'server_lifetime', 'generation_latency', 'server_gpu_embodied_gwp'}, 'request_embodied_adpe': {'server_gpu_embodied_adpe', 'batch_size', 'server_lifetime', 'generation_latency'}, 'request_embodied_pe': {'batch_size', 'server_gpu_embodied_pe', 'server_lifetime', 'generation_latency'}}
from pprint import pprint
pprint(dag._DAG__dependencies)
{'generation_latency': {'batch_size',
                        'latency_alpha',
                        'latency_beta',
                        'latency_gamma',
                        'model_active_parameter_count',
                        'output_token_count',
                        'request_latency'},
 'gpu_energy': {'batch_size',
                'gpu_energy_alpha',
                'gpu_energy_beta',
                'gpu_energy_gamma',
                'model_active_parameter_count',
                'output_token_count'},
 'gpu_required_count': {'gpu_memory', 'model_required_memory'},
 'model_required_memory': {'model_quantization_bits',
                           'model_total_parameter_count'},
 'request_embodied_adpe': {'batch_size',
                           'generation_latency',
                           'server_gpu_embodied_adpe',
                           'server_lifetime'},
 'request_embodied_gwp': {'batch_size',
                          'generation_latency',
                          'server_gpu_embodied_gwp',
                          'server_lifetime'},
 'request_embodied_pe': {'batch_size',
                         'generation_latency',
                         'server_gpu_embodied_pe',
                         'server_lifetime'},
 'request_energy': {'datacenter_pue',
                    'gpu_energy',
                    'gpu_required_count',
                    'server_energy'},
 'request_usage_adpe': {'if_electricity_mix_adpe', 'request_energy'},
 'request_usage_gwp': {'if_electricity_mix_gwp', 'request_energy'},
 'request_usage_pe': {'request_energy', 'if_electricity_mix_pe'},
 'request_usage_wcf': {'datacenter_pue',
                       'datacenter_wue',
                       'if_electricity_mix_wue',
                       'request_energy'},
 'server_energy': {'batch_size',
                   'generation_latency',
                   'gpu_required_count',
                   'server_gpu_count',
                   'server_power'},
 'server_gpu_embodied_adpe': {'gpu_embodied_adpe',
                              'gpu_required_count',
                              'server_embodied_adpe',
                              'server_gpu_count'},
 'server_gpu_embodied_gwp': {'gpu_embodied_gwp',
                             'gpu_required_count',
                             'server_embodied_gwp',
                             'server_gpu_count'},
 'server_gpu_embodied_pe': {'gpu_embodied_pe',
                            'gpu_required_count',
                            'server_embodied_pe',
                            'server_gpu_count'}}
dag._DAG__tasks["generation_latency"]
<function generation_latency at 0x105c7f4c0>
dag._DAG__tasks["generation_latency"].__code__
<code object generation_latency at 0x105b68830, file "/Users/vinville/dev/ecologits/ecologits/impacts/llm.py", line 65>
import inspect
func = dag._DAG__tasks["generation_latency"]
inspect.getsource(func)
'@dag.asset\ndef generation_latency(\n        model_active_parameter_count: float,\n        output_token_count: float,\n        batch_size: int,\n        latency_alpha: float,\n        latency_beta: float,\n        latency_gamma: float,\n        request_latency: float\n) -> ValueOrRange:\n    """\n    Compute the token generation latency in seconds.\n\n    Args:\n        model_active_parameter_count: Number of active parameters of the model (in billion).\n        output_token_count: Number of generated tokens.\n        batch_size: Number of requests handled concurrently by the server.\n        latency_alpha: Alpha coefficient of the latency regression.\n        latency_beta: Beta coefficient of the latency regression.\n        latency_gamma: Gamma coefficient of the latency regression.\n\n    Returns:\n        The token generation latency in seconds.\n    """\n    latency_per_token = latency_alpha * model_active_parameter_count + latency_beta * batch_size + latency_gamma\n    gpu_latency = output_token_count * latency_per_token\n    if request_latency < gpu_latency:\n        return request_latency\n    return gpu_latency\n'
print(inspect.getsource(func))
@dag.asset
def generation_latency(
        model_active_parameter_count: float,
        output_token_count: float,
        batch_size: int,
        latency_alpha: float,
        latency_beta: float,
        latency_gamma: float,
        request_latency: float
) -> ValueOrRange:
    """
    Compute the token generation latency in seconds.
    Args:
        model_active_parameter_count: Number of active parameters of the model (in billion).
        output_token_count: Number of generated tokens.
        batch_size: Number of requests handled concurrently by the server.
        latency_alpha: Alpha coefficient of the latency regression.
        latency_beta: Beta coefficient of the latency regression.
        latency_gamma: Gamma coefficient of the latency regression.
    Returns:
        The token generation latency in seconds.
    """
    latency_per_token = latency_alpha * model_active_parameter_count + latency_beta * batch_size + latency_gamma
    gpu_latency = output_token_count * latency_per_token
    if request_latency < gpu_latency:
        return request_latency
    return gpu_latency
func.__doc__
'\n    Compute the token generation latency in seconds.\n\n    Args:\n        model_active_parameter_count: Number of active parameters of the model (in billion).\n        output_token_count: Number of generated tokens.\n        batch_size: Number of requests handled concurrently by the server.\n        latency_alpha: Alpha coefficient of the latency regression.\n        latency_beta: Beta coefficient of the latency regression.\n        latency_gamma: Gamma coefficient of the latency regression.\n\n    Returns:\n        The token generation latency in seconds.\n    '
