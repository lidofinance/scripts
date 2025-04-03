from brownie import web3
from utils.config import contracts
from enum import IntEnum

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
        module["stakeShareLimit"] * share_multiplier,
        module["priorityExitShareThreshold"] * share_multiplier,
        module["stakingModuleFee"],
        module["treasuryFee"],
        module["maxDepositsPerBlock"],
        module["minDepositBlockDistance"],
        {"from": contracts.agent},
    )
