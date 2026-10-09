"""Mainnet rollout: https://research.lido.fi/t/0x02-csm-landscape/11697/10.

The regression fixture executes the real vote and DG proposal. Easy Track, Router,
module queues, stake accounting and ETH deposits run on the fork. CL activation
is synthetic in MockTopUpGateway; withdrawals/exits enter through their authorized
reporting boundaries. Fresh user inflow funds the post-exit checks independently
of CL withdrawal settlement. No Router/module/buffer storage is patched.
"""

from brownie import MockTopUpGateway, chain, interface, reverts, web3
from web3.logs import DISCARD

from utils.balance import set_balance
from utils.config import (
    CSM0X02_ADDRESS,
    CSM0X02_ACCOUNTING_ADDRESS,
    CSM0X02_PERMISSIONLESS_GATE_ADDRESS,
    EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
    contracts,
)
from utils.test.csm_helpers import csm_add_node_operator
from utils.test.curated_v2_helpers import ensure_curated_v2_depositable_keys
from utils.test.deposits_helpers import cover_wq_demand_and_submit
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion
from utils.test.helpers import ETH

CSM_ID = 5
CM_ID = 4
SEED = ETH(32)
ACTIVATION_DELAY = 24 * 86400
QUEUE_LIMIT = 32
UPLOADED_KEYS = 96


def _allocation(module_id, amount=None, top_up=True):
    router = contracts.staking_router
    amount = contracts.lido.getDepositableEther() if amount is None else amount
    index = list(router.getStakingModuleIds()).index(module_id)
    return router.getDepositAllocations(amount, top_up)[1][index]


def _pubkey(module, operator_id, key_index):
    return module.getSigningKeys(operator_id, key_index, 1)


def _seed_csm(csm, gateway, operator_id, sender):
    before = csm.getNodeOperator(operator_id)["totalDepositedKeys"]
    buffered = contracts.lido.getBufferedEther()
    stake = csm.getTotalModuleStake()
    chain.mine(contracts.staking_router.getStakingModuleMinDepositBlockDistance(CSM_ID))
    contracts.staking_router.deposit(CSM_ID, "0x", {"from": contracts.deposit_security_module})
    after = csm.getNodeOperator(operator_id)["totalDepositedKeys"]
    assert after > before
    assert buffered - contracts.lido.getBufferedEther() == (after - before) * SEED
    assert csm.getTotalModuleStake() - stake == (after - before) * SEED
    for key in range(before, after):
        gateway.setActivationTime(_pubkey(csm, operator_id, key), chain.time() + ACTIVATION_DELAY, {"from": sender})
    return after - before


def _top_up(gateway, module_id, module, operator_id, key_index, sender):
    buffered = contracts.lido.getBufferedEther()
    stake = module.getTotalModuleStake()
    deposit_balance = web3.eth.get_balance(contracts.staking_router.DEPOSIT_CONTRACT())
    chain.mine(contracts.top_up_gateway.getMinBlockDistance())
    tx = gateway.topUp(
        module_id, module, operator_id, key_index, _pubkey(module, operator_id, key_index), {"from": sender}
    )
    spent = buffered - contracts.lido.getBufferedEther()
    assert module.getTotalModuleStake() - stake == spent
    assert web3.eth.get_balance(contracts.staking_router.DEPOSIT_CONTRACT()) - deposit_balance == spent
    # Decode with the current local ABI: Brownie's proxy ABI cache may predate SRv3.
    router = contracts.staking_router
    event = web3.eth.contract(abi=interface.StakingRouter.abi).events.StakingRouterETHTopUp()
    receipt = {"logs": [log for log in tx.logs if log["address"] == router.address]}
    top_ups = event.process_receipt(receipt, errors=DISCARD)
    assert len(top_ups) == 1
    assert dict(top_ups[0]["args"]) == {"stakingModuleId": module_id, "amount": spent}
    return spent


def _cm_key(gateway, sender):
    """Pick a deposited CM key whose operator can actually accept a top-up."""
    cm = contracts.cm
    _, operator_ids, _ = cm.getDepositsAllocation(SEED)
    for operator_id in operator_ids:
        no = cm.getNodeOperator(operator_id)
        count = no["totalDepositedKeys"]
        balances = cm.getKeyAllocatedBalances(operator_id, 0, count)
        for key in reversed(range(count)):
            if cm.isValidatorWithdrawn(operator_id, key):
                continue
            limit = gateway.TARGET_BALANCE() - SEED - balances[key]
            if limit < ETH(2):
                continue
            pubkey = _pubkey(cm, operator_id, key)
            gateway.setActivationTime(pubkey, chain.time(), {"from": sender})
            return operator_id, key
    raise AssertionError("Fork needs an eligible active CMv2 key for the competing top-up")


