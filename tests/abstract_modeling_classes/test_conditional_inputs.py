from typing import Union
from unittest.mock import patch

import pytest

from efootprint.abstract_modeling_classes.conditional_inputs import allowed_values, dependent_inputs, resolve_input_path
from efootprint.abstract_modeling_classes.contextual_modeling_object_attribute import ContextualModelingObjectAttribute
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.source_objects import SourceObject, SourceValue
from efootprint.constants.units import u


def rule(path, branches=None):
    return {"choice": {"depends_on": path, "conditional_list_values": branches or {}}}


class Controller(ModelingObject):
    def __init__(self, name, mode: SourceObject, alternate: SourceObject):
        super().__init__(name)
        self.mode = mode
        self.alternate = alternate


class OtherController(ModelingObject):
    def __init__(self, name, mode: SourceObject):
        super().__init__(name)
        self.mode = mode


class DirectChoice(ModelingObject):
    conditional_list_values = rule("controller.mode")

    def __init__(self, name, controller: Controller, choice: SourceObject):
        super().__init__(name)
        self.controller = controller
        self.choice = choice


class InheritedChoice(DirectChoice):
    pass


class OverriddenChoice(DirectChoice):
    conditional_list_values = rule("controller.alternate")


class NoChoice(DirectChoice):
    conditional_list_values = {}


class Middle(ModelingObject):
    def __init__(self, name, controller: Controller | OtherController | None):
        super().__init__(name)
        self.controller = controller


class MultiHopChoice(ModelingObject):
    conditional_list_values = rule("middle.controller.mode")

    def __init__(self, name, middle: Middle, choice: SourceObject):
        super().__init__(name)
        self.middle = middle
        self.choice = choice


class LocalChoice(ModelingObject):
    conditional_list_values = rule("mode")

    def __init__(self, name, mode: SourceObject, choice: SourceObject):
        super().__init__(name)
        self.mode = mode
        self.choice = choice


def controller(name):
    return Controller(name, SourceObject("a"), SourceObject("b"))


def test_dependent_inputs_return_one_step_of_same_owner_chain():
    """Test callers receive the immediate dependent and can discover the next link separately."""
    class Chain(ModelingObject):
        conditional_list_values = {
            "first": {"depends_on": "mode", "conditional_list_values": {}},
            "second": {"depends_on": "first", "conditional_list_values": {}}}

        def __init__(self, name, mode: SourceObject, first: SourceObject, second: SourceObject):
            super().__init__(name)
            self.mode = mode
            self.first = first
            self.second = second

    obj = Chain("chain", SourceObject("a"), SourceObject("x"), SourceObject("y"))
    first = dependent_inputs({(obj, "mode")})
    assert first == {(obj, "first")}
    assert dependent_inputs(first) == {(obj, "second")}


def test_dependent_inputs_inherited_overridden_and_removed_rules():
    """Test exact dependent classes prevent inherited and overridden routes from leaking."""
    api = controller("api")
    direct, inherited, overridden, removed = [
        cls(cls.__name__, api, SourceObject("x"))
        for cls in (DirectChoice, InheritedChoice, OverriddenChoice, NoChoice)]

    assert dependent_inputs({(api, "mode")}) == {(direct, "choice"), (inherited, "choice")}
    assert dependent_inputs({(api, "alternate")}) == {(overridden, "choice")}
    assert dependent_inputs({(job, "controller") for job in (direct, inherited, overridden, removed)}) == {
        (job, "choice") for job in (direct, inherited, overridden)}


def test_dependent_inputs_multi_hop_union_and_replacement_triggers():
    """Test terminal controllers and every intermediate replacement discover all affected owners."""
    first, second = controller("first"), OtherController("second", SourceObject("a"))
    left, right = Middle("left", first), Middle("right", second)
    left_job, right_job = [MultiHopChoice(name, middle, SourceObject("x"))
                           for name, middle in (("left job", left), ("right job", right))]
    assert dependent_inputs({(first, "mode"), (left, "controller"), (left_job, "middle")}) == {(left_job, "choice")}
    assert dependent_inputs({(second, "mode")}) == {(right_job, "choice")}
    assert resolve_input_path(left_job.middle, "controller.mode") == (first, "mode")


def test_dependent_inputs_match_a_controller_subclass_through_its_mro():
    """Test an inherited controller type participates in routes registered for its base class."""
    class SpecializedController(Controller):
        pass

    api = SpecializedController("specialized", SourceObject("a"), SourceObject("b"))
    job = DirectChoice("job", api, SourceObject("x"))
    assert dependent_inputs({(api, "mode")}) == {(job, "choice")}


