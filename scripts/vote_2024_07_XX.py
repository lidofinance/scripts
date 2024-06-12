"""
Voting XX/07/2024.

1. Update LidoLocator to new instance 0x1234567890123456789012345678901234567890

Vote passed & executed on XX-XX-2024 XX:XX:XX PM +UTC, block XXXXXXXX.
"""

import time

from typing import Dict
from brownie.network.transaction import TransactionReceipt
from brownie import interface
from utils.agent import agent_forward
from utils.shapella_upgrade import get_tx_params
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    LIDO_LOCATOR_IMPL,
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
    get_max_fee,
)

description = """
Update LidoLocator
"""

def get_tx_params(deployer):
    tx_params = {"from": deployer}
    tx_params["priority_fee"] = "10 gwei"

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()
        tx_params["max_fee"] = get_max_fee()
    return tx_params


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    deployer = get_deployer_account()
    print("==== deployer", deployer)

    tx_params2 = get_tx_params(deployer)

    vote_desc_items, call_script_items = zip(
        (
            "1) Update LidoLocator",
            agent_forward(
            [
                (
                    contracts.lido_locator.address,
                    interface.OssifiableProxy(contracts.lido_locator).proxy__upgradeTo.encode_input(
                        LIDO_LOCATOR_IMPL
                    ),
                )
            ]
            )
        )
    )
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    if silent:
        desc_ipfs = calculate_vote_ipfs_description(description)
    else:
        desc_ipfs = upload_vote_ipfs_description(description)


    print("==== get_tx_params", tx_params, tx_params2)

    return confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params2, desc_ipfs=desc_ipfs)
    )


def main():
    tx_params = {"from": get_deployer_account()}
    # print("==== deployer FIRST ", get_deployer_account())

    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=True)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
