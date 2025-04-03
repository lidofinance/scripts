from typing import Dict

from brownie import web3
from web3 import Web3

from utils.config import contracts
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member, fill_csm_operators_with_keys
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys
from utils.test.staking_router_helpers import StakingModuleStatus

TOTAL_BASIS_POINTS = 10000


class Module:
    def __init__(
        self, id, stake_share_limit, module_fee, treasury_fee, deposited_keys, exited_keys, depositable_keys, status,
        priorityExitShareThreshold, maxDepositsPerBlock, minDepositBlockDistance
    ):
        self.id = id
        self.target_share = stake_share_limit
        self.status = status
        self.active_keys = 0
        self.depositable_keys = depositable_keys
        self.allocated_keys = 0
        self.allocation_limit = 0
        self.module_fee = module_fee
        self.treasury_fee = treasury_fee
        self.deposited_keys = deposited_keys
        self.exited_keys = exited_keys
        self.priorityExitShareThreshold = priorityExitShareThreshold
        self.maxDepositsPerBlock = maxDepositsPerBlock
        self.minDepositBlockDistance = minDepositBlockDistance

def get_modules_info(staking_router):
    # collect the modules information
    module_digests = staking_router.getAllStakingModuleDigests()
    modules = {}

    for digest in module_digests:
        (_, _, state, summary) = digest
        (id, _, module_fee, treasury_fee, stake_share_limit, status, _, _, _, _, priorityExitShareThreshold, maxDepositsPerBlock, minDepositBlockDistance) = state
        (exited_keys, deposited_keys, depositable_keys) = summary
        if status != StakingModuleStatus.Active.value:
            # reset depositable keys in case of module is inactivated
            # https://github.com/lidofinance/lido-dao/blob/331ecec7fe3c8d57841fd73ccca7fb1cc9bc174e/contracts/0.8.9/StakingRouter.sol#L1230-L1232
            depositable_keys = 0

        modules[id] = Module(
            id, stake_share_limit, module_fee, treasury_fee, deposited_keys, exited_keys, depositable_keys, status,
            priorityExitShareThreshold, maxDepositsPerBlock, minDepositBlockDistance
        )

    # total_active_keys = sum([module.active_keys for module in modules.values()])
    return modules


def prep_modules_info(modules: Dict[int, Module]):
    # reset keys counters
    total_active_keys = 0

    for module in modules.values():
        module.active_keys = module.deposited_keys - module.exited_keys
        assert module.active_keys >= 0
        total_active_keys += module.active_keys

    return total_active_keys


def calc_allocation(modules: Dict[int, Module], keys_to_allocate: int, ignore_depositable: bool = False):

    total_active_keys = prep_modules_info(modules)
    # simulate target share distribution
    # https://github.com/lidofinance/lido-dao/blob/331ecec7fe3c8d57841fd73ccca7fb1cc9bc174e/contracts/0.8.9/StakingRouter.sol#L1266-L1268

    target_total_active_keys = total_active_keys + keys_to_allocate

    for module in modules.values():
        target_active_keys = module.target_share * target_total_active_keys // TOTAL_BASIS_POINTS
        module.allocation_limit = (
            target_active_keys
            if ignore_depositable
            else min(target_active_keys, module.active_keys + module.depositable_keys)
        )
        module.allocated_keys = 0

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
    return total_allocated_keys, target_total_active_keys


def assure_depositable_keys(stranger):
    modules = get_modules_info(contracts.staking_router)
    if not modules[1].depositable_keys:
        pass
    if not modules[2].depositable_keys:
        fill_simple_dvt_ops_vetted_keys(stranger, 3, 5)
    if not modules[3].depositable_keys:
        address, proof = get_ea_member()
        csm_add_node_operator(contracts.csm, contracts.cs_accounting, address, proof, curve_id=contracts.cs_early_adoption.CURVE_ID())

def test_stake_distribution(stranger):
    """
    Test stake distribution among the staking modules
    1. checks that result of `getDepositsAllocation` matches the local allocation calculations
    2. checks that deposits to modules can be made according to the calculated allocation
    """
    assure_depositable_keys(stranger)

    keys_to_allocate = 100  # keys to allocate to the modules
    allocation_from_contract = contracts.staking_router.getDepositsAllocation(keys_to_allocate)

    # collect the modules information
    modules = get_modules_info(contracts.staking_router)
    total_allocated_keys, _ = calc_allocation(modules, keys_to_allocate)

    # check that local allocation matches the contract allocation
    assert allocation_from_contract == (total_allocated_keys, [module.active_keys for module in modules.values()])

    # fill the deposit buffer
    fill_deposit_buffer(total_allocated_keys)

    # perform deposits to the modules
    for module in modules.values():
        if module.allocated_keys > 0:
            contracts.lido.deposit(module.allocated_keys, module.id, "0x", {"from": contracts.deposit_security_module})

    # check that the new active keys in the modules match the expected values
    module_digests_after_deposit = contracts.staking_router.getAllStakingModuleDigests()
    expected_modules_state = modules

    for digest in module_digests_after_deposit:
        (_, _, state, summary) = digest
        (id, _, _, _, _, _, _, _, _, _, _, _, _) = state
        (exited_keys, deposited_keys, _) = summary

        active_keys_after_deposit = deposited_keys - exited_keys
        assert expected_modules_state[id].active_keys == active_keys_after_deposit


