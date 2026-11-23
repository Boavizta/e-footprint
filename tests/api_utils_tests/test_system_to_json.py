from comprehension_harness.python.declare import planned_test


# No narrative case passes a file: the save-and-load narrative works on the returned dict.
@planned_test("comparison-file#export: `systems_to_json` writes the dict it returns to the file it is given")
def test_systems_to_json_writes_the_file_it_is_given(tmp_path):
    ...
