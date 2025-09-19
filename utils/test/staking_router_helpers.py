from brownie import web3
from utils.config import contracts
from enum import IntEnum

TOTAL_BASIS_POINTS = 10_000


class StakingModuleStatus(IntEnum):
    Active = 0
    DepositsPaused = 1
    Stopped = 2


def set_staking_module_status(module_id, staking_module_status: StakingModuleStatus):
    contracts.staking_router.setStakingModuleStatus(module_id, staking_module_status, {"from": contracts.agent})


def increase_staking_module_share(module_id, share_multiplier):
    module = contracts.staking_router.getStakingModule(module_id)

    contracts.staking_router.updateStakingModule(
        module_id,
        min(module["stakeShareLimit"] * share_multiplier, TOTAL_BASIS_POINTS),
        min(module["priorityExitShareThreshold"] * share_multiplier, TOTAL_BASIS_POINTS),
        module["stakingModuleFee"],
        module["treasuryFee"],
        module["maxDepositsPerBlock"],
        module["minDepositBlockDistance"],
        {"from": contracts.agent},
    )
