from typing import Dict, Tuple, Callable, TypeVar, Optional, Any, TypeVar, NamedTuple, Union

T, U = TypeVar("T"), TypeVar("U")
ValueChanged = NamedTuple("ValueChanged", [("from_val", T), ("to_val", T)])


def dict_diff(from_dict: Dict[str, T], to_dict: Dict[str, T]) -> Dict[str, ValueChanged]:
    result: Dict[str, ValueChanged] = {}

    all_keys: set[str] = from_dict.keys() | to_dict.keys()
    for key in all_keys:
        if type(from_dict.get(key)) != type(to_dict.get(key)) or from_dict.get(key) != to_dict.get(key):
            result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))

    return result


def dict_zip(dict1: Dict[str, T], dict2: Dict[str, U]) -> Dict[str, Tuple[Union[T, None], Union[U, None]]]:
    keys: set[str] = dict1.keys() | dict2.keys()

    zipped_dict: Dict[str, Tuple[Union[T, None], Union[U, None]]] = {}
    for key in keys:
        zipped_dict[key] = dict1.get(key), dict2.get(key)

    return zipped_dict


def try_or_none(runnable: Callable[[], T]) -> Optional[T]:
    try:
        return runnable()
    except:
        return None


def assert_no_diffs(step: str, diff: Dict[str, ValueChanged]) -> None:
    assert len(diff) == 0, f"Unexpected diffs on step '{step}': {diff}"


def assert_expected_diffs(step, diff, expected) -> None:
    for key in expected.keys():
        assert (
            diff[key] == expected[key]
        ), f"Step '{step}': '{key}' was expected to be '{expected[key]}' but found {diff[key]}"
        del diff[key]
