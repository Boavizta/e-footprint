"""Compare authored inputs without changing explainable arithmetic equality."""

from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject


def input_values_match(first, second):
    """Match presence and timeseries authoring state as well as the underlying value."""
    if isinstance(first, EmptyExplainableObject) != isinstance(second, EmptyExplainableObject):
        return False
    if hasattr(first, "form_inputs") or hasattr(second, "form_inputs"):
        if type(first) is not type(second) or first.form_inputs != second.form_inputs:
            return False
    return first == second