def _drain_other_modules(gateway, sender):
    spent = 0
    router = contracts.staking_router
    for _ in range(100):
        if contracts.lido.getDepositableEther() < SEED:
            return spent
        assert _allocation(CSM_ID) == 0, "CSM still reserves top-up allocation"
        if _allocation(CM_ID) > 0:
            operator_id, key = _cm_key(gateway, sender)
            amount = _top_up(gateway, CM_ID, contracts.cm, operator_id, key, sender)
        else:
            amount = 0
            for module_id in router.getStakingModuleIds():
                if module_id == CSM_ID or _allocation(module_id, top_up=False) == 0:
                    continue
                buffered = contracts.lido.getBufferedEther()
                deposited = router.getStakingModuleSummary(module_id)[1]
                chain.mine(router.getStakingModuleMinDepositBlockDistance(module_id))
                router.deposit(module_id, "0x", {"from": contracts.deposit_security_module})
                amount = buffered - contracts.lido.getBufferedEther()
                assert amount == (router.getStakingModuleSummary(module_id)[1] - deposited) * SEED
                if amount:
                    break
        assert amount > 0, "No other module consumed its allocation"
        spent += amount
    raise AssertionError("Other modules did not drain the depositable buffer")


def _set_share(share, sender):
    factory = interface.UpdateStakingModuleShareLimits(EASYTRACK_CSM0X02_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY)
    state = contracts.staking_router.getStakingModule(CSM_ID)
    current = state["stakeShareLimit"]
    while current != share:
        # The production factory permits at most +50 bp in one motion.
        next_share = min(share, current + 50)
        threshold = state["priorityExitShareThreshold"]
        create_and_enact_motion(
            contracts.easy_track,
            set_balance(factory.trustedCaller(), 100),
            factory,
            _encode_calldata(["uint16"] * 4, [current, next_share, threshold, threshold]),
            sender,
        )
        current = contracts.staking_router.getStakingModule(CSM_ID)["stakeShareLimit"]
        assert current == next_share


def _fill_to(amount):
    current = contracts.lido.getDepositableEther()
    assert current <= amount
    if current < amount:
        cover_wq_demand_and_submit(amount - current)
    assert amount <= contracts.lido.getDepositableEther() <= amount + 5


def _first_cm_top_up_buffer():
    """Find the first 32-ETH buffer quantum for which CMv2 gets an allocation."""
    low, high = 0, 1
    while _allocation(CM_ID, high * SEED) == 0:
        high *= 2
        assert high < 100_000
    while high - low > 1:
        middle = (low + high) // 2
        if _allocation(CM_ID, middle * SEED):
            high = middle
        else:
            low = middle
    return high * SEED


