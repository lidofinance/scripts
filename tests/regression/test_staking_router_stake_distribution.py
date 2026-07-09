from typing import Dict

from brownie import chain, interface

from utils.config import contracts
from utils.test.csm_helpers import csm_add_node_operator, fill_csm_operators_with_keys
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys
from utils.test.staking_router_helpers import StakingModuleStatus

TOTAL_BASIS_POINTS = 10000
WC_TYPE_02 = 2


class Module:
    def __init__(
        self,
        id,
        address,
        stake_share_limit,
        module_fee,
        treasury_fee,
        deposited_keys,
        exited_keys,
        depositable_keys,
        status,
        priorityExitShareThreshold,
        maxDepositsPerBlock,
        minDepositBlockDistance,
        withdrawal_credentials_type,
        total_module_stake,
    ):
        self.id = id
        self.address = address
        self.target_share = stake_share_limit
        self.status = status
        self.active_keys = 0
        self.depositable_keys = depositable_keys
        self.current_allocation = 0
        self.allocated_keys = 0
        self.allocation_limit = 0
        self.module_fee = module_fee
        self.treasury_fee = treasury_fee
        self.deposited_keys = deposited_keys
        self.exited_keys = exited_keys
        self.priorityExitShareThreshold = priorityExitShareThreshold
        self.maxDepositsPerBlock = maxDepositsPerBlock
        self.minDepositBlockDistance = minDepositBlockDistance
        self.withdrawal_credentials_type = withdrawal_credentials_type
        self.total_module_stake = total_module_stake


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def get_modules_info(staking_router):
    # collect the modules information
    module_digests = staking_router.getAllStakingModuleDigests()
    modules = {}

    for digest in module_digests:
        (_, _, state, summary) = digest
        (
            id,
            address,
            module_fee,
            treasury_fee,
            stake_share_limit,
            status,
            _,
            _,
            _,
            exited_keys_stored,
            priorityExitShareThreshold,
            maxDepositsPerBlock,
            minDepositBlockDistance,
            withdrawalCredentialsType,
            _,
        ) = state
        (exited_keys, deposited_keys, depositable_keys) = summary

        total_module_stake = 0
        if withdrawalCredentialsType == WC_TYPE_02:
            total_module_stake = interface.IStakingModuleV2(address).getTotalModuleStake()

        modules[id] = Module(
            id,
            address,
            stake_share_limit,
            module_fee,
            treasury_fee,
            deposited_keys,
            max(exited_keys, exited_keys_stored),
            depositable_keys,
            status,
            priorityExitShareThreshold,
            maxDepositsPerBlock,
            minDepositBlockDistance,
            withdrawalCredentialsType,
            total_module_stake,
        )

    return modules


def prep_modules_info(modules: Dict[int, Module], deposit_size: int):
    # reset the allocation counters; a module's current allocation is measured in
    # 32-ETH validator equivalents: active validators for WC 0x01 modules,
    # ceil(total module stake / 32 ETH) for WC 0x02 modules
    total_allocation = 0

    for module in modules.values():
        module.active_keys = module.deposited_keys - module.exited_keys
        assert module.active_keys >= 0
        if module.withdrawal_credentials_type == WC_TYPE_02:
            module.current_allocation = ceil_div(module.total_module_stake, deposit_size)
        else:
            module.current_allocation = module.active_keys
        module.allocated_keys = 0
        total_allocation += module.current_allocation

    return total_allocation


