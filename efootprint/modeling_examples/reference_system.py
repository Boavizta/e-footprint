"""The canonical mixed web/edge modeling script shared with the documentation."""
from efootprint.narrate import planned


def build_reference_system():
    planned("agent-guidance#canonical-example:mixed-model", "Port docs_case into a deterministic core-only mixed model with editable timeseries, explicit assumptions and connected device-group and workload-component examples.")
    raise NotImplementedError("planned: agent-guidance#canonical-example")


def run_reference_example(output_directory="."):
    planned("agent-guidance#canonical-example:results-and-files", "Use `build_reference_system` to inspect totals and sizing, demonstrate materialization and write single-system and identity-preserving ordered comparison files outside the package.")
    raise NotImplementedError("planned: agent-guidance#canonical-example")


if __name__ == "__main__":
    run_reference_example()
