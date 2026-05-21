"""Authoring scripts that regenerate the how-to template JSONs.

Each script exposes a ``build_system()`` constructor and writes its JSON when
run as a module. IDs are pinned to readable, name-based slugs (rather than the
default per-process uuids) so the committed JSON is reviewable and stable
across regenerations. Importing this package flips the ``_use_name_as_id`` flag
on both ``ModelingObject`` and ``Source`` *before* any other efootprint import
loads, so that source constants instantiated at module-import time also use
name-based ids.
"""
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject

ModelingObject._use_name_as_id = True
Source._use_name_as_id = True
