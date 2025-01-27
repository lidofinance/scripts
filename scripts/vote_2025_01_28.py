"""
Voting 28/01/2025.

I. CSM: Enable Permissionless Phase and Increase the Share Limit
1. Grant MODULE_MANAGER_ROLE on CS Module to Aragon Agent
2. Activate public release mode on CS Module
3. Increase the stake share limit from 1% to 2% and the priority exit threshold from 1.25% to 2.5% on CS Module
4. Revoke MODULE_MANAGER_ROLE on CS Module from Aragon Agent

II. NO Acquisitions: Bridgetower is now part of Solstice Staking
5. Rename Node Operator ID 17 from BridgeTower to Solstice

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

from utils.csm import activate_public_release

from utils.agent import agent_forward

description = """
1. **Transition Community Staking Module to Permissionless Phase** by activating public release and **increasing the share limit** from 1% to 2%, as [approved on Snapshot](https://snapshot.org/#/s:lido-snapshot.eth/proposal/0x7cbd5e9cb95bda9581831daf8b0e72d1ad0b068d2cbd3bda2a2f6ae378464f26). Alongside the share limit, [it is proposed](https://research.lido.fi/t/community-staking-module/5917/86) to **raise the priority exit share threshold **from 1.25% to 2.5% to maintain parameter ratios. Items 1-4.

2. **Rename Node Operator ID 17 from BridgeTower to Solstice** as [requested on the forum](https://research.lido.fi/t/node-operator-registry-name-reward-address-change/4170/41). Item 5.
"""

def start_vote(tx_params: Dict[str, str], silent: bool) -> bool | list[int | TransactionReceipt | None]:
    """Prepare and run voting."""
    voting: interface.Voting = contracts.voting
    csm: interface.CSModule = contracts.csm
    staking_router: interface.StakingRouter = contracts.staking_router
    csm_module_id = 3
    new_stake_share_limit = 200 #2%
    new_priority_exit_share_threshold = 250 #2.5%
    old_staking_module_fee = 600
    old_treasury_fee = 400
    old_max_deposits_per_block = 30
    old_min_deposit_block_distance = 25

    vote_desc_items, call_script_items = zip(
        #
        # I. CSM: Enable Permissionless Phase and Increase the Share Limit
        #
        (
            "1. Grant MODULE_MANAGER_ROLE on CS Module to Aragon Agent",
            agent_forward(
                [
                    encode_oz_grant_role(csm, "MODULE_MANAGER_ROLE", contracts.agent)
                ]
            ),
        ),
        (
            "2. Activate public release mode on CS Module",
            agent_forward(
                [
                    activate_public_release(csm.address)
                ]
            ),
        ),
        (
            "3. Increase the stake share limit from 1% to 2% and the priority exit threshold from 1.25% to 2.5% on CS Module",
            agent_forward(
                [
                    update_staking_module(csm_module_id, new_stake_share_limit, new_priority_exit_share_threshold,
                                          old_staking_module_fee, old_treasury_fee, old_max_deposits_per_block,
                                          old_min_deposit_block_distance)
                ]
            ),
        ),
        (
            "4. Revoke MODULE_MANAGER_ROLE on CS Module from Aragon Agent",
            agent_forward(
                [
                    encode_oz_revoke_role(csm, "MODULE_MANAGER_ROLE", revoke_from=contracts.agent)
                ]
            ),
        ),
        #
        # II. NO Acquisitions:  Bridgetower is now part of Solstice Staking
        #
        (
            "5. Rename Node Operator ID 17 from BridgeTower to Solstice",
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

def update_staking_module(staking_module_id, stake_share_limit,
                          priority_exit_share_threshold, staking_module_fee,
                          treasury_fee, max_deposits_per_block,
                          min_deposit_block_distance) -> Tuple[str, str]:
    return (contracts.staking_router.address,  contracts.staking_router.updateStakingModule.encode_input(
        staking_module_id, stake_share_limit, priority_exit_share_threshold, staking_module_fee,
        treasury_fee, max_deposits_per_block, min_deposit_block_distance
    ))
