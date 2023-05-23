"""
Voting 23/05/2023

1) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
2) Set Anyblock Analytics targetValidatorsCount to 0
3) Renounce STAKING_MODULE_MANAGE_ROLE from Lido Agent
4) Fund the reWARDS committee for June 2023 with 170 stETH
5) Increase Easy Track motions amount limit: set motionsCountLimit to 20

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

    ANYBLOCK_ANALYTICS_ID = 12
    STAKING_MODULE_MANAGE_ROLE = "0x3105bcbf19d4417b73ae0e58d508a65ecf75665e46c2622d8521732de6080c48"

    motionsCountLimit = 20

    REWARDS_MULTISIG_ADDRESS = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
    REWARDS_JUNE_BUDGET = 170*1e18

    call_script_items = [
        # Set Anyblock Analytics targetValidatorsCount to 0

        ## Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.grantRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),
        ## Set Anyblock Analytics targetValidatorsCount to 0
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.updateTargetValidatorsLimits.encode_input(1, ANYBLOCK_ANALYTICS_ID, True, 0),
                )
            ]
        ),
        ## Renounce STAKING_MODULE_MANAGE_ROLE
        agent_forward(
            [
                (
                    contracts.staking_router.address,
                    contracts.staking_router.renounceRole.encode_input(STAKING_MODULE_MANAGE_ROLE, contracts.agent.address),
                )
            ]
        ),

        # Send the reWARDS June payment
        make_steth_payout(
            target_address=REWARDS_MULTISIG_ADDRESS,
            steth_in_wei=REWARDS_JUNE_BUDGET,
            reference='reWARDS June 2023 budget'
        ),

        # Set max EasyTrack motions limit to 20
        set_motions_count_limit(motionsCountLimit),
    ]

    vote_desc_items = [
        "1) Grant STAKING_MODULE_MANAGE_ROLE to Lido Agent",
        "2) Set Anyblock Analytics targetValidatorsCount to 0",
        "3) Renounce STAKING_MODULE_MANAGE_ROLE from Lido Agent",
        "4) Fund the reWARDS committee for June 2023 with 170 stETH",
        "5) Increase Easy Track motions amount limit: set motionsCountLimit to 20",
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
