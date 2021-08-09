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
    get_signing_key_indexes, fetch_last_duplicated_indexes, get_signing_key_pubkeys
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

    start_index = 1690
    end_index = 1810

    signing_keys = get_signing_keys(node_operator_id, registry, True, start_index, end_index)
    duplicated_signing_keys = find_last_duplicated_signing_keys(signing_keys)
    duplicated_signing_keys_indexes = get_signing_key_indexes(duplicated_signing_keys)
    duplicated_signing_keys_pubkeys = get_signing_key_pubkeys(duplicated_signing_keys, True)

    pp('Duplicated signing keys qty', len(duplicated_signing_keys))
    pp('Duplicated signing keys indexes', duplicated_signing_keys_indexes)
    pp('Duplicated signing keys pubkeys', duplicated_signing_keys_pubkeys)



