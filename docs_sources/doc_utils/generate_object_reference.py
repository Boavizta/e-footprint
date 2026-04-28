import os
from inspect import cleandoc

from jinja2 import Template
import ruamel.yaml

from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_hourly_quantities import ExplainableHourlyQuantities
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from docs_sources.doc_utils.docs_case import (
    system, usage_pattern, usage_journey, network, streaming_step, autoscaling_server, storage,
    serverless_server, on_premise_gpu_server, video_streaming, genai_model,
    video_streaming_job, genai_model_job, manually_written_job, custom_gpu_job, edge_computer,
    edge_usage_pattern, edge_function, edge_usage_journey, edge_storage, edge_process, edge_appliance, edge_workload,
    cpu_component, ram_component, edge_device, ram_need, cpu_need, storage_need, edge_device_need,
    recurrent_server_need, edge_device_group, workload_component)
from efootprint.logger import logger
from efootprint.utils.placeholder_resolver import resolve_placeholders
from efootprint.utils.tools import get_init_signature_params
from format_tutorial_md import doc_utils_path, generated_mkdocs_sourcefiles_path


def _reject_ui(target: str) -> str:
    raise ValueError(
        f"Library description contains forbidden interface-only placeholder {{ui:{target}}}")


def _build_placeholder_handlers(documented_classes: set[str]) -> dict:
    def class_link(target: str) -> str:
        if target in documented_classes:
            return f"[{target}]({target}.md)"
        return f"`{target}`"

    def member_link(target: str) -> str:
        class_name, member = target.split(".", 1)
        if class_name in documented_classes:
            return f"[{class_name}.{member}]({class_name}.md#{member})"
        return f"`{class_name}.{member}`"

    def doc_link(target: str) -> str:
        return f"[{target}]({target}.md)"

    return {
        "class": class_link,
        "param": member_link,
        "calc": member_link,
        "doc": doc_link,
        "ui": _reject_ui,
    }


_PLACEHOLDER_HANDLERS: dict | None = None


def _render(text: str | None) -> str | None:
    if not text:
        return None
    if _PLACEHOLDER_HANDLERS is None:
        raise RuntimeError("Placeholder handlers not initialised")
    return resolve_placeholders(cleandoc(text), _PLACEHOLDER_HANDLERS)


def return_class_str(input_obj):
    obj_to_compute_class_on = input_obj
    if isinstance(input_obj, ContextualModelingObjectAttribute):
        obj_to_compute_class_on = input_obj._value
    return str(obj_to_compute_class_on.__class__).replace("<class '", "").replace("'>", "").split(".")[-1]


def _type_summary(input_obj, attr_name: str) -> str:
    """Short type/unit hint appended after the curated description."""
    def format_label(label: str):
        return label.capitalize()

    if isinstance(input_obj, ModelingObject):
        obj_class = return_class_str(input_obj)
        return f"An instance of [{obj_class}]({obj_class}.md)."
    if isinstance(input_obj, ExplainableQuantity):
        return f"Unit: {input_obj.value.units}."
    if isinstance(input_obj, list) and input_obj and isinstance(input_obj[0], ModelingObject):
        obj_class = return_class_str(input_obj[0])
        return f"A list of [{obj_class}s]({obj_class}.md)."
    if isinstance(input_obj, EmptyExplainableObject):
        return (f"{format_label(input_obj.label)}. Can be an EmptyExplainableObject in which case the optimum "
                f"number of instances will be computed, or an ExplainableQuantity with a dimensionless value, "
                f"in which case e-footprint will raise an error if the object needs more instances than available.")
    if isinstance(input_obj, ExplainableHourlyQuantities):
        return f"{format_label(input_obj.label)}, in hourly timeseries data."
    if isinstance(input_obj, ExplainableRecurrentQuantities):
        return (f"{format_label(input_obj.label)}, in typical week of hourly timeseries data, starting on Monday "
                f"at midnight. For example, {input_obj}")
    if isinstance(input_obj, ExplainableObject) and isinstance(input_obj.value, str):
        return f"For example, {input_obj.value}."
    return ""


def _find_param_description(cls, attr_name):
    for klass in cls.__mro__:
        descriptions = klass.__dict__.get("param_descriptions") or {}
        if attr_name in descriptions:
            return descriptions[attr_name]
    return None


