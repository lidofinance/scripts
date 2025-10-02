import math

from brownie import ZERO_ADDRESS, accounts, web3

from utils.test.helpers import ETH
from utils.config import contracts

NODE_OPERATORS_REGISTRY_ID = 1
WEI_TOLERANCE = 5  # wei tolerance to avoid rounding issue


def fill_deposit_buffer(deposits_count, heuristic=1):
    deposit_size = ETH(32)
    depositable_eth = deposits_count * deposit_size * heuristic

    cover_wq_demand_and_submit(depositable_eth)

def cover_wq_demand_and_submit(depositable_eth):
    staking_router, lido, withdrawal_queue = contracts.staking_router, contracts.lido, contracts.withdrawal_queue

    buffered_ether_before_submit = lido.getBufferedEther()
    withdrawal_unfinalized_steth = withdrawal_queue.unfinalizedStETH()

    eth_debt = max(0, withdrawal_unfinalized_steth - buffered_ether_before_submit)
    eth_to_submit = depositable_eth + eth_debt + WEI_TOLERANCE

    eth_whale = accounts.at(staking_router.DEPOSIT_CONTRACT(), force=True)

    (
        is_staking_paused,
        is_staking_limit_set,
        current_stake_limit,
        max_stake_limit,
        max_stake_limit_growth_blocks,
        _,
        _
    ) = lido.getStakeLimitFullInfo()

    is_limit_reached = is_staking_limit_set and current_stake_limit < eth_to_submit

    assert not is_staking_paused, "Staking is paused"

    contracts.acl.grantPermission(
        contracts.agent,
        contracts.lido,
        web3.keccak(text="STAKING_CONTROL_ROLE"),
        {"from": contracts.agent}
    )

    if is_limit_reached:
        lido.removeStakingLimit({"from": contracts.agent})

    lido.submit(ZERO_ADDRESS, {"from": eth_whale, "value": eth_to_submit})

    if is_limit_reached:
        stake_limit_increase_per_block = max_stake_limit // max_stake_limit_growth_blocks
        lido.setStakingLimit(max_stake_limit, stake_limit_increase_per_block, {"from": contracts.agent})

    contracts.acl.revokePermission(
        contracts.agent,
        contracts.lido,
        web3.keccak(text="STAKING_CONTROL_ROLE"),
        {"from": contracts.agent}
    )

    assert lido.getDepositableEther() > depositable_eth

def drain_remained_buffered_ether():
    depositable_ether = math.floor(contracts.lido.getDepositableEther() / 10**18)

    while depositable_ether > 32:
        contracts.lido.deposit(100, NODE_OPERATORS_REGISTRY_ID, "0x0", {"from": contracts.deposit_security_module})
        depositable_ether = math.floor(contracts.lido.getDepositableEther() / 10**18)
