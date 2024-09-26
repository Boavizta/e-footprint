import unittest
from unittest.mock import Mock, patch
from copy import copy

from efootprint.abstract_modeling_classes.list_linked_to_modeling_obj import ListLinkedToModelingObj
from efootprint.abstract_modeling_classes.modeling_object import ModelingObject


class TestListLinkedToModelingObj(unittest.TestCase):
    def setUp(self):
        self.mock_modeling_obj = Mock()
        self.mock_modeling_obj.id = 1
        self.mock_modeling_obj.name = "TestModelingObject"
        self.mock_explainable_obj = Mock(spec=ModelingObject)
        self.mock_explainable_obj.set_modeling_obj_container = Mock()
        self.mock_explainable_obj.to_json = Mock(return_value={"mock": "object"})
        self.mock_explainable_obj2 = Mock(spec=ModelingObject)
        self.mock_explainable_obj2.set_modeling_obj_container = Mock()
        self.mock_explainable_obj2.to_json = Mock(return_value={"mock2": "object2"})
        self.linked_list = ListLinkedToModelingObj()

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_init(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        linked_list = ListLinkedToModelingObj([self.mock_explainable_obj, self.mock_explainable_obj2])
        self.assertIn(self.mock_explainable_obj, linked_list)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=None)
        self.assertIn(self.mock_explainable_obj2, linked_list)
        self.mock_explainable_obj2.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=None)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_set_modeling_obj_container(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        linked_list = ListLinkedToModelingObj([self.mock_explainable_obj, self.mock_explainable_obj2])
        linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.assertIn(self.mock_explainable_obj, linked_list)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)
        self.assertIn(self.mock_explainable_obj2, linked_list)
        self.mock_explainable_obj2.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_append(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        self.assertIn(self.mock_explainable_obj, self.linked_list)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_insert(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.insert(0, self.mock_explainable_obj)
        self.assertEqual(self.linked_list[0], self.mock_explainable_obj)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_setitem(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        self.linked_list[0] = self.mock_explainable_obj2
        self.assertEqual(self.linked_list[0], self.mock_explainable_obj2)
        self.mock_explainable_obj2.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_remove(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        self.linked_list.remove(self.mock_explainable_obj)
        self.assertNotIn(self.mock_explainable_obj, self.linked_list)
        self.mock_explainable_obj.set_modeling_obj_container.assert_called_with(None, None)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_pop(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        popped_item = self.linked_list.pop()
        self.assertEqual(popped_item, self.mock_explainable_obj)
        self.mock_explainable_obj.set_modeling_obj_container.assert_called_with(None, None)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_clear(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        self.linked_list.clear()
        self.assertEqual(len(self.linked_list), 0)
        self.mock_explainable_obj.set_modeling_obj_container.assert_called_with(None, None)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_extend(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.extend([self.mock_explainable_obj, self.mock_explainable_obj2])
        self.assertIn(self.mock_explainable_obj, self.linked_list)
        self.assertIn(self.mock_explainable_obj2, self.linked_list)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)
        self.mock_explainable_obj2.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_iadd(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list += [self.mock_explainable_obj, self.mock_explainable_obj2]
        self.assertIn(self.mock_explainable_obj, self.linked_list)
        self.assertIn(self.mock_explainable_obj2, self.linked_list)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)
        self.mock_explainable_obj2.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_imul(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        self.linked_list.set_modeling_obj_container(self.mock_modeling_obj, "attr_name")
        self.linked_list.append(self.mock_explainable_obj)
        self.linked_list *= 2
        self.assertEqual(len(self.linked_list), 2)
        self.assertEqual(self.linked_list[0], self.mock_explainable_obj)
        self.assertEqual(self.linked_list[1], self.mock_explainable_obj)
        self.mock_explainable_obj.add_obj_to_modeling_obj_containers.assert_called_with(new_obj=self.mock_modeling_obj)

    @patch.object(ListLinkedToModelingObj, "check_value_type")
    def test_copy(self, mock_check_value_type):
        mock_check_value_type.return_value = True
        linked_list = ListLinkedToModelingObj([self.mock_explainable_obj, self.mock_explainable_obj2])
        copy_list = copy(linked_list)

        self.assertEqual(len(linked_list), len(copy_list))
        for index in range(len(linked_list)):
            self.assertEqual(linked_list[index], copy_list[index])


if __name__ == '__main__':
    unittest.main()
