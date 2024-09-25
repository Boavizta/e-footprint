from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject


def handle_model_input_update(old_value_that_gets_updated: ExplainableObject):
    for child_to_update in old_value_that_gets_updated.update_computation_chain:
        child_update_func = child_to_update.update_function

        child_update_func()