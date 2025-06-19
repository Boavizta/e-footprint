import json

from efootprint.api_utils.system_to_json import system_to_json
from tests.performance_tests.generate_big_system import generate_big_system


def get_values_size(d: dict, key: str):
    """Recursively find all keys and sum their string byte lengths."""
    total = 0
    if isinstance(d, dict):
        for k, v in d.items():
            if k == key:
                if isinstance(v, str):
                    total += len(v.encode('utf-8')) / 1000 # byte size of string
                elif isinstance(v, (dict, list)):
                    total += len(json.dumps(v, separators=(",", ":")).encode('utf-8')) / 1000
            else:
                total += get_values_size(v, key)
    elif isinstance(d, list):
        for item in d:
            total += get_values_size(item, key)

    return total


def get_keys_size(d: dict):
    """Recursively find all keys and sum their string byte lengths."""
    total = 0
    if isinstance(d, dict):
        for k, v in d.items():
            total += len(k.encode('utf-8')) / 1000
            total += get_keys_size(v)

    return total


if __name__ == "__main__":
    system = generate_big_system(
        nb_of_servers_of_each_type=3, nb_of_uj_per_each_server_type=3, nb_of_uj_steps_per_uj=4, nb_of_up_per_uj=3,
        nb_years=5)
    data = system_to_json(system, save_calculated_attributes=True)

    # Step 1: Serialize JSON and get size
    json_str = json.dumps(data, separators=(",", ":"))  # compact encoding
    json_bytes = json_str.encode('utf-8')
    total_json_size = len(json_bytes) / 1000
    with open("big_system_with_calc_attr_compact.json", "w") as file:
        file.write(json.dumps(data, separators=(",", ":")))
    with open("big_system_with_calc_attr_no_compact.json", "w") as file:
        file.write(json.dumps(data))
    with open("big_system_with_calc_attr_no_compact_indent.json", "w") as file:
        file.write(json.dumps(data, indent=4))
    # Step 2: Get compressed_values byte size
    compressed_values_size = get_values_size(data, "compressed_values")
    label_values_size = get_values_size(data, "label")
    api_values_size = get_values_size(data, "api_call_response")
    direct_ancestors_with_id_size = get_values_size(data, "direct_ancestors_with_id")
    direct_children_with_id_size = get_values_size(data, "direct_children_with_id")
    explain_nested_tuples_size = get_values_size(data, "explain_nested_tuples")
    calculus_graph_size = direct_children_with_id_size + direct_ancestors_with_id_size + explain_nested_tuples_size
    keys_size = get_keys_size(data)
    other_values_size = (total_json_size - compressed_values_size - api_values_size - label_values_size -
                         calculus_graph_size - keys_size)

    # Step 3: Compute ratio
    relative_weight_compressed_values = compressed_values_size / total_json_size
    relative_weight_label_values = label_values_size / total_json_size
    relative_weight_api_values = api_values_size / total_json_size
    relative_weight_calculus_graph = calculus_graph_size / total_json_size
    relative_weight_keys = keys_size / total_json_size
    relative_weight_other_values = other_values_size / total_json_size

    # Display
    print(f"Total JSON size (kilobytes): {int(total_json_size)}")
    print(f"Total compressed_values size (kilobytes): {int(compressed_values_size)}")
    print(f"Total label_values size (kilobytes): {int(label_values_size)}")
    print(f"Total API value size (kilobytes): {int(api_values_size)}")
    print(f"Total calculus graph size (kilobytes): {int(calculus_graph_size)}")
    print(f"Total keys size (kilobytes): {int(keys_size)}")
    print(f"Other values size (kilobytes): {int(other_values_size)}")
    print(f"Relative weight compressed values: {relative_weight_compressed_values:.2%}")
    print(f"Relative weight label values: {relative_weight_label_values:.2%}")
    print(f"Relative weight API value size: {relative_weight_api_values:.2%}")
    print(f"Relative weight calculus graph: {relative_weight_calculus_graph:.2%}")
    print(f"Relative weight keys: {relative_weight_keys:.2%}")
    print(f"Relative weight other values: {relative_weight_other_values:.2%}")