def test_proposed_links_redirect_every_hop_without_attaching():
    """Test the proposed graph excludes overridden live links and includes new multi-hop links."""
    old, new = controller("old"), controller("new")
    left, right = Middle("left", old), Middle("right", old)
    job = MultiHopChoice("job", left, SourceObject("x"))
    changes = {(job, "middle"): right, (right, "controller"): new}
    assert dependent_inputs({(old, "mode")}, changes) == set()
    assert dependent_inputs({(new, "mode")}, changes) == {(job, "choice")}
    assert resolve_input_path(job, "middle.controller.mode", changes) == (new, "mode")
    assert job.middle._value is left
    assert right.controller._value is old
    assert new.contextual_modeling_obj_containers == []


def test_proposed_links_accept_wrappers_and_unlinking():
    """Test wrapped proposed relationships normalize to actual owners and None removes a route."""
    old, new = controller("old"), controller("new")
    job = DirectChoice("job", old, SourceObject("x"))
    other = DirectChoice("other", new, SourceObject("x"))
    changes = {(job, "controller"): other.controller}
    assert dependent_inputs({(other.controller, "mode")}, changes) == {(job, "choice"), (other, "choice")}
    assert resolve_input_path(job, "controller.mode", changes) == (new, "mode")
    assert dependent_inputs({(old, "mode")}, {(job, "controller"): None}) == set()


def test_dependent_inputs_ignore_detached_and_stale_backlinks():
    """Test wrappers must still occupy the declared direct input to participate in reverse lookup."""
    old, new = controller("old"), controller("new")
    job = DirectChoice("job", old, SourceObject("x"))
    stale = ContextualModelingObjectAttribute(old, job, "controller")
    job._set_input_passively("controller", new)
    assert stale.modeling_obj_container is job
    assert dependent_inputs({(old, "mode")}) == set()
    assert dependent_inputs({(new, "mode")}) == {(job, "choice")}


def test_later_classes_register_without_instance_lifecycle_side_effects():
    """Test a class defined after controllers exist contributes routes before any instance is made."""
    api = controller("api")

    class LaterChoice(ModelingObject):
        conditional_list_values = rule("controller.mode")

        def __init__(self, name, controller: Union[Controller, OtherController], choice: SourceObject):
            super().__init__(name)
            self.controller = controller
            self.choice = choice

    with patch("efootprint.abstract_modeling_classes.conditional_inputs.register_conditional_inputs",
               side_effect=AssertionError("instance registration")):
        later = LaterChoice("later", api, SourceObject("x"))
        other = OtherController("other", SourceObject("a"))
        second = LaterChoice("second", other, SourceObject("x"))
        assert dependent_inputs({(api, "mode")}) == {(later, "choice")}
        assert dependent_inputs({(other, "mode")}) == {(second, "choice")}


@pytest.mark.parametrize(
    "path", ["missing.mode", "controller.missing", "controller..mode", "", "controller.mode.extra"])
def test_invalid_paths_fail_at_class_definition(path):
    """Test malformed paths report the declaring class and complete path at registration."""
    with pytest.raises(ValueError) as error:
        class InvalidChoice(DirectChoice):
            conditional_list_values = rule(path)

    assert "InvalidChoice.choice" in str(error.value)
    assert repr(path) in str(error.value)


@pytest.mark.parametrize("annotation", [list[Controller], dict[str, Controller]])
def test_collection_paths_fail_at_class_definition(annotation):
    """Test a collection annotation cannot be interpreted as a direct relationship."""
    with pytest.raises(ValueError, match="direct ModelingObject relationship"):
        class CollectionChoice(ModelingObject):
            conditional_list_values = rule("controllers.mode")

            def __init__(self, name, controllers: annotation, choice: SourceObject):
                super().__init__(name)


def test_resolve_input_path_reports_missing_values_without_computing():
    """Test missing final and intermediate values are errors but proposed terminal values resolve."""
    api = controller("api")
    job = DirectChoice("job", api, SourceObject("x"))
    for path, changes in (("controller.missing", {}), ("controller.mode", {(job, "controller"): None})):
        with pytest.raises(ValueError) as error:
            resolve_input_path(job, path, changes)
        assert path in str(error.value)
    assert resolve_input_path(job, "controller.missing", {(api, "missing"): SourceObject(0)}) == (api, "missing")


