import collections
from typing import List, Dict, TypedDict, Union, Optional

from brownie.convert.datatypes import HexString

from utils.evm_script import encode_call_script
from generated.types import NodeOperatorsRegistry
from utils.utils import group_by, pick_by, ProgressBar


# Type description
class SigningKeyIndexed(TypedDict):
    key: HexString
    depositSignature: HexString
    used: bool
    index: int


def encode_set_node_operator_staking_limit(id, limit, registry):
    return (
        registry.address,
        registry.setNodeOperatorStakingLimit.encode_input(id, limit)
    )


def encode_set_node_operators_staking_limits_evm_script(node_operators, registry):
    return encode_call_script([
        encode_set_node_operator_staking_limit(id=node_operator["id"],
                                               limit=node_operator["limit"],
                                               registry=registry)
        for node_operator in node_operators
    ])


def get_node_operators(registry):
    return [{**registry.getNodeOperator(i, True), **{'index': i}} for i in range(registry.getNodeOperatorsCount())]


def encode_remove_signing_key(operator_id, index_to_remove, registry):
    return (
        registry.address,
        registry.removeSigningKey.encode_input(operator_id, index_to_remove)
    )


def encode_remove_signing_keys(operator_id, indexes_to_remove, registry):
    return [
        encode_remove_signing_key(operator_id=operator_id,
                                  index_to_remove=key_index,
                                  registry=registry)
        for key_index in indexes_to_remove
    ]


def get_signing_keys(node_operator_id: int, registry: NodeOperatorsRegistry, progress: bool = False,
                     start_index: int = 0, end_index: int = -1) -> List[SigningKeyIndexed]:
    total_keys = registry.getTotalSigningKeyCount(node_operator_id)

    end_index = (total_keys - 1) if end_index == -1 else end_index

    assert start_index <= end_index
    assert start_index <= total_keys
    assert end_index < total_keys

    bar = ProgressBar(start_index, end_index, start_index, f"Fetching keys for OP #{node_operator_id} " +
                      f"(from {start_index} to {end_index})")

    keys = []
    for i in range(start_index, end_index + 1):
        keys.append({**registry.getSigningKey(node_operator_id, i), **{'index': i}})
        if progress:
            bar.stepTo(i)

    return keys


def find_all_duplicated_signing_keys(keys: List[SigningKeyIndexed]) -> List[SigningKeyIndexed]:
    """
    Finds all keys that have duplicates in a whole array of keys
    and checks that all keys are not 'used'
    Args:
        keys (List[SigningKeyIndexed]): Collection to of all keys
    Returns:
        list: Unsorted collection of duplicated signing keys
    Example:
        keys = find_all_duplicated_keys([A{index=1}, B{index=5}, A{index=7}, A{index=3}, C{index=4}])
        assert keys == [A{index=1}, A{index=7}, A{index=3}]
    """
    group_by_key: Dict[str, List[SigningKeyIndexed]] = group_by(keys, 'key')

    duplicate_groups = pick_by(group_by_key, lambda group, _: len(group) > 1)

    # checking that all 'duplicate_groups' have only unused keys (with 'used': False)
    for _, group in duplicate_groups.items():
        for signing_key in group:
            assert signing_key.get('used', True) is False

    duplicated_keys: List[SigningKeyIndexed] = []
    for _, group in duplicate_groups.items():
        duplicated_keys.extend(group)

    return duplicated_keys


def find_last_duplicated_signing_keys(keys: List[SigningKeyIndexed]) -> List[SigningKeyIndexed]:
    duplicated_keys = find_all_duplicated_signing_keys(keys)

    duplicated_keys.sort(key=lambda signing_key: signing_key['index'], reverse=False)

    found_duplicated_keys = []
    ret = []
    for signing_key in duplicated_keys:
        if signing_key.get('key') not in found_duplicated_keys:
            found_duplicated_keys.append(signing_key.get('key'))
        else:
            ret.append(signing_key)

    return ret


