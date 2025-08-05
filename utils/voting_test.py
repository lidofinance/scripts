from typing import Callable

import inspect
import os


def if_voting_script_in_archive(func: Callable):
    func_path = inspect.getfile(func)
    return "archive" in os.path.normpath(func_path).split(os.sep)