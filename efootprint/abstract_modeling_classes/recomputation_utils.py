from typing import List

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


def launch_attributes_computation_chain(attributes_computation_chain: List[ExplainableObject]):
    for child_to_update in attributes_computation_chain:
        child_update_func = child_to_update.update_function

        child_update_func()
