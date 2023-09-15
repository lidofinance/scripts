"""
Voting 164 12/09/2023
Vote REJECTED
"""

import time

from typing import Dict

from brownie.network.transaction import TransactionReceipt
from brownie import web3, interface  # type: ignore
from utils.agent import agent_forward

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)

from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

description = """
The proposal is to support **Jump Crypto voluntarily exits from the validator set** by setting `targetValidatorsCount` to 0.
Algorithm would prioritise exiting Jump Crypto validators in order to fulfil users' withdrawals requests.
Jump Crypto request on [forum](https://research.lido.fi/t/lido-dao-proposal-to-set-targetvalidatorscount-for-jump-crypto-operator-to-0-to-wind-down-the-jump-crypto-legacy-set/5259).
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    # contracts.node_operators_registry.getNodeOperator(1, True)
    JUMP_CRYPTO_ID = 1
    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    call_script_items = [
        # 1. Support **Jump Crypto voluntarily exits from the validator set** by setting `targetValidatorsCount` to 0.
        ## 1) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(
                        STAKING_MODULE_MANAGE_ROLE, contracts.agent.address
                    ),
                )
            ]
        ),
        ## 2) Set Jump Crypto targetValidatorsCount to 0
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, JUMP_CRYPTO_ID, True, 0),
                )
            ]
        ),
    ]

    vote_desc_items = [
        f"1) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent",
        f"2) Set Jump Crypto targetValidatorsLimits to 0",
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
