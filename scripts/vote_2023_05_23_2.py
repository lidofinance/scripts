"""
Voting 23/05/2023 — take 2.

. Burn 13.45978634 stETHs as cover

. Set Anyblocks Analytics key limit to 0

. Send 170 stETH to reWARDS 0x87D93d9B2C672bf9c9642d853a8682546a5012B5

. Increase Easy Track motions amount limit: set motionsCountLimit to 20

"""

import time

from typing import Dict, Tuple, Optional

from brownie.network.transaction import TransactionReceipt
from brownie import web3  # type: ignore
from utils.agent import agent_forward
from utils.finance import make_steth_payout

from utils.voting import bake_vote_items, confirm_vote_script, create_vote

from utils.config import (
    get_deployer_account,
    get_is_live,
    contracts,
    STAKING_ROUTER,
    WITHDRAWAL_VAULT,
    WITHDRAWAL_VAULT_IMPL,
    SELF_OWNED_STETH_BURNER,
    get_priority_fee,
)

from utils.easy_track import (
    set_motions_count_limit
)

def start_vote(tx_params: Dict[str, str], silent: bool) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    # Burn 13.45978634 stETHs as cover
    stETH_to_burn = 13.45978634 * 1e18
    REQUEST_BURN_MY_STETH_ROLE = "0x28186f938b759084eea36948ef1cd8b40ec8790a98d5f1a09b70879fe054e5cc"

    # Set Anyblocks Analytics key limit to 0

    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    # Send 170 stETH to reWARDS 0x87D93d9B2C672bf9c9642d853a8682546a5012B5    

    # 1 Increase Easy Track motions amount limit
    motionsCountLimit = 20
    

    call_script_items = [
        # Burn 13.45978634 stETHs as cover
        agent_forward(
            [
                (
                    contracts.insurance_fund.address,
                    contracts.insurance_fund.transferERC20.encode_input(contracts.lido.address, contracts.agent.address, stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.lido.address,
                    contracts.lido.approve.encode_input(contracts.burner.address, stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.grantRole.encode_input(REQUEST_BURN_MY_STETH_ROLE, contracts.agent.address),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.requestBurnMyStETHForCover.encode_input(stETH_to_burn),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.burner.address,
                    contracts.burner.renounceRole.encode_input(REQUEST_BURN_MY_STETH_ROLE, contracts.agent.address),
                )
            ]
        ),

        # # Set Anyblocks Analytics key limit to 0

        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, 12, True, 0),
                )
            ]
        ),
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.renounceRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),

        # reWARDS payment
        make_steth_payout(
            target_address='0x87D93d9B2C672bf9c9642d853a8682546a5012B5',
            steth_in_wei=170*1e18,
            reference='reWARDS June 2023 budget'
        ),
        
        # 
        set_motions_count_limit(motionsCountLimit),
    ]

    vote_desc_items = [
        "ururu1",
        "ururu2",
        "ururu3",
        "ururu4",
        "ururu5",
        "ururu6",
        "ururu7",
        "ururu8",
        "ururu9",
        "Increase Easy Track motions amount limit: set motionsCountLimit to 20",
    ]

    vote_items = bake_vote_items(vote_desc_items, call_script_items)

    return confirm_vote_script(vote_items, silent) and list(create_vote(vote_items, tx_params))


def main():
    tx_params = {"from": get_deployer_account()}

    if get_is_live():
        tx_params["max_fee"] = "300 gwei"
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)

    vote_id >= 0 and print(f"Vote created: {vote_id}.")

    time.sleep(5)  # hack for waiting thread #2.
