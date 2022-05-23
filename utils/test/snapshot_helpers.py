from collections import namedtuple
from typing import Dict, Tuple

ValueChanged = namedtuple('ValueChanged', ['from_val', 'to_val'])


def dict_diff(from_dict: Dict[str, any], to_dict: Dict[str, any]) -> Dict[str, ValueChanged]:
    result = {}

    all_keys = from_dict.keys() | to_dict.keys()
    for key in all_keys:
        if from_dict.get(key) != to_dict.get(key):
            result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))

    return result


def dict_zip(dict1: Dict[str, any], dict2: Dict[str, any]) -> Dict[str, Tuple[any, any]]:
    keys = dict1.keys() | dict2.keys()

    zipped_dict = {}
    for key in keys:
        zipped_dict[key] = (dict1.get(key), dict2.get(key))

    return zipped_dict

