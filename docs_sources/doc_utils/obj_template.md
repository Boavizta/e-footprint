# {{ obj_dict["class"] }}
{% if obj_dict["class_description"] %}
{{ obj_dict["class_description"] | safe }}
{% endif %}
{% if obj_dict["disambiguation"] %}
## When to use this class
{{ obj_dict["disambiguation"] | safe }}
{% endif %}
{% if obj_dict["interactions"] %}
## Usage from Python
{{ obj_dict["interactions"] | safe }}
{% endif %}
{% if obj_dict["pitfalls"] %}
## Common pitfalls
{{ obj_dict["pitfalls"] | safe }}
{% endif %}

## Params
{% for param_desc in obj_dict["params"] %}
{{ param_desc | safe}}
{% endfor %}

## Backwards links
{% for linked_obj in obj_dict["modeling_obj_containers"] %}
- [{{ linked_obj }}]({{ linked_obj }}.md)
{% endfor %}

## Calculated attributes
{% for calculated_attr_desc in obj_dict["calculated_attrs"] %}
{{ calculated_attr_desc | safe}}
{% endfor %}
