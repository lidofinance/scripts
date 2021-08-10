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

    pubkeys_shifted_to_new_indexes = {
        '0x93c2f46cf10faea331c52c318a89e8ed37750077dd67f0747d55ad4eba66ae56306fbeeb5b494b2089b211ec2f7f9ada': 1760,
        '0x9811801c9fc9a91b3d2ba06447c603fc14070172a999770920f549c5ce5491ed04331c4ab0d68703123ef7a0eaa7249c': 1761,
        '0x8d2be8083d409a39b4d1be767f683bfa62209b418217a859da360daf1e3b7a140e183a61cd43dc985e5d3c328fa0814c': 1762,
        '0x94c818726678d40173c59c6876cd2c7a696e13fc703354a221a169372ddad33c154b5ada3da37078536a099ce85e20c3': 1763,
        '0xacee82e6b730f807d870025040f9df1c0decb778fa5fd064c782a95fdd702513ed1a63fb8fd24c039597a7d17abc4aeb': 1764,
        '0xb86e79a44093ac32ad6c3f54944c1f6fe90f4f11dc007c0b0af4b454cb3d93ff336efb3c4dfde940353bbd8f9a296b99': 1765,
        '0xa5a8aa7f3b1ccd67a9c9664f520a7032568a5b7e740e2fbb5835c9d10a1a9fd541df2e0e156552e91773e6aa1500fcde': 1766,
        '0xa10192cc9a2b36f06ccf448580818824cf0151b19307856eb3ea723fdb48436a517e4837dddd3eab271281b6901e17f9': 1767,
        '0x82ac9ff21fe7436e8ee69a0dea42fc8c3568000326d5afb2d60adf6af170356a1be2b1c71bff41f49b76e7360eeb1ae6': 1768,
        '0xa9b4d0a8d7a989fb634bc383374f05495977a2e972787d9164571d0012a19e0dee1bd7923443070c83eb74b944ec0d12': 1769,
        '0xb90b9a70f8a3bc1581a659e3a388a2de775489e0dc391f0aedbed1bce3a159efd919f1229f49fe8767ffe54c4f64af81': 1770,
        '0x909559af31acfb3ef45c70da2579b14cb9c41f26209dde95b71adbf7d8d8b99a6522a2d21d21c6fde5332abb0780fa2f': 1771,
        '0x82e85f6e0fe7021d22c7d568f65be4fa63ee3a60b14d02a6f3342fbfb528b82227de4c7e67fcd4dd44ff9b9bf0a67b12': 1772,
        '0x993e8492c9cf30241bbf4a53ea8b7a4c05b8ac47f4b0dfdfd76a4fcccaeefc27cc21d4dab9229073ae55755f5c2eb36f': 1773,
        '0x87b5be6f34eb7cc9352f68b72e4287a7757f87070d49bfc7474df867839cda1301ec4b62a423b66bf3af4ddbe310f00e': 1774,
        '0xa3e175607942783647a00ec545154e9bf16df021559e222ab876e0a5e6ee9048af696c6df07b43662fd2939240d60da6': 1775,
        '0xa19480a00eb92c2e2eec2e897b401efe2a17daa35b6214dd853b91b88be932d0fd05ecbe2ade7fe6012b1272bb0735d0': 1776,
        '0x8f807e2f9978ae83158fb37c03a6d7fd3d5a0fa5ada83dbd4b25f9b4feae1a21affb23ff59170a676d526de95a2dd356': 1777,
        '0xb7b91490c1b2b6a9c9a00942c20bd052b6f33a24de65927fe67ea8ccdf288bbba4f3f9af4bf0e05e2cc1177d7fd042a6': 1778,
        '0x8c87a5a869c60141717c4a30f31da5dec7b8f6d43639b3f9616f2d7f7a8f884eb84d2ee6a60401aae0b9d0c2c86a51dd': 1779,
    }

    print('Script for checking correct keys shift after duplicates removal')
    pp('Operator Name', operator_name)
    pp('Operator address', operator_address)

    assert node_operator_name == operator_name

    start_index = 1700

    signing_keys = get_signing_keys(node_operator_id, registry, True, start_index)
    duplicated_signing_keys = find_last_duplicated_signing_keys(signing_keys)
    assert len(duplicated_signing_keys) == 0

    removed_qty = len(pubkeys_shifted_to_new_indexes)

    last_signing_keys = signing_keys[-removed_qty:]

    for signing_key in last_signing_keys:
        assert signing_key.get('index') == pubkeys_shifted_to_new_indexes[str(signing_key.get('key'))]
