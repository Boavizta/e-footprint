"""Reproduce the parked delta-timeseries encoding size and speed experiment.

Run this script from the e-footprint-interface Poetry environment; see plan.html.
It does not modify input files.
"""

from __future__ import annotations

import argparse
import base64
import copy
import gc
import json
import logging
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

import numpy as np
import orjson
import zstandard as zstd


DELTA_KEY_EXTRA_BYTES = len("delta_compressed_values") - len("compressed_values")


def iter_timeseries_dicts(value):
    """Yield nested dictionaries carrying the current compressed hourly codec."""
    stack = [value]
    while stack:
        candidate = stack.pop()
        if isinstance(candidate, dict):
            if isinstance(candidate.get("compressed_values"), str):
                yield candidate
            stack.extend(candidate.values())
        elif isinstance(candidate, list):
            stack.extend(candidate)


def decode_raw(encoded: str) -> np.ndarray:
    raw = zstd.ZstdDecompressor().decompress(base64.b64decode(encoded))
    if len(raw) % np.dtype(np.float32).itemsize:
        raise ValueError("Compressed timeseries does not contain complete float32 words")
    return np.frombuffer(raw, dtype=np.float32)


def encode_raw(values: np.ndarray) -> str:
    compressed = zstd.ZstdCompressor(level=0).compress(values.astype(np.float32, copy=False).tobytes())
    return base64.b64encode(compressed).decode("ascii")


def encode_delta(values: np.ndarray) -> str:
    bits = values.astype(np.float32, copy=False).view(np.uint32)
    deltas = np.empty_like(bits)
    deltas[0] = bits[0]
    deltas[1:] = bits[1:] - bits[:-1]
    compressed = zstd.ZstdCompressor(level=0).compress(deltas.tobytes())
    return base64.b64encode(compressed).decode("ascii")


def decode_delta(encoded: str) -> np.ndarray:
    raw = zstd.ZstdDecompressor().decompress(base64.b64decode(encoded))
    if len(raw) % np.dtype(np.uint32).itemsize:
        raise ValueError("Delta timeseries does not contain complete uint32 words")
    deltas = np.frombuffer(raw, dtype=np.uint32)
    return np.cumsum(deltas, dtype=np.uint32).view(np.float32)


def normalized_payload(path: Path) -> dict:
    """Upgrade and fully materialize a model through the production import path."""
    from model_builder.domain.interfaces.system_repository import ISystemRepository
    from model_builder.domain.services.system_import_service import SystemImportService

    raw = json.loads(path.read_text())
    upgraded = ISystemRepository.upgrade_system_data(copy.deepcopy(raw))
    return SystemImportService(float("inf")).import_system(upgraded)


def analyze_payload(data: dict) -> dict:
    current_size = len(orjson.dumps(data))
    current_strings = 0
    universal_strings = 0
    adaptive_strings = 0
    array_count = 0
    adaptive_delta_count = 0

    for timeseries in iter_timeseries_dicts(data):
        current = timeseries["compressed_values"]
        values = decode_raw(current)
        delta = encode_delta(values)
        reconstructed = decode_delta(delta)
        if not np.array_equal(reconstructed.view(np.uint32), values.view(np.uint32)):
            raise AssertionError("Delta round trip was not bit-exact")

        current_length = len(current)
        delta_length = len(delta) + DELTA_KEY_EXTRA_BYTES
        current_strings += current_length
        universal_strings += delta_length
        adaptive_strings += min(current_length, delta_length)
        adaptive_delta_count += delta_length < current_length
        array_count += 1

    return {
        "current": current_size,
        "universal": current_size - current_strings + universal_strings,
        "adaptive": current_size - current_strings + adaptive_strings,
        "arrays": array_count,
        "adaptive_delta_arrays": adaptive_delta_count,
    }


def timed(function, repetitions: int) -> float:
    for _ in range(2):
        function()
    durations = []
    for _ in range(repetitions):
        gc.collect()
        started = perf_counter()
        function()
        durations.append(1000 * (perf_counter() - started))
    return median(durations)