def test_allowed_values_branch_order_static_intersection_and_live_metadata():
    """Test choice queries preserve branch order and read metadata changes without registration."""
    first, second, third = SourceObject("first"), SourceObject("second"), SourceObject("third")
    declarations = rule("mode", {SourceObject("a"): [third, first, second], SourceObject("empty"): []})
    with patch.object(LocalChoice, "conditional_list_values", declarations), \
            patch.object(LocalChoice, "list_values", {"choice": [SourceObject("second"), SourceObject("first")]}):
        assert allowed_values(LocalChoice, "choice", SourceObject("a")) == (first, second)
        assert allowed_values(LocalChoice, "choice", SourceObject("missing")) == (second, first)
        assert allowed_values(LocalChoice, "choice", SourceObject("empty")) == ()
        declarations["choice"]["conditional_list_values"][SourceObject("a")] = [second]
        assert allowed_values(LocalChoice, "choice", SourceObject("a")) == (second,)
        assert second.modeling_obj_container is None
    assert allowed_values(LocalChoice, "choice", SourceObject("missing")) is None
    with patch.object(LocalChoice, "list_values", {"static": [third]}):
        assert allowed_values(LocalChoice, "static", None) == (third,)
    with patch.object(LocalChoice, "list_values", {"choice": []}):
        assert allowed_values(LocalChoice, "choice", SourceObject("missing")) == ()


def test_allowed_values_distinguishes_absence_from_zero_for_keys_and_choices():
    """Test semantic membership keeps empty values distinct from explicit numeric zero."""
    absent, zero = EmptyExplainableObject(), SourceValue(0 * u.dimensionless)
    with patch.object(LocalChoice, "conditional_list_values", rule("mode", {SourceObject(0): [absent, zero]})), \
            patch.object(LocalChoice, "list_values", {"choice": [zero]}):
        assert allowed_values(LocalChoice, "choice", absent) == (zero,)
        assert allowed_values(LocalChoice, "choice", SourceObject(0)) == (zero,)
    with patch.object(LocalChoice, "conditional_list_values", rule("mode", {SourceObject(0): []})):
        assert allowed_values(LocalChoice, "choice", absent) is None
        assert allowed_values(LocalChoice, "choice", SourceObject(0)) == ()


def test_allowed_values_preserve_timeseries_authoring_semantics():
    """Test equal numeric series with different authored units remain distinct choices."""
    from efootprint.builders.timeseries.explainable_recurrent_quantities_from_constant import (
        ExplainableRecurrentQuantitiesFromConstant)

    watts = ExplainableRecurrentQuantitiesFromConstant({"constant_value": 1000, "constant_unit": "W"})
    kilowatts = ExplainableRecurrentQuantitiesFromConstant({"constant_value": 1, "constant_unit": "kW"})
    assert (watts.value == kilowatts.value).all()
    with patch.object(LocalChoice, "list_values", {"choice": [watts]}), \
            patch.object(LocalChoice, "conditional_list_values", rule("mode", {SourceObject("a"): [kilowatts]})):
        assert allowed_values(LocalChoice, "choice", SourceObject("a")) == ()


def test_dependent_inputs_visit_only_matching_routes_and_reached_backlinks():
    """Test lookup work stays constant when disconnected unrelated owners are added."""
    class CountedController(ModelingObject):
        def __init__(self, name, mode: SourceObject):
            super().__init__(name)
            self.mode = mode

    class CountedChoice(ModelingObject):
        conditional_list_values = rule("controller.mode")

        def __init__(self, name, controller: CountedController, choice: SourceObject):
            super().__init__(name)
            self.controller = controller
            self.choice = choice

    class CountedBacklinks(list):
        visits = 0

        def __iter__(self):
            for value in super().__iter__():
                self.visits += 1
                yield value

    api = CountedController("api", SourceObject("a"))
    job = CountedChoice("job", api, SourceObject("x"))
    links = CountedBacklinks(api.contextual_modeling_obj_containers)
    api.contextual_modeling_obj_containers = links
    assert dependent_inputs({(api, "unrelated")}) == set()
    assert links.visits == 0
    assert dependent_inputs({(api, "mode")}) == {(job, "choice")}
    assert links.visits == 1
    unrelated = [CountedChoice(f"job {i}", CountedController(f"api {i}", SourceObject("a")), SourceObject("x"))
                 for i in range(100)]
    assert dependent_inputs({(api, "mode")}) == {(job, "choice")}
    assert links.visits == 2
    assert len(unrelated) == 100
