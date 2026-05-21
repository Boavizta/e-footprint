import inspect

from ecologits.impacts.llm import dag as llm_dag
from ecologits.impacts.video import dag as video_dag
from ecologits.utils.range_value import RangeValue

from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.builders.external_apis.ecologits.ecologits_explainable_quantity import EcoLogitsExplainableQuantity
from efootprint.builders.external_apis.ecologits.ecologits_unit_mapping import ECOLOGITS_UNIT_MAPPING
from efootprint.constants.units import u


ECOLOGITS_LLM_DEPENDENCY_GRAPH = llm_dag._DAG__dependencies
ECOLOGITS_VIDEO_DEPENDENCY_GRAPH = video_dag._DAG__dependencies


def get_formula(dag, task_name: str) -> str:
    task = dag._DAG__tasks.get(task_name)
    task_code = inspect.getsource(task)
    return task_code.split("\"\"\"")[-1].replace("return", task_name + " =").replace("\n    ", "\n")


def mean_value_or_range(value) -> float:
    """Collapse a RangeValue to its mean and cast scalars to float. Used where a definite float is
    required: the LLM model-parameter lookups and the video impacts dict (whose RangeValue nodes,
    downstream of `server_accelerator_power`, must become scalars for JSON and unit attachment)."""
    if isinstance(value, RangeValue):
        return (value.min + value.max) / 2
    return float(value)


def collapse_range(value):
    """Collapse a RangeValue to its mean, leaving non-range values — and their original int/float
    type — untouched. Used for explainability ancestor and extracted values, whose numeric type is
    preserved verbatim in serialization (e.g. integer EcoLogits inputs like batch_size)."""
    if isinstance(value, RangeValue):
        return (value.min + value.max) / 2
    return value


def extract_calculated_attribute_from_impacts_dict(
        modeling_obj, attribute_name: str, dependency_graph: dict, dag, source: Source) -> None:
    """Read one field out of the cached EcoLogits impact dictionary on `modeling_obj`, attach the
    right unit, and wire its EcoLogits formula and ancestors for explainability. Used by every
    auto-generated ``update_<attr>`` method on the LLM and video Job classes."""
    if attribute_name not in modeling_obj.impacts.value:
        raise ValueError(f"Ecologits impacts has no attribute `{attribute_name}`.")
    ancestors = {}
    for ancestor in dependency_graph[attribute_name]:
        if ancestor in modeling_obj.impacts.value and ancestor in ECOLOGITS_UNIT_MAPPING:
            ancestors[ancestor] = collapse_range(modeling_obj.impacts.value[ancestor])
    ecologits_unit = ECOLOGITS_UNIT_MAPPING[attribute_name]
    value = collapse_range(modeling_obj.impacts.value[attribute_name]) * ecologits_unit
    if ecologits_unit == u.kWh and value.magnitude < 0.01:
        value = value.to(u.Wh)
    if ecologits_unit == u.kg and value.magnitude < 0.01:
        value = value.to(u.g)
    setattr(modeling_obj, attribute_name, EcoLogitsExplainableQuantity(
        value,
        f"Ecologits {attribute_name} for {modeling_obj.external_api.model_name}",
        parent=modeling_obj.impacts, operator="extraction",
        ancestors=dict(sorted(ancestors.items())),
        formula=get_formula(dag, attribute_name),
        source=source))


def create_update_method_for_ecologits_attribute(
        attribute_name: str, dependency_graph: dict, dag, source: Source):
    """Factory: returns an `update_<attr>` closure that extracts attribute_name from the modeling
    object's impacts dict via extract_calculated_attribute_from_impacts_dict."""
    def update_method(self):
        extract_calculated_attribute_from_impacts_dict(self, attribute_name, dependency_graph, dag, source)
    update_method.__name__ = f"update_{attribute_name}"
    update_method.__doc__ = (
        f"Extracts the {attribute_name} field from the cached EcoLogits impact dictionary on this job, "
        f"converted into a typed e-footprint quantity.")
    return update_method
