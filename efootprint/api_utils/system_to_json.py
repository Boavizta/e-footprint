import json

import efootprint
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


def recursively_write_json_dict(output_dict, mod_obj, save_calculated_attributes):
    mod_obj_class = mod_obj.class_as_simple_str
    if mod_obj_class not in output_dict:
        output_dict[mod_obj_class] = {}
    if mod_obj.id not in output_dict[mod_obj_class]:
        output_dict[mod_obj_class][mod_obj.id] = mod_obj.to_json(save_calculated_attributes)
        for key, value in mod_obj.__dict__.items():
            if isinstance(value, ModelingObject):
                recursively_write_json_dict(output_dict, value, save_calculated_attributes)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ModelingObject):
                for mod_obj_elt in value:
                    recursively_write_json_dict(output_dict, mod_obj_elt, save_calculated_attributes)

    return output_dict


def system_to_json(input_system, save_calculated_attributes, output_filepath=None, indent=4):
    output_dict = {"efootprint_version": efootprint.__version__}
    recursively_write_json_dict(output_dict, input_system, save_calculated_attributes)

    if output_filepath is not None:
        with open(output_filepath, "w") as file:
            file.write(json.dumps(output_dict, indent=indent))

    return output_dict
