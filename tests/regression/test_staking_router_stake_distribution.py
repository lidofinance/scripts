from utils.config import contracts
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.staking_router_helpers import ModuleStatus


class Module:
    def __init__(self, id, target_share, status, active_keys, depositable_keys):
        self.id = id
        self.target_share = target_share
        self.status = status
        self.active_keys = active_keys
        self.depositable_keys = depositable_keys
        self.allocated_keys = 0
        self.allocation_limit = 0


def test_stake_distribution():
    """
    Test stake distribution among the staking modules
    1. checks that result of `getDepositsAllocation` matches the local allocation calculations
    2. checks that deposits to modules can be made according to the calculated allocation
    """
    lido, deposit_security_module = contracts.lido, contracts.deposit_security_module

    staking_router = contracts.staking_router
    module_digests = staking_router.getAllStakingModuleDigests()

    keys_to_allocate = 100  # keys to allocate to the modules
    allocation_from_contract = staking_router.getDepositsAllocation(keys_to_allocate)

    # collect the modules information

    modules = {}

    for digest in module_digests:
        (_, _, state, summary) = digest
        (id, _, _, _, target_share, status, _, _, _, _) = state
        (exited_keys, deposited_keys, depositable_keys) = summary

        active_keys = deposited_keys - exited_keys
        assert active_keys >= 0

        if status != ModuleStatus.ACTIVE.value:
            # reset depositable keys in case of module is inactivated
            # https://github.com/lidofinance/lido-dao/blob/331ecec7fe3c8d57841fd73ccca7fb1cc9bc174e/contracts/0.8.9/StakingRouter.sol#L1230-L1232
            depositable_keys = 0

        modules[id] = Module(id, target_share, status, active_keys, depositable_keys)

    total_active_keys = sum([module.active_keys for module in modules.values()])

    # simulate target share distribution
    # https://github.com/lidofinance/lido-dao/blob/331ecec7fe3c8d57841fd73ccca7fb1cc9bc174e/contracts/0.8.9/StakingRouter.sol#L1266-L1268

    target_total_active_keys = total_active_keys + keys_to_allocate
    total_basis_points = staking_router.TOTAL_BASIS_POINTS()

    for module in modules.values():
        target_active_keys = module.target_share * target_total_active_keys // total_basis_points
        module.allocation_limit = min(target_active_keys, module.active_keys + module.depositable_keys)

    # simulate min first strategy
    # https://github.com/lidofinance/lido-dao/blob/331ecec7fe3c8d57841fd73ccca7fb1cc9bc174e/contracts/0.8.9/StakingRouter.sol#L1274

    for _ in range(keys_to_allocate):
        # find the module with the lowest active_keys
        min_active_keys = modules[1].active_keys
        min_active_keys_module = modules[1]

        for module in modules.values():
            if module.active_keys < min_active_keys and module.active_keys < module.allocation_limit:
                min_active_keys = module.active_keys
                min_active_keys_module = module

        # allocate one key to the module if possible
        if min_active_keys_module.active_keys < min_active_keys_module.allocation_limit:
            min_active_keys_module.active_keys += 1
            min_active_keys_module.allocated_keys += 1

    total_allocated_keys = sum([module.allocated_keys for module in modules.values()])

    # check that local allocation matches the contract allocation
    assert allocation_from_contract == (total_allocated_keys, [module.active_keys for module in modules.values()])

    # fill the deposit buffer
    fill_deposit_buffer(total_allocated_keys)

    # perform deposits to the modules
    for module in modules.values():
        if module.allocated_keys > 0:
            lido.deposit(module.allocated_keys, module.id, "0x", {"from": deposit_security_module})

    # check that the new active keys in the modules match the expected values
    module_digests_after_deposit = staking_router.getAllStakingModuleDigests()
    expected_modules_state = modules

    for digest in module_digests_after_deposit:
        (_, _, state, summary) = digest
        (id, _, _, _, _, _, _, _, _, _) = state
        (exited_keys, deposited_keys, _) = summary

        active_keys_after_deposit = deposited_keys - exited_keys
        assert expected_modules_state[id].active_keys == active_keys_after_deposit