def test_target_share_distribution(stranger):
    keys_to_allocate = 100  # keys to allocate to the modules
    keys_to_allocate_double = keys_to_allocate * 2

    modules = get_modules_info(contracts.staking_router)
    min_target_share = 1  # 0.01% = 1 / 10000
    nor_m_id = 1
    nor_m = modules[nor_m_id]

    cur_total_active_keys = prep_modules_info(modules)

    module = sorted(modules.values(), key=lambda m: m.active_keys / cur_total_active_keys * TOTAL_BASIS_POINTS)[0]

    # calc some hypothetical module allocation share for testing
    expected_active_keys_1 = module.active_keys + keys_to_allocate
    expected_active_keys_2 = module.active_keys + keys_to_allocate_double

    expected_total_active_keys = cur_total_active_keys + keys_to_allocate
    expected_total_active_keys_2 = cur_total_active_keys + keys_to_allocate_double

    # calc module share that is guaranteed to fit `keys_to_allocate` deposited keys amount (upper cap)
    expected_target_share_1 = (expected_active_keys_1 * TOTAL_BASIS_POINTS // expected_total_active_keys) + 1
    # calc module share for doubled `keys_to_allocate` keys amount, expected to overcome the 1st target share
    expected_target_share_2 = expected_active_keys_2 * TOTAL_BASIS_POINTS // expected_total_active_keys_2

    # ensure 2nd keys amount is enough to overcome the 1st target share (after 1st keys amount) at least by 1 basis point
    assert expected_target_share_1 >= min_target_share
    assert expected_target_share_2 > expected_target_share_1

    # force update module `targetShare` value to simulate new allocation
    module.target_share = expected_target_share_1

    expected_total_allocated_keys, expected_total_active_keys = calc_allocation(modules, keys_to_allocate, True)
    assert expected_total_allocated_keys == keys_to_allocate
    assert module.active_keys >= expected_active_keys_1
    assert module.allocated_keys == keys_to_allocate
    assert nor_m.allocated_keys == 0

    expected_total_allocated_keys, expected_total_active_keys = calc_allocation(modules, keys_to_allocate_double, True)
    assert expected_total_allocated_keys == keys_to_allocate_double
    assert module.active_keys < expected_active_keys_2
    assert module.allocated_keys < keys_to_allocate_double
    assert nor_m.allocated_keys <= keys_to_allocate_double

    # set the new target share value, which will be reached after 1s deposit of `keys_to_allocate`` batch
    contracts.staking_router.updateStakingModule(
        module.id,
        expected_target_share_1,
        module.priorityExitShareThreshold,
        module.module_fee,
        module.treasury_fee,
        module.maxDepositsPerBlock,
        module.minDepositBlockDistance,
        {"from": contracts.agent},
    )
    # add enough depositable keys to the target module to overcome the target share
    # at least first 3 NOs, each with 1/3 of the `keys_to_allocate_double` available keys
    if module.id == 2:
        fill_simple_dvt_ops_vetted_keys(stranger, 3, (module.deposited_keys + keys_to_allocate_double + 3) // 3)
    elif module.id == 3:
        fill_csm_operators_with_keys(3, (module.deposited_keys + keys_to_allocate_double + 3) // 3)

    # update the modules info and recalc the allocation according to the module limits
    modules = get_modules_info(contracts.staking_router)
    expected_total_allocated_keys, expected_total_active_keys = calc_allocation(modules, keys_to_allocate_double, False)

    assert expected_total_allocated_keys == keys_to_allocate_double
    assert module.active_keys < expected_active_keys_2
    assert module.allocated_keys < keys_to_allocate_double
    assert nor_m.allocated_keys <= keys_to_allocate_double

    allocation_from_contract = contracts.staking_router.getDepositsAllocation(keys_to_allocate_double)
    # check that local allocation matches the contract allocation
    assert allocation_from_contract == (
        expected_total_allocated_keys,
        [module.active_keys for module in modules.values()],
    )

    # fill the deposit buffer
    fill_deposit_buffer(keys_to_allocate_double)

    web3.manager.request_blocking(
        "hardhat_setBalance",  # type: ignore
        [
            contracts.deposit_security_module.address,
            Web3.to_hex(90_000_000_000),
        ],
    )

    # perform deposits to the modules
    for module in modules.values():
        if module.allocated_keys > 0:
            contracts.lido.deposit(
                module.allocated_keys, module.id, "0x", {"from": contracts.deposit_security_module, "gas_price": 4}
            )

    # check that the new active keys in the modules match the expected values
    module_digests_after_deposit = contracts.staking_router.getAllStakingModuleDigests()
    expected_modules_state = modules

    for digest in module_digests_after_deposit:
        (_, _, state, summary) = digest
        (id, _, _, _, _, _, _, _, _, _, _, _, _) = state
        (exited_keys, deposited_keys, _) = summary

        active_keys_after_deposit = deposited_keys - exited_keys
        assert expected_modules_state[id].active_keys == active_keys_after_deposit
