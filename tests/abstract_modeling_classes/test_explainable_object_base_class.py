from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

import pytz

from efootprint.abstract_modeling_classes.explainable_object_base_class import ExplainableObject, \
    optimize_attr_updates_chain
from efootprint.abstract_modeling_classes.explainable_timezone import ExplainableTimezone
from efootprint.abstract_modeling_classes.source_objects import Source


class TestExplainableObjectBaseClass(TestCase):
    def setUp(self) -> None:
        self.a = ExplainableObject(1, "a")
        self.b = ExplainableObject(2, "b")

        self.c = ExplainableObject(3, "c")
        self.c.left_parent = self.a
        self.c.right_parent = self.b
        self.c.operator = "+"
        self.c.direct_ancestors_with_id = [self.a, self.b]

        self.d = ExplainableObject(4, "d")
        self.d.left_parent = self.c
        self.d.right_parent = self.a
        self.d.operator = "+"
        self.d.direct_ancestors_with_id = [self.c, self.a]

        self.e = ExplainableObject(5, "e")
        self.e.left_parent = self.c
        self.e.right_parent = self.b
        self.e.operator = "+"
        self.e.label = None
        self.e.direct_ancestors_with_id = [self.c, self.b]

        self.f = ExplainableObject(6, "f")
        self.f.left_parent = self.e
        self.f.right_parent = self.a
        self.f.operator = "+"
        self.f.direct_ancestors_with_id = [self.a]

        self.g = ExplainableObject(2, "g")
        self.g.left_parent = self.d
        self.g.operator = "root square"
        self.g.direct_ancestors_with_id = [self.d]

        self.modeling_obj_container_mock = MagicMock()
        self.modeling_obj_container_mock.id = 1
        self.modeling_obj_container_mock.name = "Model1"

        for expl_obj in [self.a, self.b, self.c, self.d, self.f, self.g]:
            expl_obj.set_modeling_obj_container(MagicMock(), "attr_name")

    def test_copy_should_set_modeling_obj_container_to_none(self):
        a = ExplainableObject(1, "a")
        a.modeling_obj_container = "obj"
        from copy import copy
        b = copy(a)

        self.assertEqual("a", b.label)
        self.assertEqual(1, b.value)
        self.assertIsNone(b.modeling_obj_container)

    def test_creation_with_label(self):
        eo = ExplainableObject(value=5, label="Label A")
        self.assertEqual(eo.value, 5)
        self.assertEqual(eo.label, "Label A")
        self.assertIsNone(eo.left_parent)
        self.assertIsNone(eo.right_parent)

    def test_creation_without_label_and_child(self):
        with self.assertRaises(ValueError):
            ExplainableObject(value=5)

    def test_set_modeling_obj_container_without_label(self):
        self.a.label = None
        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")

    def test_set_modeling_obj_container_with_different_modeling_object_should_raise_PermissionError(self):
        self.a.left_parent = MagicMock()
        self.a.modeling_obj_container = MagicMock()
        self.a.modeling_obj_container.id = 2
        self.a.modeling_obj_container.name = "Model2"
        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")

    def test_set_modeling_obj_container_success(self):
        self.a.set_modeling_obj_container(None, None)
        self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")
        self.assertEqual(self.a.modeling_obj_container, self.modeling_obj_container_mock)
        self.assertEqual(self.a.attr_name_in_mod_obj_container, "attr1")

    def test_set_modeling_obj_container_should_trigger_add_child_to_direct_children_with_id(self):
        ancestor = MagicMock()
        self.a._direct_ancestors_with_id = [ancestor]
        self.a.set_modeling_obj_container(None, None)
        self.a.set_modeling_obj_container(self.modeling_obj_container_mock, "attr1")
        ancestor.add_child_to_direct_children_with_id.assert_called_once_with(direct_child=self.a)

    def test_set_modeling_obj_container_should_trigger_remove_child_from_direct_children_with_id(self):
        ancestor = MagicMock()
        self.a._direct_ancestors_with_id = [ancestor]
        self.a._direct_ancestors_with_id = [ancestor]
        self.a.modeling_obj_container = MagicMock()
        self.a.modeling_obj_container.id = 2
        self.a.modeling_obj_container.name = "Model2"
        self.a.set_modeling_obj_container(None, None)
        ancestor.remove_child_from_direct_children_with_id.assert_called_once_with(direct_child=self.a)

    def test_add_child_to_direct_children_with_id_shouldnt_update_list_if_child_already_in_list(self):
        self.a.direct_children_with_id = [self.c]
        self.c.modeling_obj_container = self.modeling_obj_container_mock
        self.a.add_child_to_direct_children_with_id(self.c)

        self.assertEqual([self.c], self.a.direct_children_with_id)

    def test_remove_child_from_direct_children_with_id_shouldnt_update_list_if_child_not_in_list(self):
        direct_child = MagicMock(id="1")
        self.a.direct_children_with_id = [direct_child]
        self.a.remove_child_from_direct_children_with_id(MagicMock(id="2"))

        self.assertEqual([direct_child], self.a.direct_children_with_id)

    def test_remove_child_from_direct_children_with_id_should_update_list_if_child_in_list(self):
        direct_child = MagicMock(id="1")
        self.a.direct_children_with_id = [direct_child]
        self.a.remove_child_from_direct_children_with_id(direct_child)

        self.assertEqual([], self.a.direct_children_with_id)

    def test_all_descendants_with_id(self):
        root = ExplainableObject(0, "root")
        child1 = ExplainableObject(1, "child1")
        child1.modeling_obj_container = MagicMock(id="child1_mod_obj_container")
        child1.attr_name_in_mod_obj_container = "grandchild1"
        child2 = ExplainableObject(2, "child2")
        child2.modeling_obj_container = MagicMock(id="child2_mod_obj_container")
        child2.attr_name_in_mod_obj_container = "grandchild2"
        grandchild1 = ExplainableObject(3, "grandchild1")
        grandchild1.modeling_obj_container = MagicMock(id="grandchild1_mod_obj_container")
        grandchild1.attr_name_in_mod_obj_container = "grandchild1"
        grandchild2 = ExplainableObject(4, "grandchild2")
        grandchild2.modeling_obj_container = MagicMock(id="grandchild2_mod_obj_container")
        grandchild2.attr_name_in_mod_obj_container = "grandchild2"

        root.direct_children_with_id.append(child1)
        root.direct_children_with_id.append(child2)
        child1.direct_children_with_id.append(grandchild1)
        child2.direct_children_with_id.append(grandchild2)

        descendants = root.all_descendants_with_id
        descendants_labels = [descendant.label for descendant in descendants]

        self.assertEqual(len(descendants), 4)
        self.assertListEqual(descendants_labels, ["child1", "child2", "grandchild2", "grandchild1"])

    def test_all_ancestors_with_id(self):
        descendant = ExplainableObject(0, "descendant")
        parent1 = ExplainableObject(1, "parent1")
        parent1.modeling_obj_container = MagicMock(id="parent1_mod_obj_container")
        parent1.attr_name_in_mod_obj_container = "parent1"
        parent2 = ExplainableObject(2, "parent2")
        parent2.modeling_obj_container = MagicMock(id="parent2_mod_obj_container")
        parent2.attr_name_in_mod_obj_container = "parent2"
        grandparent1 = ExplainableObject(3, "grandparent1")
        grandparent1.modeling_obj_container = MagicMock(id="grandparent1_mod_obj_container")
        grandparent1.attr_name_in_mod_obj_container = "grandparent1"
        grandparent2 = ExplainableObject(4, "grandparent2")
        grandparent2.modeling_obj_container = MagicMock(id="grandparent2_mod_obj_container")
        grandparent2.attr_name_in_mod_obj_container = "grandparent2"

        descendant.direct_ancestors_with_id.append(parent1)
        descendant.direct_ancestors_with_id.append(parent2)
        parent1.direct_ancestors_with_id.append(grandparent1)
        parent2.direct_ancestors_with_id.append(grandparent2)

        ancestors = descendant.all_ancestors_with_id
        ancestors_labels = [ancestor.label for ancestor in ancestors]

        self.assertEqual(len(ancestors), 4)
        self.assertListEqual(ancestors_labels, ["parent1", "grandparent1", "parent2", "grandparent2"])

    def test_direct_children(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        left_parent.modeling_obj_container = MagicMock(name="lc_mod_obj_name", id="lc_mod_obj_id")
        left_parent.attr_name_in_mod_obj_container = "left_parent"
        right_parent.modeling_obj_container = MagicMock(name="rc_mod_obj_name", id="rc_mod_obj_id")
        right_parent.attr_name_in_mod_obj_container = "right_parent"

        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent")
        self.assertEqual([left_parent, right_parent], eo.direct_ancestors_with_id)

    def test_update_function_chain_single_level_descendants(self):
        mod_obj_container = "mod_obj"
        parent = ExplainableObject(1, "test")
        parent.modeling_obj_container = MagicMock()
        parent.modeling_obj_container.id = "id"
        parent.attr_name_in_mod_obj_container = "parent_attr"

        child1 = MagicMock()
        child1.id = "child1_id"
        child1.direct_children_with_id = []
        child1.direct_ancestors_with_id = [parent]

        child2 = MagicMock()
        child2.id = "child2_id"
        child2.direct_children_with_id = []
        child2.direct_ancestors_with_id = [parent]

        parent.direct_children_with_id = [child1, child2]

        for index, child in enumerate([child1, child2]):
            child.modeling_obj_container = mod_obj_container
            child.attr_name_in_mod_obj_container = f"attr_{index}"
            child.dict_container = None
            child.update_function = MagicMock()

        with patch.object(ExplainableObject, "all_descendants_with_id", new_callable=PropertyMock) \
                as mock_all_descendants_with_id:
            mock_all_descendants_with_id.return_value = [child1, child2]

            result = parent.update_function_chain

            self.assertEqual([child1.update_function, child2.update_function], result)

    def test_update_function_chain_multiple_levels_of_descendants(self):
        mod_obj_container = "mod_obj_container"
        parent = ExplainableObject(1, "test")
        parent.modeling_obj_container = MagicMock()
        parent.modeling_obj_container.id = "id"
        parent.attr_name_in_mod_obj_container = "parent_attr"

        child1 = MagicMock()
        child1.id = "child1_id"
        child1.direct_ancestors_with_id = [parent]

        grandchild1 = MagicMock()
        grandchild1.id = "grandchild1_id"
        grandchild1.direct_children_with_id = []
        grandchild1.direct_ancestors_with_id = [child1]

        grandchild2 = MagicMock()
        grandchild2.id = "grandchild2_id"
        grandchild2.direct_children_with_id = []
        grandchild2.direct_ancestors_with_id = [child1]

        child1.direct_children_with_id = [grandchild1, grandchild2]
        parent.direct_children_with_id = [child1]

        for index, child in enumerate([child1, grandchild1, grandchild2]):
            child.modeling_obj_container = mod_obj_container
            child.attr_name_in_mod_obj_container = f"attr_{index}"
            child.dict_container = None
            child.update_function = MagicMock()

        with patch.object(ExplainableObject, "all_descendants_with_id", new_callable=PropertyMock) \
                as mock_all_descendants_with_id:
            mock_all_descendants_with_id.return_value = [child1, grandchild1, grandchild2]

            result = parent.update_function_chain

            self.assertEqual([child1.update_function, grandchild1.update_function, grandchild2.update_function], result)

    def test_update_function_chain_optimizes_loops(self):
        mod_obj_container = "mod_obj_container"
        parent = ExplainableObject(1, "test")
        parent.modeling_obj_container = MagicMock()
        parent.modeling_obj_container.id = "id"
        parent.attr_name_in_mod_obj_container = "parent_attr"

        child1 = MagicMock()
        child1.id = "child1_id"
        child1.direct_ancestors_with_id = [parent]

        child2 = MagicMock()
        child2.id = "child2_id"
        child2.direct_ancestors_with_id = [parent]
        child2.dict_container = None
        child2.update_function = MagicMock()

        grandchild1 = MagicMock()
        grandchild1.id = "grandchild1_id"
        grandchild1.direct_children_with_id = []
        grandchild1.direct_ancestors_with_id = [child1, child2]

        grandchild2 = MagicMock()
        grandchild2.id = "grandchild2_id"
        grandchild2.direct_children_with_id = []
        grandchild2.direct_ancestors_with_id = [child1]

        child1.direct_children_with_id = [grandchild1, grandchild2]
        child2.direct_children_with_id = [grandchild1]
        parent.direct_children_with_id = [child1, child2]

        for index, child in enumerate([child1, grandchild1, grandchild2]):
            child.modeling_obj_container = mod_obj_container
            child.attr_name_in_mod_obj_container = f"attr_{index}"
            child.dict_container = None
            child.update_function = MagicMock()

        with patch.object(ExplainableObject, "all_descendants_with_id", new_callable=PropertyMock) \
                as mock_all_descendants_with_id:
            mock_all_descendants_with_id.return_value = [child1, child2, grandchild1, grandchild2]

            result = parent.update_function_chain

            self.assertEqual(
                [child1.update_function, child2.update_function, grandchild1.update_function,
                 grandchild2.update_function], result)

    def test_optimize_attr_updates_chain_removes_dict_element_if_dict_is_recomputed_later(self):
        element_in_dict = MagicMock()
        element_in_dict.id = "element_id"
        dict_container = MagicMock()
        dict_container.id = "dict_container_id"
        element_in_dict.dict_container = dict_container

        attr_updates_chain = [element_in_dict, dict_container]

        optimized_chain = optimize_attr_updates_chain(attr_updates_chain)

        self.assertEqual(optimized_chain, [dict_container])

    def test_set_label(self):
        eo = ExplainableObject(value=5, label="Label A")
        eo.set_label("Intermediate A")
        self.assertEqual(eo.label, "Intermediate A")

    def test_has_child_property(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        eo_with_child = ExplainableObject(value=7, left_parent=left_parent, label="Parent")
        eo_without_child = ExplainableObject(value=7, label="Parent")
        self.assertTrue(eo_with_child.has_parent)
        self.assertFalse(eo_without_child.has_parent)

    def test_explain_simple_sum(self):
        self.assertEqual("c = a + b = 1 + 2 = 3", self.c.explain(pretty_print=False))

    def test_explain_nested_sum(self):
        self.assertEqual("d = c + a = 3 + 1 = 4", self.d.explain(pretty_print=False))

    def test_explain_should_skip_calculus_element_without_label(self):
        self.assertEqual("f = c + b + a = 3 + 2 + 1 = 6", self.f.explain(pretty_print=False))

    def test_explain_without_right_parent(self):
        self.assertEqual("g = root square (d) = root square (4) = 2", self.g.explain(pretty_print=False))

    def test_explain_should_put_right_parenthesis_in_complex_calculations(self):
        self.d.set_modeling_obj_container(None, None)
        self.c.set_modeling_obj_container(None, None)
        self.c.left_parent = self.a
        self.c.right_parent = self.b
        self.d.left_parent = self.c
        self.d.right_parent = self.a
        h = ExplainableObject(1, None, self.c, self.c, "/")
        i = ExplainableObject(2, None, h, self.g, "*")
        j = ExplainableObject(-1, "k", i, self.c, "-")
        j.set_modeling_obj_container(MagicMock(), "attr_name")
        self.assertEqual("k = ((a + b) / (a + b)) * g - (a + b) = ((1 + 2) / (1 + 2)) * 2 - (1 + 2) = -1", j.explain(
            pretty_print=False))
        self.d.set_modeling_obj_container(MagicMock(), "attr_name")
        self.c.set_modeling_obj_container(MagicMock(), "attr_name")

    def test_explain_without_children(self):
        eo = ExplainableObject(value=5, label="Label A")
        result = eo.explain()
        self.assertEqual(result, "Label A = 5")

    def test_compute_explain_nested_tuples(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent",
                               operator="+")
        result = eo.compute_explain_nested_tuples()
        self.assertEqual(result, (left_parent, "+", right_parent))

    def test_print_flat_tuple_formula(self):
        left_parent = ExplainableObject(value=3, label="Label L")
        right_parent = ExplainableObject(value=4, label="Label R")
        eo = ExplainableObject(value=7, left_parent=left_parent, right_parent=right_parent, label="Parent",
                               operator="+")
        
        self.assertEqual(eo.print_flat_tuple_formula((left_parent, "+", right_parent), False), "Label L + Label R")
        self.assertEqual(eo.print_flat_tuple_formula((left_parent, "+", right_parent), True), "3 + 4")

    def test_pretty_print_calculation(self):
        calc_str = "Label A = Label L + Label R = 3 + 4 = 7"
        result = ExplainableObject.pretty_print_calculation(calc_str)
        expected_result = """Label A
=
Label L + Label R
=
3 + 4
=
7"""
        self.assertEqual(expected_result, result)

    def test_set_mod_obj_cont_raises_error_if_value_already_linked_to_another_modeling_obj_container_and_children(self):
        self.a.modeling_obj_container = MagicMock(id="mod obj id")
        new_parent_mod_obj = MagicMock(id="another obj id")
        self.a.left_parent = "non null left child"

        with self.assertRaises(PermissionError):
            self.a.set_modeling_obj_container(new_parent_mod_obj, "test_attr_name")

    def test_to_json_for_timezone(self):
        timezone_expl = ExplainableTimezone(
            pytz.timezone("Europe/Paris"), "timezone", source=Source("source name", "source link"))

        self.assertEqual(
            {"label": "timezone from source name", "zone": "Europe/Paris",
             "source": {"name": "source name", "link": "source link"}}, timezone_expl.to_json())
