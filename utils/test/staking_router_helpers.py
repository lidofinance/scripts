from brownie import web3
from utils.config import contracts
from enum import IntEnum

class StakingModuleStatus(IntEnum):
    Active = 0
    DepositsPaused = 1
    Stopped = 2

new_staking_module_manager_address = "0xB871BB28d7e6Be4A373ed7a2DD6733a7423dC089"
staking_router_manager_role = web3.keccak(text="STAKING_MODULE_MANAGE_ROLE")

def set_staking_module_status(module_id, staking_module_status: StakingModuleStatus):
    if(not contracts.staking_router.hasRole(staking_router_manager_role, new_staking_module_manager_address)):
        contracts.staking_router.grantRole(
            staking_router_manager_role,
            new_staking_module_manager_address,
            {"from": contracts.agent},
        )

    contracts.staking_router.setStakingModuleStatus(module_id, staking_module_status, {"from": new_staking_module_manager_address})
