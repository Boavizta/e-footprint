# Integration tests pattern
Integration tests follow a pattern to make sure that the same tests are run on a system generated with code and the same system read from json.

- The system from code test module and the system from json test module are defined respectively in @tests/integration_tests/test_integration_[test_name].py and @tests/integration_tests/test_integration_[test_name]_from_json.py.
- In their modules, they define respectively an IntegrationTest[TestName] and an IntegrationTest[TestName]FromJson class that both inherit from the IntegrationTest[TestName]BaseClass defined in @tests/integration_tests/integration_[test_name]_base_class.py.
- The IntegrationTest[TestName]FromJson class overwrites the setUpClass classmethod so that the system is first generated like in the system from code test, then written to json and read from json, so that subsequent tests are run on a system loaded from json.
- Both classes implement the same test methods, that call their run_[test_method_name] methods from the IntegrationTest[TestName]BaseClass.
