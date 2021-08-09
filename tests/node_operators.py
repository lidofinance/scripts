from brownie.convert.datatypes import HexString
from pytest import raises
from generated.types import BrownieInterface
from utils.node_operators import find_last_duplicated_signing_keys, find_all_duplicated_signing_keys, \
    get_signing_key_indexes_by_unique_pubkeys, get_signing_key_indexes


def _dummy():
    """
    Function only needed here to add type hint to brownie interfaces
    """
    global interface
    interface = {}  # type: BrownieInterface


def hex_str(bytes: bytes):
    return HexString(bytes, "bytes32")


signing_keys_one_duplicate = [
    {'key': 'A', 'index': 3, 'used': False, },
    {'key': 'B', 'index': 2, 'used': False, },
    {'key': 'A', 'index': 1, 'used': False, },
    {'key': 'C', 'index': 4, 'used': False, },
]

signing_keys_multiple_duplicates = [
    {'key': 'A', 'index': 3, 'used': False, },
    {'key': 'B', 'index': 2, 'used': False, },
    {'key': 'C', 'index': 5, 'used': False, },
    {'key': 'A', 'index': 1, 'used': False, },
    {'key': 'C', 'index': 4, 'used': False, },
]

signing_keys_with_unique_used_and_multiple_duplicates = [
    {'key': 'A', 'index': 3, 'used': False, },
    {'key': 'B', 'index': 2, 'used': False, },
    {'key': 'C', 'index': 5, 'used': False, },
    {'key': 'A', 'index': 1, 'used': False, },
    {'key': 'C', 'index': 4, 'used': False, },
    {'key': 'D', 'index': 6, 'used': True, },
]

signing_keys_with_used_and_multiple_duplicates = [
    {'key': 'A', 'index': 3, 'used': False, },
    {'key': 'B', 'index': 2, 'used': False, },
    {'key': 'C', 'index': 5, 'used': False, },
    {'key': 'D', 'index': 7, 'used': True, },
    {'key': 'A', 'index': 1, 'used': False, },
    {'key': 'C', 'index': 4, 'used': False, },
    {'key': 'D', 'index': 6, 'used': True, },
]

signing_keys_unique = [
    {'key': hex_str(b'\x00\x0A'), 'index': 0, 'used': True, },
    {'key': hex_str(b'\x00\x0B'), 'index': 1, 'used': True, },
    {'key': hex_str(b'\x00\x0C'), 'index': 2, 'used': True, },
    {'key': hex_str(b'\x00\x0D'), 'index': 3, 'used': True, },
]

signing_keys_non_unique = [
    {'key': hex_str(b'\x00\x0A'), 'index': 0, 'used': True, },
    {'key': hex_str(b'\x00\x0B'), 'index': 1, 'used': True, },
    {'key': hex_str(b'\x00\x0C'), 'index': 2, 'used': True, },
    {'key': hex_str(b'\x00\x0D'), 'index': 3, 'used': True, },
    {'key': hex_str(b'\x00\x0C'), 'index': 4, 'used': True, },
]


def test_find_all_duplicated_signing_keys():
    res = find_all_duplicated_signing_keys(signing_keys_one_duplicate)
    assert res == [
        {'key': 'A', 'index': 3, 'used': False},
        {'key': 'A', 'index': 1, 'used': False},
    ]

    res = find_all_duplicated_signing_keys(signing_keys_multiple_duplicates)
    assert res == [
        {'key': 'A', 'index': 3, 'used': False},
        {'key': 'A', 'index': 1, 'used': False},
        {'key': 'C', 'index': 5, 'used': False},
        {'key': 'C', 'index': 4, 'used': False},
    ]


def test_find_last_duplicated_signing_keys():
    res = find_last_duplicated_signing_keys(signing_keys_one_duplicate)
    assert res == [
        {'key': 'A', 'index': 3, 'used': False},
    ]

    res = find_last_duplicated_signing_keys(signing_keys_multiple_duplicates)
    assert res == [
        {'key': 'A', 'index': 3, 'used': False},
        {'key': 'C', 'index': 5, 'used': False},
    ]


def test_find_last_duplicated_signing_keys_no_used_keys():
    res = find_last_duplicated_signing_keys(signing_keys_with_unique_used_and_multiple_duplicates)
    assert res == [
        {'key': 'A', 'index': 3, 'used': False},
        {'key': 'C', 'index': 5, 'used': False},
    ]


def test_find_last_duplicated_signing_keys_with_used_keys():
    with raises(AssertionError):
        find_last_duplicated_signing_keys(signing_keys_with_used_and_multiple_duplicates)


def test_get_signing_key_indexes_by_unique_pubkeys():
    pubkeys = [
        # index: 0
        '0x0A',
        # index: 2
        '0x0C'
    ]

    res = get_signing_key_indexes_by_unique_pubkeys(signing_keys_unique, pubkeys)
    assert res == [0, 2]


def test_get_signing_key_indexes_by_unique_pubkeys_non_unique():
    pubkeys = [
        # index: 0
        '0x0A',
        # index: 1
        '0x0B',
        # index: 2
        '0x0C',
    ]
    with raises(AssertionError):
        get_signing_key_indexes_by_unique_pubkeys(signing_keys_non_unique, pubkeys)


def test_get_signing_key_indexes():
    res = get_signing_key_indexes(signing_keys_unique)
    assert res == [0, 1, 2, 3]