def calc_allocation(modules: Dict[int, Module], deposit_amount: int, is_top_up: bool = False):
    # simulate SRLib._getDepositAllocations: everything is computed in 32-ETH
    # validator-equivalent units, the results are returned in wei
    deposit_size = contracts.staking_router.INITIAL_DEPOSIT_SIZE()
    max_effective_balance = contracts.staking_router.MAX_EFFECTIVE_BALANCE_WC_TYPE_02()
    units_to_allocate = deposit_amount // deposit_size

    total_validators = units_to_allocate + prep_modules_info(modules, deposit_size)

    for module in modules.values():
        if module.status != StakingModuleStatus.Active.value:
            module.allocation_limit = module.current_allocation
            continue
        if is_top_up and module.withdrawal_credentials_type == WC_TYPE_02:
            capacity = module.active_keys * max_effective_balance // deposit_size
        else:
            capacity = module.current_allocation + module.depositable_keys
        target_validators = module.target_share * total_validators // TOTAL_BASIS_POINTS
        module.allocation_limit = min(target_validators, capacity)

    # simulate min first strategy: every unit goes to the least filled module
    # that still has free capacity, first index wins the tie
    for _ in range(units_to_allocate):
        best_module = None
        for module in modules.values():
            filled = module.current_allocation + module.allocated_keys
            if filled >= module.allocation_limit:
                continue
            if best_module is None or filled < best_module.current_allocation + best_module.allocated_keys:
                best_module = module
        if best_module is None:
            break
        best_module.allocated_keys += 1

    allocated = [module.allocated_keys * deposit_size for module in modules.values()]
    new_allocations = [
        (module.current_allocation + module.allocated_keys) * deposit_size for module in modules.values()
    ]
    return sum(allocated), allocated, new_allocations


def assure_depositable_keys(stranger):
    modules = get_modules_info(contracts.staking_router)
    if not modules[1].depositable_keys:
        pass
    if not modules[2].depositable_keys:
        fill_simple_dvt_ops_vetted_keys(stranger, 3, 5)
    if not modules[3].depositable_keys:
        csm_add_node_operator(contracts.csm, contracts.cs_permissionless_gate, contracts.cs_accounting, stranger)


def test_stake_distribution(stranger):
    """
    Test stake distribution among the staking modules
    1. checks that result of `getDepositAllocations` matches the local allocation calculations
    2. checks that deposits to modules can be made according to the calculated allocation
    """
    assure_depositable_keys(stranger)

    deposits_count = 100  # seed deposits to add to the buffer
    fill_deposit_buffer(deposits_count)

    deposit_amount = contracts.lido.getDepositableEther()
    allocation_from_contract = contracts.staking_router.getDepositAllocations(deposit_amount, False)

    # collect the modules information
    modules = get_modules_info(contracts.staking_router)
    total_allocated, allocated, new_allocations = calc_allocation(modules, deposit_amount)

    # check that local allocation matches the contract allocation
    assert allocation_from_contract == (total_allocated, allocated, new_allocations)

    # perform deposits to the modules; the router computes the deposits count itself:
    # min(maxDepositsPerBlock, module allocation / 32 ETH)
    for module in modules.values():
        expected_deposits = min(module.maxDepositsPerBlock, module.allocated_keys)
        if expected_deposits == 0:
            continue

        (_, deposited_before, _) = contracts.staking_router.getStakingModuleSummary(module.id)
        chain.mine(module.minDepositBlockDistance)
        contracts.staking_router.deposit(module.id, "0x", {"from": contracts.deposit_security_module})
        (_, deposited_after, _) = contracts.staking_router.getStakingModuleSummary(module.id)

        assert deposited_after - deposited_before == expected_deposits

    # check that the new active keys in the modules match the expected values
    module_digests_after_deposit = contracts.staking_router.getAllStakingModuleDigests()
    expected_modules_state = modules

    for digest in module_digests_after_deposit:
        (_, _, state, summary) = digest
        (id, _, _, _, _, _, _, _, _, _, _, _, _, _, _) = state
        (exited_keys, deposited_keys, _) = summary

        active_keys_after_deposit = deposited_keys - exited_keys
        expected = expected_modules_state[id]
        assert active_keys_after_deposit == expected.active_keys + min(
            expected.maxDepositsPerBlock, expected.allocated_keys
        )