def get_signing_key_indexes(keys: List[SigningKeyIndexed]) -> List[int]:
    return [signing_key.get('index') for signing_key in keys]


def get_signing_key_pubkeys(keys: List[SigningKeyIndexed], to_str: bool = False) -> List[Union[HexString, str]]:
    if to_str:
        return [str(signing_key.get('key')) for signing_key in keys]

    return [signing_key.get('key') for signing_key in keys]


def get_signing_key_indexes_by_unique_pubkeys(signing_keys: List[SigningKeyIndexed],
                                              pubkeys: List[str]) -> List[int]:
    # getting unique pubkeys
    unique_pubkeys = list(set(pubkeys))

    assert len(unique_pubkeys) == len(pubkeys)

    found_signing_keys = []
    for signing_key in signing_keys:
        if signing_key.get('key') in pubkeys:
            found_signing_keys.append(signing_key)

    # check that all pubkeys found in node_operator keys has no duplicates
    found_signing_keys_with_maybe_non_unique_indexes = []
    for signing_key in found_signing_keys:
        found_signing_keys_with_maybe_non_unique_indexes \
            .append(str(signing_key.get('key')) + str(signing_key.get('index')))

    assert len(found_signing_keys_with_maybe_non_unique_indexes) == len(pubkeys)

    return get_signing_key_indexes(found_signing_keys)


def fetch_last_duplicated_indexes(node_operator_id: int, registry: NodeOperatorsRegistry,
                                  start_index: int = 0, end_index: int = -1) -> List[int]:
    signing_keys = get_signing_keys(node_operator_id, registry, False, start_index, end_index)
    last_duplicated_keys = find_last_duplicated_signing_keys(signing_keys)
    return get_signing_key_indexes(last_duplicated_keys)


def get_signing_key_by_index(keys: List[SigningKeyIndexed], index: int) -> Optional[SigningKeyIndexed]:
    for signing_key in keys:
        if signing_key.get('index') == index:
            return signing_key

    return None


def get_signing_keys_by_pubkey(keys: List[SigningKeyIndexed], pubkey: Union[str, HexString]) -> List[SigningKeyIndexed]:
    res = []

    for signing_key in keys:
        if signing_key.get('key') == pubkey:
            res.append(signing_key)

    return res


def get_signing_key_index_by_pubkey(keys: List[SigningKeyIndexed], pubkey: Union[str, HexString]) -> Optional[int]:
    for signing_key in keys:
        if signing_key.get('key') == pubkey:
            return signing_key.get('index')

    return None


def print_signing_keys_diff(keys_a: List[SigningKeyIndexed], keys_b: List[SigningKeyIndexed]):
    print(f'Length difference: A=[{len(keys_a)}] B=[{len(keys_b)}] diff [{len(keys_a) - len(keys_b)}]')

    index_min = 1E100
    index_max = 0

    res = []

    a_dict = {}
    for key_a in keys_a:
        a_index = key_a.get('index')
        if index_min > a_index:
            index_min = a_index
        if index_max < a_index:
            index_max = a_index
        a_pubkey = key_a.get('key')
        a_dict[a_index] = a_pubkey

    b_dict = {}
    for key_b in keys_b:
        b_index = key_b.get('index')
        if index_min > b_index:
            index_min = b_index
        if index_max < b_index:
            index_max = b_index

        b_pubkey = key_b.get('key')
        b_dict[b_index] = b_pubkey

    for i in range(index_min, index_max + 1):
        key_a = a_dict.get(i, None)
        key_b = b_dict.get(i, None)

        if key_a is None and key_b is None:
            print()
        if key_a is None and key_b is not None:
            print(f'-[{i}] A [NOT FOUND] -> B [{key_b}]')
            continue
        if key_b is None and key_a is not None:
            print(f'-[{i}] A [{key_a}] -> B [NOT FOUND]')
            continue
        if key_b != key_a:
            print(f'-[{i}] A [{key_a}] -> B [{key_b}]')
            continue
