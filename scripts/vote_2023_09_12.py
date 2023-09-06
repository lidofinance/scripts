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

from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    contracts,
)

from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description

description = """
The **Omnibus vote** contain two motions:
1. Decrease an Easy Track limit for TRP Committee multisig to 9,277,540 LDO, [proposed on the forum](https://research.lido.fi/t/request-to-authorise-a-22m-ldo-ceiling-for-a-four-year-contributor-token-reward-plan-trp/3833/22) (items 1, 2);
2. Support **Jump Crypto voluntarily exits from the validator set** by setting `targetValidatorsCount` to 0. Jump Crypto requested it [here](https://research.lido.fi/t/lido-dao-proposal-to-set-targetvalidatorscount-for-jump-crypto-operator-to-0-to-wind-down-the-jump-crypto-legacy-set/5259) (items 3,4).
"""


def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""

    # contracts.node_operators_registry.getNodeOperator(1, True)
    JUMP_CRYPTO_ID = 1
    # web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    TOKEN_REWARDS_PLAN_ADDRESS = "0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8"

    trp_registry = interface.AllowedRecipientRegistry(TOKEN_REWARDS_PLAN_ADDRESS)
    trp_ldo_limit = 9_277_540 * (10**18)
    call_script_items = [
        # 1. Decrease an Easy Track limit for TRP Committee multisig to 9,277,540 LDO
        ## Set limit for Easy Track TRP registry
        agent_forward(
            [
                (
                    trp_registry.address,
                    trp_registry.setLimitParameters.encode_input(trp_ldo_limit, 12),
                )
            ]
        ),
        #
        agent_forward(
            [
                (
                    trp_registry.address,
                    trp_registry.unsafeSetSpentAmount.encode_input(0),
                )
            ]
        ),
        # 2. Support **Jump Crypto voluntarily exits from the validator set** by setting `targetValidatorsCount` to 0.
        ## Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
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
        ## Set Anyblock Analytics targetValidatorsCount to 0
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, JUMP_CRYPTO_ID, True, 0),
                )
            ]
        ),
        ## Renounce STAKING_MODULE_MANAGE_ROLE
        # agent_forward(
        #     [
        #         (
        #             contracts.staking_router.address,
        #             contracts.staking_router.renounceRole.encode_input(STAKING_MODULE_MANAGE_ROLE,
        #                                                                contracts.agent.address),
        #         )
        #     ]
        # ),
    ]

    vote_desc_items = [
        f"1) Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 9277540000000000000000000",
        f"2) Set send amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0",
        f"3) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent",
        f"4) Set Jump Crypto targetValidatorsLimits to 0",
        # f"5) Renounce STAKING_MODULE_MANAGE_ROLE from Lido Agent",
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