def test_target_share_distribution(stranger):
    """
    Test that `stakeShareLimit` caps the deposit allocation of a module
    1. sets a module a share limit that admits exactly `keys_to_allocate` more seed deposits
    2. checks that the share limit is the binding constraint (the module has spare keys above it)
    3. checks that on an oversized allocation the module fills up to the share limit and stops,
       the rest spills over to the other modules
    4. checks the contract allocation matches the local model and a real deposit follows it
    """
    deposit_size = contracts.staking_router.INITIAL_DEPOSIT_SIZE()

    modules = get_modules_info(contracts.staking_router)
    total_allocation = prep_modules_info(modules, deposit_size)

    # target module: the least filled active module which can be topped up with keys
    # (no key onboarding helper for Curated Module v2 yet, so ids 2-3 only)
    candidates = [m for m in modules.values() if m.status == StakingModuleStatus.Active.value and m.id in (2, 3)]
    module = min(candidates, key=lambda m: m.current_allocation)
    module_idx = list(modules.keys()).index(module.id)

    # scenario size: must exceed the 1 bp share granularity (1 bp of the total)
    keys_to_allocate = max(100, 2 * (total_allocation // TOTAL_BASIS_POINTS))
    required_depositable_keys = 2 * keys_to_allocate

    # a share limit that admits exactly +keys_to_allocate to the target module
    target_share = (module.current_allocation + keys_to_allocate) * TOTAL_BASIS_POINTS // (
        total_allocation + keys_to_allocate
    ) + 1
    assert target_share <= module.priorityExitShareThreshold

    # the doubled amount must not fit into the target share (share granularity check)
    doubled_share = (
        (module.current_allocation + required_depositable_keys)
        * TOTAL_BASIS_POINTS
        // (total_allocation + required_depositable_keys)
    )
    assert doubled_share > target_share

    # the module must have more depositable keys than the share admits,
    # so the share limit is the binding constraint, not the keys
    if module.depositable_keys < required_depositable_keys:
        min_keys_cnt = (required_depositable_keys + 2) // 3
        if module.id == 2:
            fill_simple_dvt_ops_vetted_keys(stranger, 3, min_keys_cnt)
        elif module.id == 3:
            fill_csm_operators_with_keys(3, min_keys_cnt)

    contracts.staking_router.updateStakingModule(
        module.id,
        target_share,
        module.priorityExitShareThreshold,
        module.module_fee,
        module.treasury_fee,
        module.maxDepositsPerBlock,
        module.minDepositBlockDistance,
        {"from": contracts.agent},
    )

    modules = get_modules_info(contracts.staking_router)
    module = modules[module.id]
    assert module.target_share == target_share
    assert module.depositable_keys >= required_depositable_keys

    # the share limit admits the base amount and the contract agrees with the model
    deposit_amount = keys_to_allocate * deposit_size
    allocations = calc_allocation(modules, deposit_amount)
    assert contracts.staking_router.getDepositAllocations(deposit_amount, False) == allocations
    assert module.allocation_limit >= module.current_allocation + keys_to_allocate
    assert module.current_allocation + module.depositable_keys > module.allocation_limit

    # find an allocation amount that overflows the target module: the module fills up
    # to its share limit and stops, no matter how close the other modules levels are
    overflow_amount = required_depositable_keys * deposit_size
    for _ in range(10):
        total_allocated, allocated, new_allocations = calc_allocation(modules, overflow_amount)
        if new_allocations[module_idx] == module.allocation_limit * deposit_size:
            break
        overflow_amount *= 2

    assert new_allocations[module_idx] == module.allocation_limit * deposit_size
    assert module.current_allocation + module.depositable_keys > module.allocation_limit
    assert allocated[module_idx] < overflow_amount
    assert contracts.staking_router.getDepositAllocations(overflow_amount, False) == (
        total_allocated,
        allocated,
        new_allocations,
    )

    # the new share limit applies to a real deposit as well
    fill_deposit_buffer(keys_to_allocate)
    (_, allocated, _) = calc_allocation(modules, contracts.lido.getDepositableEther())

    expected_deposits = min(module.maxDepositsPerBlock, allocated[module_idx] // deposit_size)
    if expected_deposits > 0:
        (_, deposited_before, _) = contracts.staking_router.getStakingModuleSummary(module.id)
        chain.mine(module.minDepositBlockDistance)
        contracts.staking_router.deposit(module.id, "0x", {"from": contracts.deposit_security_module})
        (_, deposited_after, _) = contracts.staking_router.getStakingModuleSummary(module.id)

        assert deposited_after - deposited_before == expected_deposits
