import inspect

from ecologits.impacts.llm import dag


ECOLOGITS_DEPENDENCY_GRAPH = dag._DAG__dependencies


def get_formula(task_name: str):
    task = dag._DAG__tasks.get(task_name)
    task_code = None
    if task:
        task_code = inspect.getsource(task)
    return task_code.split("\"\"\"")[-1].replace("return", task_name + " =").replace("\n    ", "\n")
