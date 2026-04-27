"""Completeness checks for SSOT description metadata on every concrete class.

These tests enforce the contract defined in
``e-footprint-interface/specs/features/tutorial-and-documentation/01-single-source-of-truth.md``:

1. Every concrete class has a non-empty ``__doc__``.
2. ``param_descriptions`` is defined on the class itself and its keys exactly
   cover the ``__init__`` params minus ``self`` and ``name``.
3. Every ``update_<attr>`` method on the class (excluding the
   ``update_dict_element_in_*`` fan-out helpers) has a non-empty docstring on
   the method that the class actually resolves to.
4. If ``param_interactions`` is defined, its keys are a subset of
   ``param_descriptions`` keys.
5. Every ``{kind:target}`` placeholder in any description string resolves:
   ``class:X`` → ``X`` is in ``ALL_EFOOTPRINT_CLASSES_DICT``;
   ``param:X.y`` → ``y`` is a ``__init__`` param of ``X`` (excluding ``self``);
   ``calc:X.y`` → ``y`` is an ``update_*`` method on ``X`` (excluding the
   ``dict_element_in_*`` helpers); ``doc:...`` is accepted (validated by the
   mkdocs build).
6. ``{ui:...}`` and any unknown kind in library strings is a hard failure.
"""
from typing import Iterable, List, Tuple

import pytest

from efootprint.all_classes_in_order import (
    ALL_EFOOTPRINT_CLASSES, ALL_EFOOTPRINT_CLASSES_DICT)
from efootprint.utils.placeholder_resolver import extract_placeholders
from efootprint.utils.tools import get_init_signature_params


ALLOWED_LIBRARY_KINDS = {"class", "param", "calc", "doc"}
OPTIONAL_STRING_ATTRS = ("disambiguation", "pitfalls", "interactions")


def _expected_param_keys(cls) -> List[str]:
    """Return the ``__init__`` param names that ``param_descriptions`` must cover."""
    return [name for name in get_init_signature_params(cls) if name not in {"self", "name"}]


def _own_class_attr(cls, name):
    """Return ``cls.__dict__[name]`` without walking the MRO; ``None`` if absent."""
    return cls.__dict__.get(name)


def _update_method_attr_names(cls) -> List[str]:
    """Names of calculated attributes inferred from ``update_<attr>`` methods on ``cls``'s MRO.

    Excludes ``update_dict_element_in_*`` fan-out helpers — those are
    implementation detail, not user-visible calculated attributes.
    """
    seen = set()
    for klass in cls.__mro__:
        for member_name in vars(klass):
            if not member_name.startswith("update_"):
                continue
            attr = member_name[len("update_"):]
            if attr.startswith("dict_element_in_"):
                continue
            seen.add(attr)
    return sorted(seen)


def _collect_description_strings(cls) -> List[Tuple[str, str]]:
    """All description strings owned by ``cls``, paired with a source label.

    The source label is what the test surfaces on failure so an author can find
    the exact string to fix.
    """
    items: List[Tuple[str, str]] = []

    if cls.__doc__:
        items.append((f"{cls.__name__}.__doc__", cls.__doc__))

    pd = _own_class_attr(cls, "param_descriptions") or {}
    for key, value in pd.items():
        items.append((f"{cls.__name__}.param_descriptions[{key!r}]", value))

    for attr in OPTIONAL_STRING_ATTRS:
        value = _own_class_attr(cls, attr)
        if value:
            items.append((f"{cls.__name__}.{attr}", value))

    pi = _own_class_attr(cls, "param_interactions") or {}
    for key, value in pi.items():
        items.append((f"{cls.__name__}.param_interactions[{key!r}]", value))

    for attr in _update_method_attr_names(cls):
        method = getattr(cls, f"update_{attr}", None)
        if method is not None and method.__doc__:
            items.append((f"{cls.__name__}.update_{attr}.__doc__", method.__doc__))

    return items


def _validate_placeholder(kind: str, target: str) -> Iterable[str]:
    """Yield error messages for a single ``{kind:target}`` token. Empty if valid."""
    if kind == "ui":
        yield f"forbidden kind 'ui' (interface-only) in library string"
        return
    if kind not in ALLOWED_LIBRARY_KINDS:
        yield f"unknown placeholder kind {kind!r}"
        return
    if kind == "doc":
        # Validation deferred to mkdocs build.
        return
    if kind == "class":
        if target not in ALL_EFOOTPRINT_CLASSES_DICT:
            yield f"{{class:{target}}} does not match any e-footprint class"
        return
    if kind in ("param", "calc"):
        if "." not in target:
            yield f"{{{kind}:{target}}} must have the form '<Class>.<member>'"
            return
        class_name, member = target.split(".", 1)
        cls = ALL_EFOOTPRINT_CLASSES_DICT.get(class_name)
        if cls is None:
            yield f"{{{kind}:{target}}} references unknown class {class_name!r}"
            return
        if kind == "param":
            params = [p for p in get_init_signature_params(cls) if p != "self"]
            if member not in params:
                yield f"{{param:{target}}} is not in __init__ of {class_name}"
        else:  # calc
            if member not in _update_method_attr_names(cls):
                yield f"{{calc:{target}}} has no matching update_{member} on {class_name}"


# Parametrize once — pytest uses ids for readable failure output.
_class_params = pytest.mark.parametrize(
    "cls", ALL_EFOOTPRINT_CLASSES, ids=lambda c: c.__name__)


@_class_params
def test_class_has_docstring(cls):
    assert cls.__doc__ and cls.__doc__.strip(), (
        f"{cls.__name__} has no class docstring")


@_class_params
def test_param_descriptions_cover_init_params(cls):
    pd = _own_class_attr(cls, "param_descriptions")
    assert pd is not None, (
        f"{cls.__name__} has no own param_descriptions dict (must be defined on "
        f"the concrete class, not inherited)")
    assert isinstance(pd, dict), f"{cls.__name__}.param_descriptions must be a dict"

    expected = set(_expected_param_keys(cls))
    actual = set(pd.keys())
    missing = expected - actual
    extra = actual - expected
    assert not missing and not extra, (
        f"{cls.__name__}.param_descriptions key mismatch.\n"
        f"  missing: {sorted(missing) or 'none'}\n"
        f"  extra:   {sorted(extra) or 'none'}")
    for key, value in pd.items():
        assert isinstance(value, str) and value.strip(), (
            f"{cls.__name__}.param_descriptions[{key!r}] must be a non-empty string")


@_class_params
def test_update_methods_have_docstrings(cls):
    missing = []
    for attr in _update_method_attr_names(cls):
        method = getattr(cls, f"update_{attr}", None)
        if method is None:
            missing.append(f"update_{attr} not resolvable on {cls.__name__}")
            continue
        if not (method.__doc__ and method.__doc__.strip()):
            missing.append(f"update_{attr} has no docstring (resolved to {method.__qualname__})")
    assert not missing, "\n".join(missing)


@_class_params
def test_param_interactions_keys_subset(cls):
    pi = _own_class_attr(cls, "param_interactions")
    if pi is None:
        return
    pd = _own_class_attr(cls, "param_descriptions") or {}
    extra = set(pi.keys()) - set(pd.keys())
    assert not extra, (
        f"{cls.__name__}.param_interactions has keys not in param_descriptions: "
        f"{sorted(extra)}")


@_class_params
def test_placeholders_resolve(cls):
    errors: List[str] = []
    for source, text in _collect_description_strings(cls):
        for kind, target in extract_placeholders(text):
            for problem in _validate_placeholder(kind, target):
                errors.append(f"{source}: {problem}")
    assert not errors, "\n".join(errors)
