import os

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
    serverless_server, on_premise_gpu_server, video_streaming, web_application, genai_model,
    video_streaming_job, web_application_job, genai_model_job, manually_written_job, custom_gpu_job, edge_computer,
    edge_usage_pattern, edge_function, edge_usage_journey, edge_storage, edge_process, edge_appliance, edge_workload,
    cpu_component, ram_component, edge_device, ram_need, cpu_need, edge_device_need)
from efootprint.utils.tools import get_init_signature_params
from format_tutorial_md import doc_utils_path, generated_mkdocs_sourcefiles_path


def return_class_str(input_obj):
    obj_to_compute_class_on = input_obj
    if isinstance(input_obj, ContextualModelingObjectAttribute):
        obj_to_compute_class_on = input_obj._value
    return str(obj_to_compute_class_on.__class__).replace("<class '", "").replace("'>", "").split(".")[-1]


def obj_to_md(input_obj, attr_name):
    if attr_name == "name":
        return f"""### name\nA human readable description of the object."""
    elif isinstance(input_obj, ModelingObject):
        obj_class = return_class_str(input_obj)
        return f"### {attr_name}\nAn instance of [{obj_class}]({obj_class}.md)."
    elif isinstance(input_obj, ExplainableQuantity):
        return f"### {attr_name}\n{input_obj.label.capitalize()} in {input_obj.value.units}."
    elif isinstance(input_obj, list):
        if isinstance(input_obj[0], ModelingObject):
            obj_class = return_class_str(input_obj[0])
            return f"### {attr_name}\nA list of [{obj_class}s]({obj_class}.md)."
        else:
            return "this shouldn’t happen"
    elif isinstance(input_obj, EmptyExplainableObject):
        return (f"### {attr_name}\n{input_obj.label.capitalize()}. "
                f"Can be an EmptyExplainableObject in which case the optimum number of instances will be computed,"
                f" or an ExplainableQuantity with a dimensionless value, in which case e-footprint will raise an error "
                f"if the object needs more instances than available.")
    elif isinstance(input_obj, ExplainableHourlyQuantities):
        return f"### {attr_name}\n{input_obj.label.capitalize()}, in hourly timeseries data."
    elif isinstance(input_obj, ExplainableRecurrentQuantities):
        return (f"### {attr_name}\n{input_obj.label.capitalize()}, in typical week of hourly timeseries data, "
                f"starting on Monday at midnight.\n\n"
                f"For example, {input_obj}")

    return f"### {attr_name}\ndescription to be done"


def calc_attr_to_md(input_obj: ExplainableObject, attr_name):
    return_str = f"### {attr_name}"
    calculation_graph_obj = input_obj
    if isinstance(input_obj, ExplainableQuantity):
        return_str += f"  \nExplainableQuantity in {input_obj.value.units}, representing the {input_obj.label.capitalize()}."
    elif isinstance(input_obj, ExplainableHourlyQuantities):
        return_str += f"""  \n{input_obj.label.capitalize()} in {input_obj.unit}."""
    elif isinstance(input_obj, ExplainableObjectDict):
        dict_value = list(input_obj.values())[0]
        dict_key = list(input_obj.keys())[0]
        return_str += f"""  \nDictionary with {dict_key.class_as_simple_str} as keys and 
                        {dict_value.label.capitalize()} as values, in {dict_value.unit}."""
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
    mod_obj_dict = {"class": return_class_str(mod_obj), "modeling_obj_containers": list(
        set([return_class_str(mod_obj) for mod_obj in mod_obj.modeling_obj_containers]))}

    init_sig_params = get_init_signature_params(type(mod_obj))
    mod_obj_dict["params"] = []
    mod_obj_dict["calculated_attrs"] = []

    for key, elt in init_sig_params.items():
        if key != "self":
            # "type": str(elt).replace(f"{key}: ", "")
            mod_obj_dict["params"].append(obj_to_md(getattr(mod_obj, key), key))

    for attr in mod_obj.calculated_attributes:
        calc_attr = getattr(mod_obj, attr)
        mod_obj_dict["calculated_attrs"].append(calc_attr_to_md(calc_attr, attr))

    with open(os.path.join(doc_utils_path, 'obj_template.md'), 'r') as file:
        template = Template(file.read(), trim_blocks=False)
    rendered_file = template.render(obj_dict=mod_obj_dict)

    filename = f"{mod_obj_dict['class']}.md"
    with open(os.path.join(generated_mkdocs_sourcefiles_path, f"{mod_obj_dict['class']}.md"), "w") as file:
        file.write(rendered_file)

    return filename


def generate_object_reference(automatically_update_yaml=False):
    country = usage_pattern.country
    device = usage_pattern.devices[0]

    nav_items = []
    for mod_obj in (
            system, usage_pattern, usage_journey, country, device, network, streaming_step,
            manually_written_job, custom_gpu_job, autoscaling_server, serverless_server, on_premise_gpu_server,
            video_streaming, web_application, genai_model, video_streaming_job, web_application_job, genai_model_job,
            storage, edge_usage_pattern, edge_function, edge_usage_journey, edge_computer, edge_storage, edge_process,
            edge_process.storage_need, edge_process.compute_need, edge_process.ram_need,
            edge_appliance, edge_workload, edge_workload.workload_need, cpu_component, ram_component, edge_device,
            ram_need, cpu_need,
            edge_device_need, edge_computer.ram_component, edge_computer.cpu_component,
            edge_appliance.appliance_component):
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
