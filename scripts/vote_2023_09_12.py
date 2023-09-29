"""
Voting {id} 12/09/2023
Vote {rejected | passed & executed} on ${date+time}, block ${blockNumber}
"""

import time

from typing import Dict

from brownie.network.transaction import TransactionReceipt
from brownie import web3, interface  # type: ignore
from utils.agent import agent_forward

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.permissions import encode_permission_revoke, encode_permission_create
from utils.easy_track import add_evmscript_factory
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)

from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

description = """
Init staking module
grant MANAGE_NODE_OPERATOR_ROLE for committee",
grant MANAGE_NODE_OPERATOR_ROLE for et executor",
"2) grant SET_NODE_OPERATOR_LIMIT_ROLE for et executor",
"2) grant MANAGE_SIGNING_KEYS for et executor",
"2) grant STAKING_ROUTER_ROLE for et executor",
"AddNodeOperators deployed at: 0x083a26e5285610b91Fd74040B81C9b5a13523bbf",
"ActivateNodeOperators deployed at: 0x7983F6879C0C06a9718bAf90e6E0ebD3e7243A3F",
"DeactivateNodeOperators deployed at: 0x47a8C2f54513d1d2445Ced353237F4ed406d16f2",
"IncreaseVettedValidatorsLimit deployed at: 0xA7AFa4E0Ce9d2A50C96Fe770D3cDd3259DAc0D76",
"SetVettedValidatorsLimits deployed at: 0xB634357735a3b63645b54A2D928CE1b09caffC9d",
"SetNodeOperatorNames deployed at: 0x827e3C09A6044afF2f5cF78BB064bB8a40B4C13F",
"SetNodeOperatorRewardAddresses deployed at: 0x2e565f073FeBD66cb24dD9CA66Bffe6CeFd0B7Af",
"TransferNodeOperatorManager deployed at: 0x8A33BA98C7165BDb61af1468fd5BD8aF22B3d87d",
"RenounceManageSigningKeysRoleManager deployed at: 0xd3218b08cbB921908C41A74E79D7Ca2672B51f3E",
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    # contracts.node_operators_registry.getNodeOperator(1, True)
    JUMP_CRYPTO_ID = 1
    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"
    
    module_name = "simple-dvt-registry"
    name = web3.keccak(text=module_name).hex()

    call_script_items = [
        (
            "0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0",
            contracts.node_operators_registry.initialize.encode_input("0x1eDf09b5023DC86737b59dE68a8130De878984f5", "0x01", 0)
        ),
        encode_permission_create(entity="0xA28F6127269e85348735e5C6d5D5d0f37C893D3E", target_app="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0", permission_name='MANAGE_NODE_OPERATOR_ROLE', manager=contracts.voting),
        encode_permission_create(entity="0x3c9AcA237b838c59612d79198685e7f20C7fE783", target_app="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0", permission_name='MANAGE_NODE_OPERATOR_ROLE', manager=contracts.voting),
        encode_permission_create(entity="0x3c9AcA237b838c59612d79198685e7f20C7fE783", target_app="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0", permission_name='SET_NODE_OPERATOR_LIMIT_ROLE', manager=contracts.voting),
        encode_permission_create(entity="0x3c9AcA237b838c59612d79198685e7f20C7fE783", target_app="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0", permission_name='MANAGE_SIGNING_KEYS', manager=contracts.voting),
        encode_permission_create(entity="0x3c9AcA237b838c59612d79198685e7f20C7fE783", target_app="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0", permission_name='STAKING_ROUTER_ROLE', manager=contracts.voting),
        add_evmscript_factory(
            factory="0x083a26e5285610b91Fd74040B81C9b5a13523bbf",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.addNodeOperator.signature[2:] + contracts.acl.address[2:]+ contracts.acl.grantPermissionP.signature[2:]
        ),
        add_evmscript_factory(
            factory="0x7983F6879C0C06a9718bAf90e6E0ebD3e7243A3F",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.activateNodeOperator.signature[2:] + contracts.acl.address[2:]+ contracts.acl.grantPermissionP.signature[2:]
        ),
        add_evmscript_factory(
            factory="0x47a8C2f54513d1d2445Ced353237F4ed406d16f2",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.deactivateNodeOperator.signature[2:] + contracts.acl.address[2:]+ contracts.acl.revokePermission.signature[2:]
        ),
        add_evmscript_factory(
            factory="0xA7AFa4E0Ce9d2A50C96Fe770D3cDd3259DAc0D76",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.setNodeOperatorStakingLimit.signature[2:]
        ),
        add_evmscript_factory(
            factory="0xB634357735a3b63645b54A2D928CE1b09caffC9d",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.setNodeOperatorStakingLimit.signature[2:]
        ),
        add_evmscript_factory(
            factory="0x827e3C09A6044afF2f5cF78BB064bB8a40B4C13F",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.setNodeOperatorName.signature[2:]
        ),
        add_evmscript_factory(
            factory="0x2e565f073FeBD66cb24dD9CA66Bffe6CeFd0B7Af",
            permissions="0x6370FA71b9Fd83aFC4196ee189a0d348C90E93b0"+contracts.node_operators_registry.setNodeOperatorRewardAddress.signature[2:]
        ),
        add_evmscript_factory(
            factory="0x8A33BA98C7165BDb61af1468fd5BD8aF22B3d87d",
            permissions=contracts.acl.address+ contracts.acl.revokePermission.signature[2:] + contracts.acl.address[2:]+ contracts.acl.grantPermissionP.signature[2:]
        ),
        add_evmscript_factory(
            factory="0xd3218b08cbB921908C41A74E79D7Ca2672B51f3E",
            permissions=contracts.acl.address+ contracts.acl.removePermissionManager.signature[2:]
        ),
    ]

    vote_desc_items = [
        f"1) Init staking module",
            "2) grant MANAGE_NODE_OPERATOR_ROLE for committee",
            "2) grant MANAGE_NODE_OPERATOR_ROLE for et executor",
            "2) grant SET_NODE_OPERATOR_LIMIT_ROLE for et executor",
            "2) grant MANAGE_SIGNING_KEYS for et executor",
            "2) grant STAKING_ROUTER_ROLE for et executor",
            "AddNodeOperators deployed at: 0x083a26e5285610b91Fd74040B81C9b5a13523bbf",
            "ActivateNodeOperators deployed at: 0x7983F6879C0C06a9718bAf90e6E0ebD3e7243A3F",
            "DeactivateNodeOperators deployed at: 0x47a8C2f54513d1d2445Ced353237F4ed406d16f2",
            "IncreaseVettedValidatorsLimit deployed at: 0xA7AFa4E0Ce9d2A50C96Fe770D3cDd3259DAc0D76",
            "SetVettedValidatorsLimits deployed at: 0xB634357735a3b63645b54A2D928CE1b09caffC9d",
            "SetNodeOperatorNames deployed at: 0x827e3C09A6044afF2f5cF78BB064bB8a40B4C13F",
            "SetNodeOperatorRewardAddresses deployed at: 0x2e565f073FeBD66cb24dD9CA66Bffe6CeFd0B7Af",
            "TransferNodeOperatorManager deployed at: 0x8A33BA98C7165BDb61af1468fd5BD8aF22B3d87d",
            "RenounceManageSigningKeysRoleManager deployed at: 0xd3218b08cbB921908C41A74E79D7Ca2672B51f3E",
        
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
