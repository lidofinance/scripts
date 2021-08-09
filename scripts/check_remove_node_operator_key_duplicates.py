try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")

import json, sys, os, re, time
from typing import Tuple, Any, List
from generated.container import BrownieInterface
from utils.utils import pp
from utils.node_operators import encode_remove_signing_keys, get_node_operators, get_signing_keys, \
    get_signing_key_indexes, fetch_last_duplicated_indexes, get_signing_key_pubkeys, get_signing_key_by_index
from utils.node_operators import find_last_duplicated_signing_keys
from utils.config import (lido_dao_node_operators_registry)


def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']  # type: BrownieInterface


def main():
    node_operator_name = 'Everstake'
    node_operator_id = 7
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    operator_info = registry.getNodeOperator(node_operator_id, True)
    operator_name = operator_info[1]
    operator_address = operator_info[2]

    print('Duplicate keys removal script')
    pp('Operator Name', operator_name)
    pp('Operator address', operator_address)

    assert node_operator_name == operator_name

    start_index = 1700
    end_index = 2200

    signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    duplicated_signing_keys = find_last_duplicated_signing_keys(signing_keys)
    duplicated_signing_keys_indexes = get_signing_key_indexes(duplicated_signing_keys)
    duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(duplicated_signing_keys, True)

    pp('[BEFORE REMOVAL] Duplicated signing keys qty', len(duplicated_signing_keys))
    pp('[BEFORE REMOVAL] Duplicated signing keys indexes', duplicated_signing_keys_indexes)
    pp('[BEFORE REMOVAL] Duplicated signing keys pubkeys', duplicated_signing_keys_pubkeys)

    # Checking according to file
    file_path = os.environ['KEY_DUPLICATES_JSON']
    with open(file_path) as json_file:
        key_duplicates_data = json.load(json_file)

        file_duplicated_signing_keys = key_duplicates_data["signingKeys"]

        file_duplicated_signing_keys_indexes = get_signing_key_indexes(file_duplicated_signing_keys)
        file_duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(file_duplicated_signing_keys, True)

        pp('[FROM FILE] Duplicated signing keys qty', len(file_duplicated_signing_keys))

        assert file_duplicated_signing_keys_indexes == duplicated_signing_keys_indexes
        assert file_duplicated_signing_keys_pubkeys == duplicated_signing_keys_pubkeys
        print(f'File {file_path} is OK')

    # removing keys
    for index in duplicated_signing_keys_indexes:
        registry.removeSigningKeyOperatorBH(node_operator_id, index, {'from': operator_address})
        pp("Removed key with index", index)

    after_removal_signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    after_removal_duplicated_signing_keys = find_last_duplicated_signing_keys(after_removal_signing_keys)
    after_removal_duplicated_signing_keys_indexes = get_signing_key_indexes(after_removal_duplicated_signing_keys)
    after_removal_duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(after_removal_duplicated_signing_keys, True)

    pp('[AFTER REMOVAL] Duplicated signing keys qty', len(after_removal_duplicated_signing_keys))
    pp('[AFTER REMOVAL] Duplicated signing keys indexes', after_removal_duplicated_signing_keys_indexes)
    pp('[AFTER REMOVAL] Duplicated signing keys pubkeys', after_removal_duplicated_signing_keys_pubkeys)

    for after_removal_signing_key in after_removal_signing_keys:
        after_removal_pubkey = after_removal_signing_key.get('key')
        after_removal_index = after_removal_signing_key.get('index')
        signing_key = get_signing_key_by_index(signing_keys, after_removal_index)
        if signing_key:
            pubkey = signing_key.get('key')
            index = signing_key.get('index')
            if pubkey != after_removal_pubkey:
                print(f" pubkey: {pubkey} - new index [{after_removal_index}] old index [{index}]")

