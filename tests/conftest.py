from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

# The collector writes what each test crossed, for the comprehension pages (specs/testing.md).
pytest_plugins = ["comprehension_harness.python.collector"]

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True
