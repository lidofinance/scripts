from utils.config import contracts
from enum import Enum


class ModuleStatus(Enum):
    ACTIVE = 0
    PAUSED = 1
    DISABLED = 2


def pause_staking_module(module_id):
    staking_router, deposit_security_module = contracts.staking_router, contracts.deposit_security_module

    pause_tx = staking_router.pauseStakingModule(module_id, {"from": deposit_security_module})
    pause_event = pause_tx.events["StakingModuleStatusSet"]
    assert pause_event["stakingModuleId"] == module_id
    assert pause_event["status"] == ModuleStatus.PAUSED.value
