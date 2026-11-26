"""Planned coverage of documentation example completeness."""
from comprehension_harness.python.declare import planned_test


@planned_test("executable-modeling-documentation#reference-examples: Scenario objects and explicit supplements preserve every currently documented class without duplicate class pages")
def test_scenario_reference_examples_preserve_documented_classes():
    pass


@planned_test("agent-guidance#class-reference: Missing concrete-class examples stop documentation generation before reference pages are written and name every missing class")
def test_missing_documentation_examples_fail_loudly():
    pass


@planned_test("agent-guidance#class-reference: Timeseries lookups print nested form-input field descriptions with resolved links without constructing examples")
def test_timeseries_lookup_fields():
    pass


@planned_test("agent-guidance#executable-doc-examples: Converted how-to examples execute their documented operations against real models")
def test_executable_topic_examples():
    pass
