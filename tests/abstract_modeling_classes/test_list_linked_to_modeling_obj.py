import unittest
from unittest.mock import Mock, patch
from copy import copy

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


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
        self.linked_list.trigger_modeling_updates = False

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
        self.assertTrue(linked_list.trigger_modeling_updates)

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


if __name__ == '__main__':
    unittest.main()
