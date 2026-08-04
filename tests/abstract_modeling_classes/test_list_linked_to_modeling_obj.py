import operator
import unittest
from unittest.mock import Mock, patch
from copy import copy

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject
from efootprint.abstract_modeling_classes.modeling_update import ModelingUpdate


class ModelingObjectWithListForContainerTest(ModelingObject):
    default_values = {}

    def __init__(self, name, children: list[ModelingObject]):
        super().__init__(name)
        self.children = children

    @property
    def systems(self):
        return []


class TestListLinkedToModelingObj(unittest.TestCase):
    def setUp(self):
        self.mock_modeling_obj_1 = Mock()
        self.mock_modeling_obj_1.id = 1
        self.mock_modeling_obj_1.name = "TestModelingObject"
        self.mock_modeling_obj_2 = Mock(spec=ModelingObject)
        self.mock_modeling_obj_2.set_modeling_obj_container = Mock()
        self.mock_modeling_obj_2.to_json = Mock(return_value={"mock": "object"})
        self.mock_modeling_obj_3 = Mock(spec=ModelingObject)
        self.mock_modeling_obj_3.set_modeling_obj_container = Mock()
        self.mock_modeling_obj_3.to_json = Mock(return_value={"mock2": "object2"})
        self.linked_list = ListLinkedToModelingObj()

        self.mock_check_value_type = patch.object(ListLinkedToModelingObj, "check_value_type").start()
        self.mock_contextual_modeling_object_attribute = patch(
            "efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ContextualModelingObjectAttribute"
        ).start()

        self.mock_check_value_type.return_value = True
        self.mock_contextual_modeling_object_attribute.side_effect = lambda x: x

        # Ensure patches are cleaned up after the test
        self.addCleanup(patch.stopall)

    def test_init(self):
        linked_list = ListLinkedToModelingObj([self.mock_modeling_obj_2, self.mock_modeling_obj_3])
        self.assertIn(self.mock_modeling_obj_2, linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(None, None)
        self.assertIn(self.mock_modeling_obj_3, linked_list)
        self.mock_modeling_obj_3.set_modeling_obj_container.assert_called_with(None, None)
        self.assertFalse(linked_list._mutations_are_transactional)

    def test_set_modeling_obj_container(self):
        linked_list = ListLinkedToModelingObj([self.mock_modeling_obj_2, self.mock_modeling_obj_3])
        linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.assertIn(self.mock_modeling_obj_2, linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")
        self.assertIn(self.mock_modeling_obj_3, linked_list)
        self.mock_modeling_obj_3.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_append(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        self.assertIn(self.mock_modeling_obj_2, self.linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")
    
    def test_insert(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.insert(0, self.mock_modeling_obj_2)
        self.assertEqual(self.linked_list[0], self.mock_modeling_obj_2)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_setitem(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        self.linked_list[0] = self.mock_modeling_obj_3
        self.assertEqual(self.linked_list[0], self.mock_modeling_obj_3)
        self.mock_modeling_obj_3.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_remove(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        self.linked_list.remove(self.mock_modeling_obj_2)
        self.assertNotIn(self.mock_modeling_obj_2, self.linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(None, None)

    def test_pop(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        popped_item = self.linked_list.pop()
        self.assertEqual(popped_item, self.mock_modeling_obj_2)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(None, None)

    def test_clear(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        self.linked_list.clear()
        self.assertEqual(len(self.linked_list), 0)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(None, None)

    def test_extend(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.extend([self.mock_modeling_obj_2, self.mock_modeling_obj_3])
        self.assertIn(self.mock_modeling_obj_2, self.linked_list)
        self.assertIn(self.mock_modeling_obj_3, self.linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")
        self.mock_modeling_obj_3.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_iadd(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list += [self.mock_modeling_obj_2, self.mock_modeling_obj_3]
        self.assertIn(self.mock_modeling_obj_2, self.linked_list)
        self.assertIn(self.mock_modeling_obj_3, self.linked_list)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")
        self.mock_modeling_obj_3.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_imul(self):
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj_1, "attr_name")
        self.linked_list.append(self.mock_modeling_obj_2)
        self.linked_list *= 2
        self.assertEqual(len(self.linked_list), 2)
        self.assertEqual(self.linked_list[0], self.mock_modeling_obj_2)
        self.assertEqual(self.linked_list[1], self.mock_modeling_obj_2)
        self.mock_modeling_obj_2.set_modeling_obj_container.assert_called_with(self.mock_modeling_obj_1, "attr_name")

    def test_copy(self):
        linked_list = ListLinkedToModelingObj([self.mock_modeling_obj_2, self.mock_modeling_obj_3])
        copy_list = copy(linked_list)

        self.assertEqual(len(linked_list), len(copy_list))
        for index in range(len(linked_list)):
            self.assertEqual(linked_list[index], copy_list[index])


class TestListLinkedToModelingObjTransactions(unittest.TestCase):
    def test_public_iadd_launches_one_modeling_update(self):
        """Test active list augmented addition launches exactly one modeling update."""
        first_child = ModelingObject("list iadd first child")
        second_child = ModelingObject("list iadd second child")
        owner = ModelingObjectWithListForContainerTest("list iadd owner", [first_child])

        with patch(
                "efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ModelingUpdate",
                wraps=ModelingUpdate) as container_update_spy, patch(
                "efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate",
                wraps=ModelingUpdate) as attribute_update_spy:
            owner.children += [second_child]

        self.assertEqual(1, container_update_spy.call_count)
        attribute_update_spy.assert_not_called()
        self.assertEqual([first_child, second_child], owner.children)

    def test_public_imul_launches_one_modeling_update(self):
        """Test active list augmented multiplication launches exactly one modeling update."""
        child = ModelingObject("list imul child")
        owner = ModelingObjectWithListForContainerTest("list imul owner", [child])

        with patch(
                "efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ModelingUpdate",
                wraps=ModelingUpdate) as container_update_spy, patch(
                "efootprint.abstract_modeling_classes.modeling_update.ModelingUpdate",
                wraps=ModelingUpdate) as attribute_update_spy:
            owner.children *= 2

        self.assertEqual(1, container_update_spy.call_count)
        attribute_update_spy.assert_not_called()
        self.assertEqual([child, child], owner.children)

    @staticmethod
    def _public_mutation_case(prefix, operation):
        first = ModelingObject(f"{prefix} first")
        second = ModelingObject(f"{prefix} second")
        third = ModelingObject(f"{prefix} third")
        fourth = ModelingObject(f"{prefix} fourth")
        cases = {
            "append": ([first, second], lambda values: values.append(third), [first, second, third]),
            "insert": ([first, second], lambda values: values.insert(1, third), [first, third, second]),
            "setitem": ([first, second], lambda values: operator.setitem(values, 0, third), [third, second]),
            "set_slice": (
                [first, second], lambda values: operator.setitem(values, slice(0, 1), [third, fourth]),
                [third, fourth, second]),
            "extend": ([first], lambda values: values.extend([second, third]), [first, second, third]),
            "pop": ([first, second], lambda values: values.pop(), [first]),
            "remove": ([first, second], lambda values: values.remove(first), [second]),
            "clear": ([first, second], lambda values: values.clear(), []),
            "reverse": ([first, second], lambda values: values.reverse(), [second, first]),
            "sort": ([second, first], lambda values: values.sort(key=lambda child: child.name), [first, second]),
            "delitem": ([first, second], lambda values: operator.delitem(values, 0), [second]),
            "del_slice": (
                [first, second, third], lambda values: operator.delitem(values, slice(1, None)), [first]),
            "iadd": ([first], lambda values: operator.iadd(values, [second, third]), [first, second, third]),
            "imul": ([first, second], lambda values: operator.imul(values, 2), [first, second, first, second]),
        }
        initial, mutate, expected = cases[operation]
        return initial, mutate, expected, [first, second, third, fourth]

    def test_every_public_mutator_is_passive_unattached_and_transactional_when_live(self):
        """Test every public list mutator across the passive and live lifecycle states."""
        operations = (
            "append", "insert", "setitem", "set_slice", "extend", "pop", "remove", "clear", "reverse",
            "sort", "delitem", "del_slice", "iadd", "imul")
        for live in (False, True):
            for operation in operations:
                with self.subTest(live=live, operation=operation):
                    prefix = f"{'live' if live else 'passive'} {operation}"
                    initial, mutate, expected, all_children = self._public_mutation_case(prefix, operation)
                    owner = ModelingObjectWithListForContainerTest(f"{prefix} owner", initial) if live else None
                    children = owner.children if live else ListLinkedToModelingObj(initial)

                    with patch(
                            "efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ModelingUpdate",
                            wraps=ModelingUpdate) as update_spy:
                        mutate(children)

                    current = owner.children if live else children
                    self.assertEqual(int(live), update_spy.call_count)
                    self.assertEqual(expected, current)
                    for child in all_children:
                        self.assertEqual([owner] if live and child in expected else [], child.modeling_obj_containers)
                    for link in list.__iter__(current):
                        self.assertIs(owner, link.modeling_obj_container)
                        self.assertEqual("children" if live else None, link.attr_name_in_mod_obj_container)

    def test_passive_slice_set_and_drop_preserve_order_and_relationship_bookkeeping(self):
        """Test passive slice replacement and deletion preserve ordering and relationship links."""
        first_child = ModelingObject("passive slice first child")
        second_child = ModelingObject("passive slice second child")
        third_child = ModelingObject("passive slice third child")
        owner = ModelingObjectWithListForContainerTest(
            "passive slice owner", [first_child, second_child])

        with patch(
                "efootprint.abstract_modeling_classes.list_linked_to_modeling_obj.ModelingUpdate",
                wraps=ModelingUpdate) as update_spy:
            owner.children._set_entry_passively(slice(0, 1), [third_child, first_child])
            removed = owner.children._drop_entry_passively(slice(1, 2))

        update_spy.assert_not_called()
        self.assertEqual([third_child, second_child], owner.children)
        self.assertEqual([first_child], removed)
        self.assertIsNone(removed[0].modeling_obj_container)
        self.assertIsNone(removed[0].attr_name_in_mod_obj_container)
        self.assertEqual([], first_child.modeling_obj_containers)
        self.assertEqual([owner], second_child.modeling_obj_containers)
        self.assertEqual([owner], third_child.modeling_obj_containers)
        for child_link in owner.children:
            self.assertIs(owner, child_link.modeling_obj_container)
            self.assertEqual("children", child_link.attr_name_in_mod_obj_container)


if __name__ == '__main__':
    unittest.main()
