"""
Rollback voting if L2 part of the upgrade failed.

TODO

"""

import time
import eth_abi
from brownie import interface, web3
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import agent_forward
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    L1_OPTIMISM_CROSS_DOMAIN_MESSENGER,
    L1_EMERGENCY_BRAKES_MULTISIG,
    LIDO_LOCATOR,
    LIDO_LOCATOR_IMPL,
    L1_OPTIMISM_TOKENS_BRIDGE,
    L1_OPTIMISM_TOKENS_BRIDGE_IMPL,
)


DESCRIPTION = """

Upgrade back L1Bridge, LidoLocator and revokeRole for deposit pause on L1Bridge

"""

DEPOSITS_ENABLER_ROLE = "0x4b43b36766bde12c5e9cbbc37d15f8d1f769f08f54720ab370faeb4ce893753a"

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    l1_token_bridge_as_proxy = interface.OssifiableProxy(L1_OPTIMISM_TOKENS_BRIDGE)
    lido_locator_as_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    call_script_items = [
        # 1. L1 TokenBridge upgrade proxy
        agent_forward(
            [
                (
                    l1_token_bridge_as_proxy.address,
                    l1_token_bridge_as_proxy.proxy__upgradeTo.encode_input(L1_OPTIMISM_TOKENS_BRIDGE_IMPL),
                )
            ]
        ),
        # 2. Rollback L1 LidoLocator implementation
        agent_forward(
            [
                (
                    lido_locator_as_proxy.address,
                    lido_locator_as_proxy.proxy__upgradeTo.encode_input(LIDO_LOCATOR_IMPL),
                )
            ]
        ),
        # 3. Revoke DEPOSITS_ENABLER_ROLE for Emergency Brakes Committee multisig
        agent_forward(
            [
                (
                    l1_token_bridge.address,
                    l1_token_bridge.revokeRole.encode_input(DEPOSITS_ENABLER_ROLE, L1_EMERGENCY_BRAKES_MULTISIG),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Rollback Optimism L1 Bridge implementation",
        "2) Upgrade LidoLocator implementation",
        "3) Revoke DEPOSITS_ENABLER_ROLE from Emergency Brakes Committee multisig",
    ]

    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(DESCRIPTION)
    else:
        desc_ipfs = upload_vote_ipfs_description(DESCRIPTION)

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
