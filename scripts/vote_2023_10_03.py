"""
Voting 03/10/2023.

1. Update Anchor Vault implementation from 0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171 to 0x26f15335BB1C6a4C0B660eDd694a0555A9F1cce3
2. Finalize Anchor Vault upgrade

Vote passed & executed on #, block #
"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.agent import agent_forward

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

ANCHOR_NEW_ADDRESS = "0x26f15335BB1C6a4C0B660eDd694a0555A9F1cce3"

def start_vote(tx_params: Dict[str, str], silent: bool = False) -> Tuple[int, Optional[TransactionReceipt]]:

    call_script_items = [
        # 1. Update Anchor Vault implementation
        agent_forward(
            [
                (
                    contracts.anchor_vault_proxy.address,
                    contracts.anchor_vault_proxy.proxy_upgradeTo.encode_input(ANCHOR_NEW_ADDRESS, b""),
                )
            ]
        )
        ,
        # 2. Finalize Anchor Vault upgrade
        agent_forward(
            [
                (
                    contracts.anchor_vault.address,
                    contracts.anchor_vault.finalize_upgrade_v4.encode_input(),
                )
            ]
        ),
    ]

    vote_desc_items = [
        "1) Update Anchor Vault implementation from 0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171 to 0x26f15335BB1C6a4C0B660eDd694a0555A9F1cce3",
        "2) Finalize Anchor Vault upgrade",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)
    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
