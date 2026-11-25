"""Planned command-level acceptance cases for installed modeling guidance."""
from comprehension_harness.python.declare import planned_test
from efootprint.agent_guide.__main__ import main
from efootprint.modeling_examples.reference_system import run_reference_example


@planned_test("agent-guidance#command: An unknown name lists every available lookup, ordered by similarity, without a traceback [unknown-name-helps]")
def test_unknown_lookup():
    pass


@planned_test("agent-guidance#command: `main` answers default, examples, class and topic forms from an installed core-only wheel outside the checkout [core-install-is-enough]")
def test_core_wheel_commands():
    pass


@planned_test("agent-guidance#class-reference: Every modeling class, including abstract canonical classes, renders in-process without constructing a model [every-class-answers]")
def test_every_modeling_class_answers():
    pass


@planned_test("agent-guidance#class-reference: Command and website references agree on descriptions, defaults, allowed values and pitfalls, retaining docstrings for empty calculated attributes [one-text-per-class]")
def test_shared_class_reference():
    pass


@planned_test("agent-guidance#class-reference: Missing concrete-class examples stop documentation generation before pages are written and name every missing class")
def test_missing_documentation_examples_fail_loudly():
    pass


@planned_test("agent-guidance#canonical-topics: Each topic renders in-process with matching command and website text after link presentation is normalized [one-text-per-topic]")
def test_shared_topic_text():
    pass


@planned_test("agent-guidance#canonical-example: `run_reference_example` runs as printed and produces loadable model files [examples-run]")
def test_executable_guide_examples():
    pass


@planned_test("agent-guidance#guide-assembly: The guide retains the canonical sections and executable source verbatim apart from presentation [one-text-per-explanation]")
def test_canonical_guide_sections():
    pass


@planned_test("agent-guidance#guide-assembly: Website and command guides contain the same assembled text apart from link presentation [one-guide]")
def test_shared_guide_text():
    pass


@planned_test("agent-guidance#guide-assembly: Emitted lookup commands target registered classes or topics [references-resolve]")
def test_emitted_lookups():
    pass


@planned_test("agent-guidance#example-discovery: Every packaged example appears with a description and existing absolute script and JSON paths [every-example-listed]")
def test_example_catalogue():
    pass


@planned_test("agent-guidance#trial-errors: A fresh process builds and exports a non-cloud model without logging the BoaviztaCloudServer import [quiet-build]")
def test_quiet_non_cloud_build():
    pass


@planned_test("agent-guidance#entry-pointers: README URLs are absolute and repository destinations match tracked files [readme-links-resolve]")
def test_readme_links():
    pass
