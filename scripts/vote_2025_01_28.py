"""
Voting 28/01/2025.

I. Community staking module: limit increase + turn off EA mode
1. Grant MODULE_MANAGER_ROLE
2. Activate public release mode
3. Grant STAKING_MODULE_MANAGE_ROLE
4. Increase share from 1% to 2%
5. Revoke MODULE_MANAGER_ROLE
6. Revoke STAKING_MODULE_MANAGE_ROLE

II. NO Acquisitions - Bridgetower is now part of Solstice Staking
1. Change name of Bridgetower to Solstice

"""

import time

from typing import Dict, Tuple, Optional, List

from brownie import interface
from brownie.network.transaction import TransactionReceipt
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.permissions import (
    encode_oz_revoke_role,
    encode_oz_grant_role
)

from utils.node_operators import encode_set_node_operator_name

from utils.config import (
    get_deployer_account,
    contracts,
    get_is_live,
    get_priority_fee,
)

from utils.staking_module import update_staking_module

from utils.csm import activate_public_release

from utils.agent import agent_forward

description = """
1. **Community staking module**: limit increase + turn off EA mode

2. **NO Acquisitions** - Bridgetower is now part of Solstice Staking
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""
    voting: interface.Voting = contracts.voting
    csm: interface.CSModule = contracts.csm
    staking_router: interface.StakingRouter = contracts.staking_router
    csm_module_id = 3
    new_stake_share_limit = 200

    vote_desc_items, call_script_items = zip(
        #
        # I. Community staking module: limit increase + turn off EA mode
        #
        (
            "1. Grant MODULE_MANAGER_ROLE",
            encode_oz_grant_role(csm, "MODULE_MANAGER_ROLE", voting)
        ),
        (
            "2. Activate public release mode",
            agent_forward(
                [
                    activate_public_release(csm.address)
                ]
            ),
        ),
        (
            "3. Grant STAKING_MODULE_MANAGE_ROLE",
            encode_oz_grant_role(staking_router, "STAKING_MODULE_MANAGE_ROLE", voting)
        ),
        (
            "4. Increase share from 1% to 2%",
            agent_forward(
                [
                    update_staking_module(csm_module_id, new_stake_share_limit, 125, 600, 400, 30, 25)
                ]
            ),
        ),
        (
            "5. Revoke MODULE_MANAGER_ROLE",
            encode_oz_revoke_role(csm, "MODULE_MANAGER_ROLE", revoke_from=voting)
        ),
        (
            "6. Revoke STAKING_MODULE_MANAGE_ROLE",
            encode_oz_revoke_role(staking_router, "STAKING_MODULE_MANAGE_ROLE", voting)
        ),
        #
        # II. NO Acquisitions - Bridgetower is now part of Solstice Staking
        #
        (
            "1. Change name of Bridgetower to Solstice",
            agent_forward(
                [
                    encode_set_node_operator_name(
                        id=17, name="Solstice", registry=contracts.node_operators_registry
                    ),
                ]
            ),
        ),
    )

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
