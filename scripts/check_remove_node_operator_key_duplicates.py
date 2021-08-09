try:
    from brownie import interface, accounts
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface)")

import json, sys, os, re, time
from typing import Tuple, Any, List
from generated.types import BrownieInterface
from utils.utils import pp
from utils.node_operators import encode_remove_signing_keys, get_node_operators, get_signing_keys, \
    get_signing_key_indexes, fetch_last_duplicated_indexes, get_signing_key_pubkeys
from utils.node_operators import find_last_duplicated_signing_keys
from utils.config import (
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address,
    lido_dao_node_operators_registry,
    get_deployer_account,
    prompt_bool
)


def set_console_globals(**kwargs):
    global interface
    interface = kwargs['interface']  # type: BrownieInterface


def main():
    node_operator_id = 7  # Everstake
    registry = interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)

    start_index = 1700
    end_index = 1810

    signing_keys = get_signing_keys(node_operator_id, registry, True, start_index, end_index)
    duplicated_signing_keys = find_last_duplicated_signing_keys(signing_keys)
    duplicated_signing_keys_indexes = get_signing_key_indexes(duplicated_signing_keys)
    duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(duplicated_signing_keys, True)

    pp('Duplicated signing keys qty', len(duplicated_signing_keys))
    pp('Duplicated signing keys indexes', duplicated_signing_keys_indexes)
    pp('Duplicated signing keys pubkeys', duplicated_signing_keys_pubkeys)

    for index in duplicated_signing_keys_indexes:
        registry.removeSigningKey.call((node_operator_id, index))
        pp("Removed key with index", index)

    updated_signing_keys = get_signing_keys(node_operator_id, registry, True, start_index, end_index)
    updated_duplicated_signing_keys = find_last_duplicated_signing_keys(updated_signing_keys)
    updated_duplicated_signing_keys_indexes = get_signing_key_indexes(updated_duplicated_signing_keys)
    updated_duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(updated_duplicated_signing_keys, True)

    pp('Duplicated signing keys qty  (after removal)', len(updated_duplicated_signing_keys))
    pp('Duplicated signing keys indexes (after removal)', updated_duplicated_signing_keys_indexes)
    pp('Duplicated signing keys pubkeys (after removal)', updated_duplicated_signing_keys_pubkeys)

    p