from copy import deepcopy, copy

import numpy as np
from pint import Quantity
from efootprint.abstract_modeling_classes.explainable_recurrent_quantities import ExplainableRecurrentQuantities
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source, ExplainableObject


@ExplainableObject.register_subclass(lambda d: "form_inputs" in d and "constant_value" in d["form_inputs"]
                                               and "constant_unit" in d["form_inputs"])
class ExplainableRecurrentQuantitiesFromConstant(ExplainableRecurrentQuantities):
    """
    ExplainableRecurrentQuantities generated from a single constant value repeated 168 times.

    Stores the constant value in JSON so it can be edited later.
    Computes the 168-element array lazily when .value is first accessed.
    """

    @classmethod
    def from_json_dict(cls, d):
        source = Source.from_json_dict(d.get("source")) if d.get("source") else None

        return cls(form_inputs=d["form_inputs"], label=d["label"], source=source)

    def __init__(self, form_inputs: dict, label: str = "no label",
                 left_parent=None, right_parent=None, operator: str = None, source: Source = None):
        """
        Initialize with a constant value that will be repeated 168 times.

        Args:
            form_inputs dict containing:
            - constant_value: The constant numeric value
            - constant_unit: The pint unit for this value
            - label: Optional label
            - source: Optional source information
        """
        self.form_inputs = form_inputs

        # Don't compute value yet - will be computed lazily
        # Initialize parent with empty dict value, will be computed in property
        super().__init__(
            value=self._compute_recurrent_values(), label=label, left_parent=left_parent,
            right_parent=right_parent, operator=operator, source=source
        )


    def _compute_recurrent_values(self) -> Quantity:
        """Generate 168-element array (7 days * 24 hours) with constant value."""
        recurrent_array = np.array([float(self.form_inputs["constant_value"])] * 168, dtype=np.float32)
        return Quantity(recurrent_array, self.form_inputs["constant_unit"])

    def to_json(self, save_calculated_attributes=False):
        """Save constant value to JSON (no need to save recurring_values since constant is already compressed)."""
        output_dict = {"form_inputs": self.form_inputs}

        # Add parent class metadata (label, source, etc.)
        output_dict.update(super(ExplainableRecurrentQuantities, self).to_json(save_calculated_attributes))

        return output_dict

    def __copy__(self):
        return ExplainableRecurrentQuantitiesFromConstant(
            form_inputs=deepcopy(self.form_inputs), label=copy(self.label), source=copy(self.source))