def benchmark_timings(data: dict, repetitions: int) -> dict:
    arrays = [decode_raw(item["compressed_values"]).copy() for item in iter_timeseries_dicts(data)]
    raw_strings = [encode_raw(values) for values in arrays]
    delta_strings = [encode_delta(values) for values in arrays]

    def encode_all_raw():
        return [encode_raw(values) for values in arrays]

    def encode_all_delta():
        return [encode_delta(values) for values in arrays]

    def decode_all_raw():
        return [decode_raw(value) for value in raw_strings]

    def decode_all_delta():
        return [decode_delta(value) for value in delta_strings]

    delta_data = copy.deepcopy(data)
    for item, encoded in zip(iter_timeseries_dicts(delta_data), delta_strings):
        del item["compressed_values"]
        item["delta_compressed_values"] = encoded
    current_json = orjson.dumps(data)
    delta_json = orjson.dumps(delta_data)

    return {
        "codec write current": timed(encode_all_raw, repetitions),
        "codec write delta": timed(encode_all_delta, repetitions),
        "codec read current": timed(decode_all_raw, repetitions),
        "codec read delta": timed(decode_all_delta, repetitions),
        "JSON write current": timed(lambda: orjson.dumps(data), repetitions),
        "JSON write delta": timed(lambda: orjson.dumps(delta_data), repetitions),
        "JSON read current": timed(lambda: orjson.loads(current_json), repetitions),
        "JSON read delta": timed(lambda: orjson.loads(delta_json), repetitions),
    }


def mb(value: int) -> str:
    return f"{value / 1_000_000:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, help="Directory containing representative JSON models")
    parser.add_argument("--stress-json", type=Path, help="Optional already-materialized stress payload")
    parser.add_argument("--timings", action="store_true", help="Benchmark codecs against --stress-json")
    parser.add_argument("--repetitions", type=int, default=9)
    parser.add_argument("--show-names", action="store_true", help="Print private filenames instead of model numbers")
    parser.add_argument(
        "--interface-root", type=Path, default=Path.cwd(),
        help="e-footprint-interface checkout (defaults to the current directory)",
    )
    args = parser.parse_args()
    if args.timings and args.stress_json is None:
        parser.error("--timings requires --stress-json")
    interface_root = args.interface_root.resolve()
    if not (interface_root / "model_builder").is_dir():
        parser.error(f"No model_builder package found under --interface-root {interface_root}")
    sys.path.insert(0, str(interface_root))

    logging.disable(logging.CRITICAL)
    paths = sorted(args.corpus.glob("*.json"))
    if not paths:
        parser.error(f"No JSON files found in {args.corpus}")

    print("model\tcurrent_MB\tuniversal_delta_MB\tuniversal_gain\tadaptive_MB\tadaptive_gain\tdelta_arrays")
    results = []
    for index, path in enumerate(paths, start=1):
        result = analyze_payload(normalized_payload(path))
        results.append(result)
        label = path.name if args.show_names else f"model-{index:02d}"
        universal_gain = 1 - result["universal"] / result["current"]
        adaptive_gain = 1 - result["adaptive"] / result["current"]
        print(
            f"{label}\t{mb(result['current'])}\t{mb(result['universal'])}\t{universal_gain:.2%}\t"
            f"{mb(result['adaptive'])}\t{adaptive_gain:.2%}\t"
            f"{result['adaptive_delta_arrays']}/{result['arrays']}"
        )

    totals = {key: sum(result[key] for result in results) for key in results[0]}
    print(
        f"TOTAL\t{mb(totals['current'])}\t{mb(totals['universal'])}\t"
        f"{1 - totals['universal'] / totals['current']:.2%}\t{mb(totals['adaptive'])}\t"
        f"{1 - totals['adaptive'] / totals['current']:.2%}\t"
        f"{totals['adaptive_delta_arrays']}/{totals['arrays']}"
    )

    if args.stress_json is not None:
        stress_data = json.loads(args.stress_json.read_text())
        stress = analyze_payload(stress_data)
        print("\nstress payload")
        print(
            f"current={mb(stress['current'])} MB universal_delta={mb(stress['universal'])} MB "
            f"gain={1 - stress['universal'] / stress['current']:.2%} arrays={stress['arrays']}"
        )
        if args.timings:
            print("\nmedian timings (ms)")
            for name, duration in benchmark_timings(stress_data, args.repetitions).items():
                print(f"{name}: {duration:.2f}")


if __name__ == "__main__":
    main()
