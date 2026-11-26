"""Planned checks of generated example artifacts."""
from comprehension_harness.python.declare import planned_test


@planned_test("executable-modeling-documentation#source-format: `main` exposes explicit conversion, documentation execution and packaged-model regeneration commands")
def test_example_authoring_command_operations():
    pass


@planned_test("executable-modeling-documentation#presentations: Conversion reproduces committed cleared notebooks and output-free readings without executing scenarios")
def test_generated_example_presentations_are_current():
    pass

