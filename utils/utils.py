from typing import List, Dict, Any
from brownie.utils import color


def pp(text: str, value: Any):
    """
    Pretty-prints key-value pair
    """
    print(text, color.highlight(str(value)), end='')


def group_by(collection: List[Dict[str, Any]], key: str):
    """
    Creates an object composed of keys generated from the results of running each element of a
    `collection` through the iteratee.
    Args:
        collection (list): Collection to iterate over.
        key (str): Key for grouping by key.
    Returns:
        dict: Results of grouping by `key`.
    Example:
        >>> results = group_by([{'a': 1, 'b': 2}, {'a': 3, 'b': 4}], 'a')
        >>> assert results == {1: [{'a': 1, 'b': 2}], 3: [{'a': 3, 'b': 4}]}
    """

    ret = {}
    for value in collection:
        group_key = str(value.get(key, None))
        if group_key not in ret:
            ret[group_key] = []
        ret[group_key].append(value)

    return ret


def pick_by(obj: Dict, predicate):
    """
    Creates an dict composed of the dict properties predicate returns truthy for. The predicate
    is invoked with two arguments: ``(value, key)``.
    :param obj: (dict): Dict to pick from.
    :param predicate: (lambda(value, key)): Lambda used to determine which properties to pick.
    Returns:
        dict: Dict containg picked properties.
    Example:
        >>> some_dict = {'a': 1, 'b': '2', 'c': 3 }
        >>> assert pick_by(some_dict, lambda v: isinstance(v, int)) == {'a': 1, 'c': 3}
    """
    ret = {}

    for key, value in obj.items():
        if predicate(value, key):
            ret[str(key)] = value

    return ret


# Print iterations progress
class ProgressBar:
    def __init__(self, start, end, pos, prefix='Progress:', suffix='Complete', decimals=1, length=50, fill='█', print_end="\r"):
        self.start = start
        self.end = end
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.print_end = print_end
        self.total = self.end - self.start
        self.pos = pos
        self.rel_pos = pos - self.start

    def stepTo(self, pos: int):
        self.pos = pos
        self.rel_pos = pos - self.start
        percent = ("{0:." + str(self.decimals) + "f}").format(100 * (self.rel_pos / float(self.total)))
        filled_length = int(self.length * self.rel_pos // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        print(f'\r{self.prefix} |{bar}| {percent}% [{self.rel_pos}/{self.total}] {self.suffix}', end=self.print_end)
        # Print New Line on Complete
        if self.pos == self.end:
            print()
