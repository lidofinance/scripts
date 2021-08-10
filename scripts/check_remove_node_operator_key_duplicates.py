try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")

import json
import os

from generated.container import BrownieInterface
from utils.config import (lido_dao_node_operators_registry)
from utils.node_operators import find_last_duplicated_signing_keys
from utils.node_operators import get_signing_keys, \
    get_signing_key_indexes, get_signing_key_pubkeys, \
    print_signing_keys_diff
from utils.utils import pp


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

    duplicated_signing_keys_indexes_sorted = sorted(duplicated_signing_keys_indexes, reverse=True)

    # removing keys
    for index in duplicated_signing_keys_indexes_sorted:
        registry.removeSigningKeyOperatorBH(node_operator_id, index, {'from': operator_address})
        pp("Removed key with index", index)

    after_removal_signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    after_removal_duplicated_signing_keys = find_last_duplicated_signing_keys(after_removal_signing_keys)
    after_removal_duplicated_signing_keys_indexes = get_signing_key_indexes(after_removal_duplicated_signing_keys)
    after_removal_duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(after_removal_duplicated_signing_keys, True)

    print()
    pp('[AFTER REMOVAL] Duplicated signing keys qty', len(after_removal_duplicated_signing_keys))
    pp('[AFTER REMOVAL] Duplicated signing keys indexes', after_removal_duplicated_signing_keys_indexes)
    pp('[AFTER REMOVAL] Duplicated signing keys pubkeys', after_removal_duplicated_signing_keys_pubkeys)

    removed_qty = len(duplicated_signing_keys)

    assert len(after_removal_signing_keys) == (len(signing_keys) - removed_qty)
    print(f'[AFTER REMOVAL] Removed signing keys qty [{removed_qty}] check OK')

    print()
    print('Last N signing keys to be moved to new indexes')
    last_n_signing_keys_pubkeys = get_signing_key_pubkeys(signing_keys[-removed_qty:])
    print(last_n_signing_keys_pubkeys)

    print()
    print('SUMMARY of keys that changed their indexes or removed:')
    print_signing_keys_diff(signing_keys, after_removal_signing_keys)

