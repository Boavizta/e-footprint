from pyvis.network import Network

from efootprint.utils.graph_tools import WIDTH, HEIGHT, set_string_max_width

COLOR_MAP = {
    "ServerBase": "red",
    "Device": "red",
    "Storage": "red",
    "UsagePattern": "blue",
    "UsageJourney": "dodgerblue",
    "UsageJourneyStep": "deepskyblue",
    "EdgeDevice": "red",
    "EdgeComponent": "red",
    "EdgeUsagePattern": "blue",
    "EdgeUsageJourney": "dodgerblue",
    "EdgeFunction": "deepskyblue",
    "JobBase": "palegoldenrod",
    "RecurrentEdgeDeviceNeed": "palegoldenrod",
    "RecurrentEdgeComponentNeed": "lightgoldenrodyellow",
    "Service": "orange",
}

USAGE_PATTERN_VIEW_CLASSES_TO_IGNORE = [
    "System", "Network", "Device", "Country", "JobBase", "RecurrentEdgeDeviceNeed",
    "Storage", "EdgeComponent", "Service", "RecurrentEdgeComponentNeed"]
INFRA_VIEW_CLASSES_TO_IGNORE = [
    "UsagePattern", "EdgeUsagePattern", "Network", "Device", "System", "UsageJourneyStep", "EdgeFunction", "Country",
    "EdgeComponent", "RecurrentEdgeComponentNeed"]


def is_included_in_graph(input_mod_obj, classes_to_ignore):
    from efootprint.all_classes_in_order import ALL_CANONICAL_CLASSES_DICT
    for ignored_class in classes_to_ignore:
        if isinstance(input_mod_obj, ALL_CANONICAL_CLASSES_DICT[ignored_class]):
            return False
    return True


def get_node_color(input_mod_obj):
    from efootprint.all_classes_in_order import ALL_CANONICAL_CLASSES_DICT
    for class_name, color in COLOR_MAP.items():
        if isinstance(input_mod_obj, ALL_CANONICAL_CLASSES_DICT[class_name]):
            return color
    return "gray"


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
    # pointing to the same ModelingObject instance, and their e-footprint ids will be the same in this case, whereas
    # the Python ids will always be different.
    visited_python_ids.add(id(input_mod_obj))
    included_in_graph = is_included_in_graph(input_mod_obj, classes_to_ignore)
    if included_in_graph:
        input_graph.add_node(
            input_mod_obj.id, label=set_string_max_width(f"{input_mod_obj.name}", 20),
            title=set_string_max_width(str(input_mod_obj), 80),
            color=get_node_color(input_mod_obj))

    for mod_obj_attribute in input_mod_obj.mod_obj_attributes:
        if is_included_in_graph(mod_obj_attribute, classes_to_ignore):
            input_graph.add_node(
                mod_obj_attribute.id, label=set_string_max_width(f"{mod_obj_attribute.name}", 20),
                title=set_string_max_width(str(mod_obj_attribute), 80),
                color=get_node_color(mod_obj_attribute))
            if included_in_graph:
                input_graph.add_edge(input_mod_obj.id, mod_obj_attribute.id)
            else:
                recursively_create_link_with_latest_non_ignored_node(
                    input_mod_obj, mod_obj_attribute, input_graph, classes_to_ignore)

        if mod_obj_attribute not in visited_python_ids:
            build_object_relationships_graph(mod_obj_attribute, input_graph, visited_python_ids, classes_to_ignore, width, height)

    return input_graph


def recursively_create_link_with_latest_non_ignored_node(source_obj, new_obj_to_link, input_graph, classes_to_ignore):
    for mod_obj in source_obj.modeling_obj_containers:
        if is_included_in_graph(mod_obj, classes_to_ignore):
            if mod_obj.id != new_obj_to_link.id and mod_obj.id in input_graph.get_nodes():
                input_graph.add_edge(mod_obj.id, new_obj_to_link.id)
        else:
            recursively_create_link_with_latest_non_ignored_node(
                mod_obj, new_obj_to_link, input_graph, classes_to_ignore)
