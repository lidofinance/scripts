from brownie import web3
from utils.config import contracts
from enum import IntEnum

class StakingModuleStatus(IntEnum):
    Active = 0
    DepositsPaused = 1
    Stopped = 2

def set_staking_module_status(module_id, staking_module_status: StakingModuleStatus):
    contracts.staking_router.setStakingModuleStatus(module_id, staking_module_status, {"from": contracts.agent})
