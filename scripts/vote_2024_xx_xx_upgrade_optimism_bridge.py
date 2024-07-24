"""
Voting xx/xx/2024.

Upgrade L1Bridge, L2Bridge, L2 wstETH, L2 stETH, TokenRateOracle

"""

import time
import eth_abi
from brownie import interface, accounts
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import agent_forward
from tests.conftest import Helpers
from utils.config import (
    contracts,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    get_gas_price,
    network_name,
    AGENT
)
from configs.config_sepolia import (
    L1_TOKENS_BRIDGE_PROXY,
    L1_TOKENS_BRIDGE_NEW_IMPL,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL_UPGRADE,
    L1_EMERGENCY_BRAKES_MULTISIG,
    L2_TOKENS_BRIDGE_PROXY,
    L2_TOKENS_BRIDGE_NEW_IMPL,
    L2_OPTIMISM_BRIDGE_EXECUTOR,
    L2_OPTIMISM_WSTETH_TOKEN,
    L2_OPTIMISM_WSTETH_TOKEN_NEW_IMPL,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
)

description = """

Upgrade L1Bridge, L2Bridge, L2 wstETH

"""


DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"


def encode_l2_upgrade_call(proxy1: str, new_impl1: str, proxy2: str, new_impl2: str):
    govBridgeExecutor = interface.OpBridgeExecutor(L2_OPTIMISM_BRIDGE_EXECUTOR)

    return govBridgeExecutor.queue.encode_input(
        [proxy1, proxy2],
        [0, 0],
        ["proxy__upgradeTo(address)", "proxy__upgradeTo(address)"],
        [
            eth_abi.encode(["address"], [new_impl1]),
            eth_abi.encode(["address"], [new_impl2]),
        ],
        [False, False],
    )


def encode_l1_l2_sendMessage(to: str, calldata: str):
    print(calldata)
    l1_l2_msg_service = interface.OpCrossDomainMessenger(L1_OPTIMISM_CROSS_DOMAIN_MESSENGER)
    min_gas_limit = 1_000_000
    return l1_l2_msg_service.sendMessage.encode_input(to, calldata, min_gas_limit)


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    if not network_name() in ("sepolia", "sepolia-fork"):
        return

    lido_locator_as_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    l1_token_bridge_as_proxy = interface.OssifiableProxy(L1_TOKENS_BRIDGE_PROXY)
    l1_token_bridge = interface.AccessControl(L1_TOKENS_BRIDGE_PROXY)

    call_script_items = [
        # 1. L1 Bridge
        agent_forward(
            [
                (
                    l1_token_bridge_as_proxy.address,
                    l1_token_bridge_as_proxy.proxy__upgradeTo.encode_input(L1_TOKENS_BRIDGE_NEW_IMPL),
                )
            ]
        ),
        # 1. L1 Bridge
        agent_forward(
            [
                (
                    lido_locator_as_proxy.address,
                    lido_locator_as_proxy.proxy__upgradeTo.encode_input(LIDO_LOCATOR_IMPL_UPGRADE),
                )
            ]
        ),
        # Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
        agent_forward(
            [
                (
                    l1_token_bridge.address,
                    l1_token_bridge.grantRole.encode_input(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG),
                )
            ]
        ),
        # 2. L2 Bridge
        agent_forward(
            [
                (
                    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
                    encode_l1_l2_sendMessage(
                        L2_OPTIMISM_BRIDGE_EXECUTOR,
                        encode_l2_upgrade_call(
                            L2_TOKENS_BRIDGE_PROXY,
                            L2_TOKENS_BRIDGE_NEW_IMPL,
                            L2_OPTIMISM_WSTETH_TOKEN,
                            L2_OPTIMISM_WSTETH_TOKEN_NEW_IMPL,
                        ),
                    ),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Upgrade L1 Bridge implementation",
        "2) Upgrade L1 LidoLocator implementation",
        "3) Grant DEPOSITS_ENABLER_ROLE to Emergency Brakes Committee multisig",
        "4) Send L2 upgrade call: (a) upgrade L2TokenBridge; (b) upgrade wstETH on L2",
    ]

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

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

def startAndExecuteForForkUpgrade():
    depoyerAccount = get_deployer_account()

    # Top up accounts
    accountWithEth = accounts.at('0x4200000000000000000000000000000000000023', force=True)
    accountWithEth.transfer(depoyerAccount.address, "1 ethers", gas_price=get_gas_price())
    accountWithEth.transfer(AGENT, "1 ethers", gas_price=get_gas_price())

    tx_params = {"from": depoyerAccount, "gas_price": get_gas_price()}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    vote_tx = Helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.