def _format_fixed_value(input_obj: ExplainableObject):
    if isinstance(input_obj, ExplainableQuantity):
        return f"`{input_obj.value:~P}`"
    if input_obj.value is not None:
        return f"`{input_obj.value}`"
    return f"`{input_obj}`"


def obj_to_md(owning_class, input_obj, attr_name, fixed_by_class=None):
    if attr_name == "name":
        return f"### name\nA human readable description of the object."

    description = _render(_find_param_description(owning_class, attr_name))
    type_hint = _type_summary(input_obj, attr_name)

    body_parts = [part for part in (description, type_hint) if part]
    if fixed_by_class is not None:
        body_parts.append(
            f"*Fixed by {fixed_by_class.__name__} to {_format_fixed_value(input_obj)} — not configurable.*")
    body = "\n\n".join(body_parts) if body_parts else "description to be done"
    return f"### {attr_name}\n{body}"


def calc_attr_to_md(owning_class, input_obj: ExplainableObject, attr_name):
    return_str = f"### {attr_name}"

    method = getattr(owning_class, f"update_{attr_name}", None)
    rendered_doc = _render(method.__doc__ if method is not None else None)
    if rendered_doc:
        return_str += f"\n\n{rendered_doc}"

    calculation_graph_obj = input_obj
    if isinstance(input_obj, ExplainableObjectDict):
        dict_value = list(input_obj.values())[0]
        calculation_graph_obj = dict_value

    str_input_obj_for_md = str(input_obj).replace("\n", "  \n")
    return_str += f"  \n  \nExample value: {str_input_obj_for_md}"

    ancestor_md_link_list = [f'[{elt.label}]({return_class_str(elt.modeling_obj_container)}' \
                             f'.md#{elt.attr_name_in_mod_obj_container})'
                             for elt in calculation_graph_obj.direct_ancestors_with_id]
    ancestor_md_links_list_formatted = "  \n- " + "\n- ".join(ancestor_md_link_list)
    return_str += f"  \n  \nDepends directly on:  \n{ancestor_md_links_list_formatted}" \
                  f"  \n\nthrough the following calculations:  \n"

    containing_obj_str = calculation_graph_obj.modeling_obj_container.name.replace(" ", "_")
    calculus_graph_path = os.path.join(generated_mkdocs_sourcefiles_path, "calculus_graphs")
    if not os.path.exists(calculus_graph_path):
        os.makedirs(calculus_graph_path)
    calculus_graph_filepath = os.path.join(calculus_graph_path, f"{containing_obj_str}_{attr_name}.html")
    calculation_graph_obj.calculus_graph_to_file(calculus_graph_filepath)
    calculus_graph_path_depth1 = os.path.join(generated_mkdocs_sourcefiles_path, "calculus_graphs_depth1")
    if not os.path.exists(calculus_graph_path_depth1):
        os.makedirs(calculus_graph_path_depth1)
    calculus_graph_depth1_filepath = os.path.join(
        calculus_graph_path_depth1, f"{containing_obj_str}_{attr_name}_depth1.html")
    calculation_graph_obj.calculus_graph_to_file(
        calculus_graph_depth1_filepath, width="760px", height="300px", max_depth=1)

    md_calculus_graph_link_depth1 = calculus_graph_depth1_filepath.replace(
        os.path.join(generated_mkdocs_sourcefiles_path), "docs_sources/generated_mkdocs_sourcefiles")
    return_str += f'\n--8<-- "{md_calculus_graph_link_depth1}"\n'

    # The relative path starts with .. instead of . because it seems like mkdocs considers md files as html within a folder
    md_calculus_graph_link = calculus_graph_filepath.replace(os.path.join(generated_mkdocs_sourcefiles_path), "..")
    return_str += f"  \nYou can also visit the <a href='{md_calculus_graph_link}' target='_blank'>link " \
                  f"to {calculation_graph_obj.label}’s full calculation graph</a>."

    return return_str