def test_csm0x02_deployment_scenario(accounts):
    csm = interface.CSModule(CSM0X02_ADDRESS)
    router = contracts.staking_router
    sender = accounts[0]

    # 1. Real activation vote + DG are executed by regression/conftest.py.
    assert router.getStakingModule(CSM_ID)["stakeShareLimit"] == 1
    assert csm.getTopUpQueue() == (True, QUEUE_LIMIT, 0, 0)
    assert not csm.isPaused()
    assert csm.getNodeOperatorsCount() == 0, "Use a pre-rollout mainnet fork"

    real_gateway = contracts.top_up_gateway
    min_block_distance = real_gateway.getMinBlockDistance()
    implementation = MockTopUpGateway.deploy(
        router, sender, real_gateway.getTargetBalanceGwei() * 10**9, {"from": sender}
    )
    proxy = interface.OssifiableProxy(real_gateway)
    proxy.proxy__upgradeTo(implementation, {"from": proxy.proxy__getAdmin()})
    gateway = MockTopUpGateway.at(real_gateway.address)
    # Keep the real gateway cooldown available after replacing its implementation.
    # The mock itself only replaces CL witness verification.
    gateway.setMinBlockDistance(min_block_distance, {"from": sender})

    operator_id = csm_add_node_operator(
        csm,
        interface.PermissionlessGate(CSM0X02_PERMISSIONLESS_GATE_ADDRESS),
        interface.ModuleAccounting(CSM0X02_ACCOUNTING_ADDRESS),
        accounts[1],
        keys_count=UPLOADED_KEYS,
    )
    cover_wq_demand_and_submit(ETH(3200))

    # 2. Seed until the 1-bp share is exhausted; "~32" is not an exact key count.
    assert _allocation(CSM_ID, top_up=False) > 0
    for _ in range(QUEUE_LIMIT):
        if _allocation(CSM_ID, top_up=False) == 0:
            break
        _seed_csm(csm, gateway, operator_id, sender)
    initial_count = csm.getNodeOperator(operator_id)["totalDepositedKeys"]
    assert 0 < initial_count <= QUEUE_LIMIT
    assert csm.getTotalModuleStake() == initial_count * SEED
    assert csm.getTopUpQueue()["length"] == initial_count
    assert csm.getNodeOperator(operator_id)["depositableValidatorsCount"] > 0
    assert _allocation(CSM_ID, top_up=False) == _allocation(CSM_ID) == 0
    with reverts("VALIDATOR_NOT_ACTIVATED"):
        gateway.topUp.call(CSM_ID, csm, operator_id, 0, _pubkey(csm, operator_id, 0), {"from": sender})

    # 3. Other modules can consume the buffer while the initial CSM keys wait.
    assert _drain_other_modules(gateway, sender) > 0
    assert contracts.lido.getDepositableEther() < SEED
    print(f"SCENARIO initial: {initial_count} seeds; other modules drain the buffer")

    # 4. Activate the first batch; increase share via real ET, within its executable
    # capacity plus the seeds which fill each newly freed FIFO position.
    chain.sleep(ACTIVATION_DELAY)
    chain.mine()
    cover_wq_demand_and_submit(ETH(80_000))
    total = sum(router.getDepositAllocations(contracts.lido.getDepositableEther(), True)[2])
    full_balance = SEED + (gateway.TARGET_BALANCE() - SEED) // ETH(2) * ETH(2)
    safe_capacity = initial_count * full_balance + QUEUE_LIMIT * SEED
    share = safe_capacity * 10_000 // total
    assert share > 1
    _set_share(share, sender)

    # 5. Follow the picture: seed priority; a full top-up dequeues the old key,
    # then another seed fills the free position. Stop at the new share.
    total_top_ups = 0
    for _ in range(4 * QUEUE_LIMIT):
        if _allocation(CSM_ID, top_up=False):
            _seed_csm(csm, gateway, operator_id, sender)
        elif _allocation(CSM_ID):
            no, key = csm.getTopUpQueueItem(0)
            assert key < initial_count, "The rollout increase already requires inactive keys"
            total_top_ups += _top_up(gateway, CSM_ID, csm, no, key, sender)
        else:
            break
    assert _allocation(CSM_ID) == 0
    assert total_top_ups > 0
    deposited = csm.getNodeOperator(operator_id)["totalDepositedKeys"]
    assert deposited > initial_count
    assert csm.getTopUpQueue()["length"] == QUEUE_LIMIT
    assert _drain_other_modules(gateway, sender) > 0
    print(f"SCENARIO rollout: share={share} bp, seeds={deposited}, top-ups={total_top_ups / ETH(1):g} ETH")

    # 6. Exit two fully topped keys and the remaining active FIFO prefix. The
    # reports free stake; zero-limit processing removes withdrawn queue entries.
    remaining_active = [
        csm.getTopUpQueueItem(i)[1] for i in range(QUEUE_LIMIT) if csm.getTopUpQueueItem(i)[1] < initial_count
    ]
    exiting = [0, 1, *remaining_active]
    assert len(set(exiting)) == len(exiting) and len(exiting) < initial_count // 2
    balances = [SEED + csm.getKeyAllocatedBalances(operator_id, key, 1)[0] for key in exiting]
    stake_before = csm.getTotalModuleStake()
    reporter_role = csm.REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE()
    csm.reportRegularWithdrawnValidators(
        [(operator_id, key, balance, 0, False) for key, balance in zip(exiting, balances)],
        {"from": csm.getRoleMember(reporter_role, 0)},
    )
    assert stake_before - csm.getTotalModuleStake() == sum(balances)
    assert all(csm.isValidatorWithdrawn(operator_id, key) for key in exiting)
    router.updateExitedValidatorsCountByStakingModule([CSM_ID], [len(exiting)], {"from": contracts.accounting_oracle})
    router.reportStakingModuleExitedValidatorsCountByNodeOperator(
        CSM_ID, operator_id.to_bytes(8, "big"), len(exiting).to_bytes(16, "big"), {"from": contracts.accounting_oracle}
    )
    while csm.getTopUpQueueItem(0)[1] in exiting:
        no, key = csm.getTopUpQueueItem(0)
        assert _top_up(gateway, CSM_ID, csm, no, key, sender) == 0
    cover_wq_demand_and_submit(ETH(1024))
    while _allocation(CSM_ID, top_up=False):
        _seed_csm(csm, gateway, operator_id, sender)
    assert csm.getNodeOperator(operator_id)["totalDepositedKeys"] > deposited
    assert csm.getTopUpQueue()["length"] == QUEUE_LIMIT

    # 7. Real Router reserves the available top-up budget; CL-inactive head cannot use it.
    no, head_key = csm.getTopUpQueueItem(0)
    head_pubkey = _pubkey(csm, no, head_key)
    assert head_key >= initial_count
    assert gateway.activationTime(web3.keccak(head_pubkey)) > chain.time()
    blocked_buffer = contracts.lido.getDepositableEther()
    assert blocked_buffer >= SEED
    assert _allocation(CSM_ID) == blocked_buffer // SEED * SEED
    assert _allocation(CM_ID) == 0
    with reverts("VALIDATOR_NOT_ACTIVATED"):
        gateway.topUp.call(CSM_ID, csm, no, head_key, head_pubkey, {"from": sender})
    cm_no, cm_key = _cm_key(gateway, sender)
    assert _top_up(gateway, CM_ID, contracts.cm, cm_no, cm_key, sender) == 0
    assert contracts.lido.getDepositableEther() == blocked_buffer

    # Seed allocation is separate: prove an actual CM seed can bypass this top-up
    # bottleneck, then restore the identical state for threshold/recovery checks.
    chain.snapshot()
    # The live CM queue may have no unused keys; supply one for this control only.
    ensure_curated_v2_depositable_keys(1, accounts[2])
    assert _allocation(CM_ID) == 0
    assert _allocation(CM_ID, top_up=False) >= SEED
    buffered = contracts.lido.getBufferedEther()
    cm_deposited = router.getStakingModuleSummary(CM_ID)[1]
    chain.mine(router.getStakingModuleMinDepositBlockDistance(CM_ID))
    router.deposit(CM_ID, "0x", {"from": contracts.deposit_security_module})
    seeded = router.getStakingModuleSummary(CM_ID)[1] - cm_deposited
    assert seeded > 0
    assert buffered - contracts.lido.getBufferedEther() == seeded * SEED
    chain.revert()

    # 8. Find and exercise both sides of the buffer threshold. Extra inflow changes
    # the share denominator, so the threshold comes from actual Router views.
    threshold = _first_cm_top_up_buffer()
    assert blocked_buffer < threshold
    _fill_to(threshold - SEED)
    assert _allocation(CM_ID) == 0
    assert _top_up(gateway, CM_ID, contracts.cm, cm_no, cm_key, sender) == 0
    _fill_to(threshold)
    assert _allocation(CM_ID) == SEED
    # Router's 32-ETH module budget is an upper bound: CM operator allocation and
    # the selected key's remaining capacity can limit the actual 2-ETH-step top-up.
    topped_up = _top_up(gateway, CM_ID, contracts.cm, cm_no, cm_key, sender)
    assert 0 < topped_up <= SEED
    assert topped_up % ETH(2) == 0
    assert _allocation(CM_ID) == 0
    assert contracts.lido.getDepositableEther() >= blocked_buffer
    print(
        f"SCENARIO blocked: {blocked_buffer / ETH(1):g} ETH; "
        f"CM top-up starts at {threshold / ETH(1):g} ETH, transfers {topped_up / ETH(1):g} ETH"
    )

    # 9a. Control: activation alone makes the same reserved budget executable.
    chain.snapshot()
    chain.sleep(ACTIVATION_DELAY)
    chain.mine()
    assert _top_up(gateway, CSM_ID, csm, no, head_key, sender) > 0
    chain.revert()

    # 9b. Operational recovery before activation: lower share through real ET.
    total = sum(router.getDepositAllocations(contracts.lido.getDepositableEther(), True)[2])
    recovered_share = csm.getTotalModuleStake() * 10_000 // total
    _set_share(recovered_share, sender)
    assert gateway.activationTime(web3.keccak(head_pubkey)) > chain.time()
    assert _allocation(CSM_ID) == 0
    assert _allocation(CM_ID) > 0
    assert _drain_other_modules(gateway, sender) > 0
    assert contracts.lido.getDepositableEther() < SEED
    print(f"SCENARIO recovered: share {share} -> {recovered_share} bp; depositable remainder <32 ETH")
