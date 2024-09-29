from typing import List, Callable


def launch_update_function_chain(update_function_chain: List[Callable]):
    for update_function in update_function_chain:
        update_function()