def write_object_reference_file(mod_obj):
    if isinstance(mod_obj, ContextualModelingObjectAttribute):
        mod_obj = mod_obj._value
    cls = type(mod_obj)
    mod_obj_dict = {
        "class": return_class_str(mod_obj),
        "class_description": _render(cls.__doc__),
        "disambiguation": _render(cls.__dict__.get("disambiguation")),
        "pitfalls": _render(cls.__dict__.get("pitfalls")),
        "interactions": _render(cls.__dict__.get("interactions")),
        "modeling_obj_containers": list(
            set([return_class_str(o) for o in mod_obj.modeling_obj_containers])),
    }

    own_init_params = list(get_init_signature_params(cls))
    mod_obj_dict["params"] = []
    mod_obj_dict["calculated_attrs"] = []
    calc_attr_names = set(mod_obj.calculated_attributes)

    for key in own_init_params:
        if key == "self":
            continue
        attr_value = getattr(mod_obj, key, None)
        mod_obj_dict["params"].append(obj_to_md(cls, attr_value, key))

    seen_params = set(own_init_params)
    for parent_cls in cls.__mro__[1:]:
        if parent_cls is object or "__init__" not in parent_cls.__dict__:
            continue
        for key in get_init_signature_params(parent_cls):
            if key in seen_params or key == "self":
                continue
            seen_params.add(key)
            if key in calc_attr_names or not hasattr(mod_obj, key):
                continue
            attr_value = getattr(mod_obj, key)
            if not isinstance(attr_value, ExplainableObject):
                continue
            mod_obj_dict["params"].append(obj_to_md(cls, attr_value, key, fixed_by_class=cls))

    for attr in mod_obj.calculated_attributes:
        calc_attr = getattr(mod_obj, attr)
        if isinstance(calc_attr, dict) and len(calc_attr) == 0:
            # The case for service_total_job_volumes in serverless server for example
            logger.warning(f"Attribute {attr} of {mod_obj_dict['class']} is an empty dict "
                           f"and won't be included in the documentation.")
            continue
        mod_obj_dict["calculated_attrs"].append(calc_attr_to_md(cls, calc_attr, attr))

    with open(os.path.join(doc_utils_path, 'obj_template.md'), 'r') as file:
        template = Template(file.read(), trim_blocks=False)
    rendered_file = template.render(obj_dict=mod_obj_dict)

    filename = f"{mod_obj_dict['class']}.md"
    with open(os.path.join(generated_mkdocs_sourcefiles_path, f"{mod_obj_dict['class']}.md"), "w") as file:
        file.write(rendered_file)

    return filename


def generate_object_reference(automatically_update_yaml=False):
    global _PLACEHOLDER_HANDLERS
    country = usage_pattern.country
    device = usage_pattern.devices[0]

    mod_objs_to_document = (
            system, usage_pattern, usage_journey, country, device, network, streaming_step,
            manually_written_job, custom_gpu_job, autoscaling_server, serverless_server, on_premise_gpu_server,
            video_streaming, genai_model, genai_model.server, video_streaming_job, genai_model_job,
            storage, edge_usage_pattern, edge_function, edge_usage_journey, edge_computer, edge_storage, edge_process,
            recurrent_server_need, edge_process.storage_need, edge_process.compute_need, edge_process.ram_need,
            edge_appliance, edge_workload, edge_workload.workload_need, cpu_component, ram_component, edge_device,
            edge_device_group, workload_component, ram_need, cpu_need, storage_need,
            edge_device_need, edge_computer.ram_component, edge_computer.cpu_component,
            edge_appliance.appliance_component)

    documented_classes = {return_class_str(mod_obj) for mod_obj in mod_objs_to_document}
    _PLACEHOLDER_HANDLERS = _build_placeholder_handlers(documented_classes)

    nav_items = []
    for mod_obj in mod_objs_to_document:
        filename = write_object_reference_file(mod_obj)
        nav_items.append(filename)

    if automatically_update_yaml:
        yaml = ruamel.yaml.YAML()
        # yaml.preserve_quotes = True
        mkdocs_yml_filepath = os.path.join(doc_utils_path, "..", "..", "mkdocs.yml")
        with open(mkdocs_yml_filepath, "r") as fp:
            data = yaml.load(fp)
        for filename in nav_items:
            write_filename = True
            for elt in data["nav"][2]["e-footprint objects reference"]:
                if filename.replace(".md", "") in elt.keys():
                    write_filename = False
            if write_filename:
                data["nav"][2]["e-footprint objects reference"].append({filename.replace(".md", ""): filename})
        with open(mkdocs_yml_filepath, "w") as fp:
            yaml.dump(data, fp)


if __name__ == "__main__":
    generate_object_reference()
