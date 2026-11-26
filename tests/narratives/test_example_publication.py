"""The intended documentation flow, recorded when executable examples are implemented."""
from comprehension_harness.python.declare import canonical, narrative, planned_test


@narrative("A modeling scenario becomes published examples", scope="doc")
class TestExamplePublication:
    """E-commerce demonstrates the generation pattern to follow when adding or editing a scenario:
    one ordered source supplies the notebook, reading, packaged model and executed documentation."""

    @canonical(steps=("example-publication:read", "example-publication:select", "example-publication:convert",
                      "example-publication:baseline", "example-publication:publish"))
    @planned_test("executable-modeling-documentation#generation-narrative: E-commerce conversion, model regeneration and documentation publication derive their artifacts from one source")
    def test_ecommerce_source_becomes_published_examples(self):
        pass
