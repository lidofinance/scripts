from typing import Dict, Tuple, List, NamedTuple
from brownie import  reverts  # type: ignore
from brownie import convert
from web3 import Web3

from utils.config import (
    contracts,
)

def add_node_operator(staking_module, voting, stranger):
    operator_id = staking_module.getNodeOperatorsCount()

    with reverts("APP_AUTH_FAILED"):
        staking_module.addNodeOperator("test", f"0xbb{str(1).zfill(38)}", {"from": stranger} )

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        {"from": voting},
    )

    staking_module.addNodeOperator("test", f"0xbb{str(1).zfill(38)}", {"from": stranger} )

    return operator_id


def calc_module_reward_shares(module_id, shares_minted_as_fees):
    distribution = contracts.staking_router.getStakingRewardsDistribution()
    module_idx = distribution[1].index(module_id)
    return distribution[2][module_idx] * shares_minted_as_fees // distribution[3]

def update_staking_module(staking_module_id, stake_share_limit,
                          priority_exit_share_threshold, staking_module_fee,
                          treasury_fee, max_deposits_per_block,
                          min_deposit_block_distance) -> Tuple[str, str]:
    return (contracts.staking_router.address,  contracts.staking_router.updateStakingModule.encode_input(
        staking_module_id, stake_share_limit, priority_exit_share_threshold, staking_module_fee,
        treasury_fee, max_deposits_per_block, min_deposit_block_distance
    ))
