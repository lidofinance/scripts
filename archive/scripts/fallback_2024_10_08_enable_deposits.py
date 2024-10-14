"""
Fallback voting xx/xx/2024.

1. Enable deposits on Optimism L1 Token Bridge

"""
import time
from brownie import interface
from typing import Dict
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.agent import agent_forward
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    L1_OPTIMISM_TOKENS_BRIDGE,
)

description = """
Fallback voting xx/xx/2024.

Enable deposits on Optimism L1 Token Bridge

"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    l1_token_bridge = interface.L1LidoTokensBridge(L1_OPTIMISM_TOKENS_BRIDGE)

    call_script_items = [
        # 1. Enable deposits on Optimism L1 Token Bridge
        agent_forward([(l1_token_bridge.address, l1_token_bridge.enableDeposits.encode_input())]),
    ]

    vote_desc_items = [
        "1) Enable deposits on Optimism L1 Token Bridge",
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
