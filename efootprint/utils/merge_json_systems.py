import hashlib
from copy import deepcopy

import efootprint
from efootprint.all_classes_in_order import ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT
from efootprint.api_utils.json_to_system import upgrade_system_dict_to_current_version


def merge_json_systems(system_dicts, merged_system_name="Merged system"):
    """Merge e-footprint system JSON dicts (as produced by system_to_json) into a single merged system dict.

    The resulting dict contains one System entry whose usage_patterns and edge_usage_patterns are the
    concatenation of those from the input systems. Ids that collide across input systems are renamed by
    suffixing them with `-X`, where X is the index of the system in the input list; every colliding copy
    is suffixed (including the one from system 0). Input dicts whose `efootprint_version` is older than
    the currently installed efootprint are upgraded before merging. Top-level keys that are not known
    e-footprint class names are ignored (neither scanned for id collisions nor carried to the output).
    """
    if not system_dicts:
        raise ValueError("merge_json_systems requires at least one input system dict.")

    efootprint_class_keys = set(ALL_CONCRETE_EFOOTPRINT_CLASSES_DICT.keys())
    upgraded_systems = [upgrade_system_dict_to_current_version(deepcopy(sd)) for sd in system_dicts]
    for idx, sd in enumerate(upgraded_systems):
        if not sd.get("System"):
            raise ValueError(f"System dict at index {idx} has no 'System' class entry; cannot merge.")

    id_occurrences = {}
    per_system_ids = [_all_ids_in_system(sd, efootprint_class_keys) for sd in upgraded_systems]
    for idx, ids in enumerate(per_system_ids):
        for obj_id in ids:
            id_occurrences.setdefault(obj_id, []).append(idx)
    colliding_ids = {obj_id for obj_id, indexes in id_occurrences.items() if len(indexes) > 1}

    renamed_systems = []
    for idx, sd in enumerate(upgraded_systems):
        rename_map = {obj_id: f"{obj_id}-{idx}" for obj_id in per_system_ids[idx] if obj_id in colliding_ids}
        renamed_systems.append(_apply_rename_map(sd, rename_map, efootprint_class_keys))

    output_dict = {"efootprint_version": efootprint.__version__}
    merged_usage_patterns = []
    merged_edge_usage_patterns = []
    for sd in renamed_systems:
        for system_obj in sd.get("System", {}).values():
            merged_usage_patterns.extend(system_obj.get("usage_patterns", []))
            merged_edge_usage_patterns.extend(system_obj.get("edge_usage_patterns", []))
        for class_key, class_dict in sd.items():
            if class_key == "System" or class_key not in efootprint_class_keys:
                continue
            output_dict.setdefault(class_key, {}).update(class_dict)

    merged_system_id = _derive_merged_system_id(system_dicts)
    output_dict["System"] = {
        merged_system_id: {
            "name": merged_system_name,
            "id": merged_system_id,
            "usage_patterns": merged_usage_patterns,
            "edge_usage_patterns": merged_edge_usage_patterns,
        }
    }
    return output_dict


def _all_ids_in_system(system_dict, efootprint_class_keys):
    ids = set()
    for class_key, class_dict in system_dict.items():
        if class_key not in efootprint_class_keys or not isinstance(class_dict, dict):
            continue
        ids.update(class_dict.keys())
    return ids


def _apply_rename_map(system_dict, rename_map, efootprint_class_keys):
    if not rename_map:
        return deepcopy(system_dict)
    new_dict = {}
    for class_key, class_dict in system_dict.items():
        if class_key not in efootprint_class_keys or not isinstance(class_dict, dict):
            new_dict[class_key] = deepcopy(class_dict)
            continue
        new_class_dict = {}
        for obj_id, obj_dict in class_dict.items():
            new_obj_id = rename_map.get(obj_id, obj_id)
            new_class_dict[new_obj_id] = _rewrite_refs(obj_dict, rename_map)
        new_dict[class_key] = new_class_dict
    return new_dict


def _rewrite_refs(value, rename_map):
    if isinstance(value, dict):
        return {
            (rename_map.get(k, k) if isinstance(k, str) else k): _rewrite_refs(v, rename_map)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_rewrite_refs(item, rename_map) for item in value]
    if isinstance(value, str):
        return rename_map.get(value, value)
    return value


def _derive_merged_system_id(system_dicts):
    original_ids = []
    for sd in system_dicts:
        original_ids.extend((sd.get("System") or {}).keys())
    hash_suffix = hashlib.md5("|".join(original_ids).encode()).hexdigest()[:6]
    return f"merged-system-{hash_suffix}"


if __name__ == "__main__":
    import json
    import os

    root_path = os.path.dirname(os.path.abspath(__file__))

    input_json_files = [
        "LEGACY Arrival Cell - 10 Cells - Legacy.e-f.json", "SDP Arrival Cell - 10 Cells - SDP.e-f.json"]

    system_dicts = []

    for json_file in input_json_files:
        with open(os.path.join(root_path, json_file), "r") as f:
            system_dicts.append(json.load(f))

    merged_dict = merge_json_systems(system_dicts)

    with open(os.path.join(root_path, "merged_system.json"), "w") as f:
        json.dump(merged_dict, f, indent=4)
