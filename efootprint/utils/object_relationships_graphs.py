from pyvis.network import Network

from efootprint.utils.graph_tools import WIDTH, HEIGHT, set_string_max_width

COLOR_MAP = {
    "Server": "red",
    "BoaviztaCloudServer": "red",
    "GPUServer": "red",
    "Device": "red",
    "Storage": "red",
    "UsagePattern": "blue",
    "UsageJourney": "dodgerblue",
    "UsageJourneyStep": "deepskyblue",
    "Job": "palegoldenrod",
    "VideoStreamingJob": "palegoldenrod",
    "GenAIJob": "palegoldenrod",
    "WebApplicationJob": "palegoldenrod",
    "VideoStreaming": "orange",
    "GenAIModel": "orange",
    "WebApplication": "orange",
}

USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE = [
    "System", "Network", "Device", "Country", "Job", "Storage", "VideoStreaming", "GenAIModel", "WebApplication",
    "VideoStreamingJob", "GenAIJob", "WebApplicationJob"]
INFRA_VIEW_CLASSES_TO_IGNORE = [
    "UsagePattern", "Network", "Device", "System", "UsageJourney", "UsageJourneyStep", "Country"]


def build_object_relationships_graph(
        input_mod_obj, input_graph=None, visited_python_ids=None, classes_to_ignore=None, width=WIDTH, height=HEIGHT,
        notebook=False):
    cdn_resources = "local"
    if notebook:
        cdn_resources = "in_line"
    if classes_to_ignore is None:
        classes_to_ignore = ["System"]
    if input_graph is None:
        input_graph = Network(notebook=notebook, width=width, height=height, cdn_resources=cdn_resources)
    if visited_python_ids is None:
        visited_python_ids = set()

    if id(input_mod_obj) in visited_python_ids:
        return input_graph
    # Python ids are used to track visited objects because there can be multiple ContextualModelingObjectAttributes
    # pointing to the same ModelingObject instance, and their ids will be the same in this case, whereas the Python ids
    # will always be different.
    visited_python_ids.add(id(input_mod_obj))

    input_mod_obj_type = input_mod_obj.class_as_simple_str
    if input_mod_obj_type not in classes_to_ignore:
        input_graph.add_node(
            input_mod_obj.id, label=set_string_max_width(f"{input_mod_obj.name}", 20),
            title=set_string_max_width(str(input_mod_obj), 80),
            color=COLOR_MAP.get(input_mod_obj_type, "gray"))

    for mod_obj_attribute in input_mod_obj.mod_obj_attributes:
        mod_obj_attribute_type = mod_obj_attribute.class_as_simple_str
        if mod_obj_attribute_type not in classes_to_ignore:
            input_graph.add_node(
                mod_obj_attribute.id, label=set_string_max_width(f"{mod_obj_attribute.name}", 20),
                title=set_string_max_width(str(mod_obj_attribute), 80),
                color=COLOR_MAP.get(mod_obj_attribute_type, "gray"))
            if input_mod_obj_type not in classes_to_ignore:
                input_graph.add_edge(input_mod_obj.id, mod_obj_attribute.id)
            else:
                recursively_create_link_with_latest_non_ignored_node(
                    input_mod_obj, mod_obj_attribute, input_graph, classes_to_ignore)

        if mod_obj_attribute not in visited_python_ids:
            build_object_relationships_graph(mod_obj_attribute, input_graph, visited_python_ids, classes_to_ignore, width, height)

    return input_graph


def recursively_create_link_with_latest_non_ignored_node(source_obj, new_obj_to_link, input_graph, classes_to_ignore):
    for mod_obj in source_obj.modeling_obj_containers:
        if mod_obj.class_as_simple_str not in classes_to_ignore:
            if mod_obj.id != new_obj_to_link.id and mod_obj.id in input_graph.get_nodes():
                input_graph.add_edge(mod_obj.id, new_obj_to_link.id)
        else:
            recursively_create_link_with_latest_non_ignored_node(
                mod_obj, new_obj_to_link, input_graph, classes_to_ignore)
