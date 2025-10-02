import pytest

from brownie import reverts, web3, ZERO_ADDRESS, accounts, chain

from utils.balance import set_balance_in_wei
from utils.config import (
    contracts,
    ContractsLazyLoader,
    CSM_COMMITTEE_MS,
    EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY,
    EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY,
)
from utils.dsm import UnvetArgs, to_bytes, set_single_guardian
from utils.staking_module import calc_module_reward_shares
from utils.test.csm_helpers import csm_add_node_operator, csm_upload_keys, get_ics_members, csm_add_ics_node_operator
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.easy_track_helpers import _encode_calldata
from utils.test.helpers import ETH
from utils.test.merkle_tree import StrikesTree
from utils.test.oracle_report_helpers import (
    oracle_report,
    wait_to_next_available_report_time,
    prepare_csm_report,
    reach_consensus,
)
from utils.test.staking_router_helpers import (
    set_staking_module_status,
    StakingModuleStatus,
    increase_staking_module_share,
)

contracts: ContractsLazyLoader = contracts

CSM_MODULE_ID = 3
MAX_DEPOSITS = 50


@pytest.fixture(scope="module")
def csm():
    return contracts.csm


@pytest.fixture(scope="module")
def permissionless_gate():
    return contracts.cs_permissionless_gate


@pytest.fixture(scope="module")
def vetted_gate():
    return contracts.cs_vetted_gate


@pytest.fixture(scope="module")
def accounting():
    return contracts.cs_accounting


@pytest.fixture(scope="module")
def parameters_registry():
    return contracts.cs_parameters_registry


@pytest.fixture(scope="module")
def fee_distributor():
    return contracts.cs_fee_distributor


@pytest.fixture(scope="module")
def fee_oracle():
    return contracts.cs_fee_oracle


@pytest.fixture(scope="module")
def ejector():
    return contracts.cs_ejector


@pytest.fixture(scope="module")
def strikes():
    return contracts.cs_strikes


@pytest.fixture
def depositable_node_operator(csm, accounting, permissionless_gate, stranger):
    increase_staking_module_share(module_id=CSM_MODULE_ID, share_multiplier=2)
    csm.cleanDepositQueue(2 * csm.getNonce(), {"from": stranger.address})
    for queue_priority in range(1, 6):
        deposit_batch = csm.depositQueueItem(queue_priority, csm.depositQueuePointers(queue_priority)["head"])
        if deposit_batch:
            node_operator_id = (deposit_batch >> 192) & ((1 << 64) - 1)
            keys_count = (deposit_batch >> 128) & ((1 << 64) - 1)
            break
    else:
        address = accounts[7].address
        keys_count = 5
        node_operator_id = csm_add_node_operator(csm, permissionless_gate, accounting, address, keys_count=keys_count)
    return node_operator_id, keys_count


@pytest.fixture
def node_operator(depositable_node_operator, csm, accounting) -> int:
    node_operator, keys_count = depositable_node_operator
    fill_deposit_buffer(keys_count)
    contracts.lido.deposit(keys_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})
    return node_operator


@pytest.fixture
def pause_modules():
    # pause deposit to all modules except csm
    # to be sure that all deposits goes to csm
    modules = contracts.staking_router.getStakingModules()
    for module in modules:
        if module[0] != CSM_MODULE_ID:
            set_staking_module_status(module[0], StakingModuleStatus.Stopped)


@pytest.fixture
def remove_stake_limit():
    contracts.acl.grantPermission(contracts.agent, contracts.lido, web3.keccak(text="STAKING_CONTROL_ROLE"), {"from": contracts.agent})
    contracts.lido.removeStakingLimit({"from": accounts.at(contracts.agent, force=True)})


@pytest.fixture
def ref_slot():
    wait_to_next_available_report_time(contracts.csm_hash_consensus)
    ref_slot, _ = contracts.csm_hash_consensus.getCurrentFrame()
    return ref_slot


def distribute_reward_tree(node_operator, ref_slot):
    consensus_version = contracts.cs_fee_oracle.getConsensusVersion()
    oracle_version = contracts.cs_fee_oracle.getContractVersion()
    distributed_before = contracts.lido.sharesOf(contracts.cs_fee_distributor)
    claimed_before = contracts.cs_fee_distributor.distributedShares(node_operator)

    rewards = ETH(0.05)
    oracle_report(cl_diff=rewards)
    distributed_shares = contracts.lido.sharesOf(contracts.cs_fee_distributor) - distributed_before
    assert distributed_shares > 0

    report, report_hash, tree = prepare_csm_report({node_operator: claimed_before + distributed_shares}, ref_slot, distributed_shares)

    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.csm_hash_consensus,
    )

    contracts.cs_fee_oracle.submitReportData(report, oracle_version, {"from": submitter})
    return distributed_shares, tree.tree


def get_sys_fee_to_eject():
    withdrawal_request_sys_address = '0x00000961Ef480Eb55e80D19ad83579A64c007002'
    val = web3.eth.call({
        "to": withdrawal_request_sys_address,
        "data": "0x",
    })
    return int.from_bytes(val, "big")


@pytest.mark.parametrize("address, proof", get_ics_members())
def test_add_node_operator_ics(csm, vetted_gate, accounting, address, proof):
    no_id = csm_add_ics_node_operator(csm, vetted_gate, accounting, address, proof)
    no = csm.getNodeOperator(no_id)

    assert no["managerAddress"] == address
    assert no["rewardAddress"] == address
    assert accounting.getBondCurveId(no_id) == vetted_gate.curveId()


def test_add_node_operator_permissionless(csm, permissionless_gate, accounting, accounts):
    address = accounts[8].address
    no_id = csm_add_node_operator(csm, permissionless_gate, accounting, address)
    no = csm.getNodeOperator(no_id)

    assert no["managerAddress"] == address
    assert no["rewardAddress"] == address
    assert accounting.getBondCurveId(no_id) == accounting.DEFAULT_BOND_CURVE_ID()


@pytest.mark.usefixtures("pause_modules")
def test_deposit(depositable_node_operator, csm, remove_stake_limit):
    (node_operator, keys_count) = depositable_node_operator
    fill_deposit_buffer(keys_count)
    total_deposited_before = csm.getNodeOperator(node_operator)["totalDepositedKeys"]
    contracts.lido.deposit(keys_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    no = csm.getNodeOperator(node_operator)
    assert no["totalDepositedKeys"] == total_deposited_before + keys_count


def test_mint_rewards_happy_path(csm, fee_distributor):
    csm_shares_before = contracts.lido.sharesOf(csm)
    fee_distributor_shares_before = contracts.lido.sharesOf(fee_distributor)
    (report_tx, _) = oracle_report()
    minted_shares = report_tx.events["TokenRebased"]["sharesMintedAsFees"]
    csm_distributed_rewards = calc_module_reward_shares(CSM_MODULE_ID, minted_shares)

    assert csm_shares_before == contracts.lido.sharesOf(csm)
    assert contracts.lido.sharesOf(fee_distributor) == fee_distributor_shares_before + csm_distributed_rewards


def test_csm_target_limits(csm, node_operator):
    target_limit_mode = 1
    target_limit = 2
    contracts.staking_router.updateTargetValidatorsLimits(
        CSM_MODULE_ID, node_operator, target_limit_mode, target_limit, {"from": contracts.agent}
    )

    no = csm.getNodeOperator(node_operator)
    assert no["targetLimitMode"] == target_limit_mode
    assert no["targetLimit"] == target_limit


def test_csm_report_exited(csm, node_operator, extra_data_service):
    total_exited = csm.getStakingModuleSummary()["totalExitedValidators"]
    exited_keys = 5
    extra_data = extra_data_service.collect({(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[total_exited + exited_keys],
    )

    no = csm.getNodeOperator(node_operator)
    assert no["totalExitedKeys"] == exited_keys


def test_csm_get_staking_module_summary(csm, accounting, node_operator, extra_data_service, remove_stake_limit):
    (exited_before, deposited_before, depositable_before) = contracts.staking_router.getStakingModuleSummary(
        CSM_MODULE_ID
    )

    # Assure there are new exited keys
    exited_keys = 5
    extra_data = extra_data_service.collect({(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[exited_before + exited_keys],
    )

    # Assure there are new deposited keys

    deposits_count = 3
    new_keys = 5
    new_depositable = new_keys - deposits_count
    csm_upload_keys(csm, accounting, node_operator, new_keys)
    increase_staking_module_share(module_id=CSM_MODULE_ID, share_multiplier=2)

    fill_deposit_buffer(deposits_count)
    contracts.lido.deposit(deposits_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    (exited_after, deposited_after, depositable_after) = contracts.staking_router.getStakingModuleSummary(CSM_MODULE_ID)

    assert exited_after == exited_before + exited_keys
    assert deposited_after == deposited_before + deposits_count
    assert depositable_after == depositable_before + new_depositable


def test_csm_get_node_operator_summary(csm, node_operator, extra_data_service):
    total_exited = csm.getStakingModuleSummary()["totalExitedValidators"]
    no = csm.getNodeOperator(node_operator)
    exited_keys = no["totalExitedKeys"] + 1
    extra_data = extra_data_service.collect(
        {(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys
    )
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[total_exited],
    )

    summary = contracts.staking_router.getNodeOperatorSummary(CSM_MODULE_ID, node_operator)
    assert summary["targetLimitMode"] == no["targetLimitMode"]
    assert summary["targetValidatorsCount"] == no["targetLimit"]
    # DEPRECATED #
    assert summary["stuckValidatorsCount"] == 0
    assert summary["refundedValidatorsCount"] == 0
    assert summary["stuckPenaltyEndTimestamp"] == 0
    ##############
    assert summary["totalExitedValidators"] == exited_keys
    assert summary["totalDepositedValidators"] == no["totalDepositedKeys"]
    assert summary["depositableValidatorsCount"] == no["depositableValidatorsCount"]


def test_csm_decrease_vetted_keys(csm, depositable_node_operator, stranger):
    (node_operator, keys_count) = depositable_node_operator
    total_added_keys = csm.getNodeOperator(node_operator)["totalAddedKeys"]
    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(CSM_MODULE_ID)
    unvet_args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=CSM_MODULE_ID,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(node_operator, 16),
        vetted_signing_keys_counts=to_bytes(total_added_keys - keys_count, 32),
    )

    set_single_guardian(contracts.deposit_security_module, contracts.agent, stranger)

    contracts.deposit_security_module.unvetSigningKeys(*unvet_args.to_tuple(), (0, 0), {"from": stranger.address})

    no = csm.getNodeOperator(node_operator)
    assert no["totalVettedKeys"] == total_added_keys - keys_count


def test_csm_penalize_node_operator(csm, accounting, node_operator, helpers):
    bond_shares_before = accounting.getBondShares(node_operator)
    withdrawal_info = (node_operator, 0, ETH(30))
    tx = csm.submitWithdrawals([withdrawal_info], {"from": contracts.cs_verifier})
    assert "StETHBurnRequested" in tx.events
    burnt_shares = tx.events["StETHBurnRequested"]["amountOfShares"]
    assert accounting.getBondShares(node_operator) == bond_shares_before - burnt_shares


def test_csm_eth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))

    bond_shares_before = accounting.getBondShares(node_operator)
    shares = contracts.lido.getSharesByPooledEth(ETH(1))
    accounting.depositETH(node_operator, {"from": manager_address, "value": ETH(1)})
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


def test_csm_steth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))

    bond_shares_before = accounting.getBondShares(node_operator)
    contracts.lido.submit(ZERO_ADDRESS, {"from": manager_address, "value": ETH(1.5)})
    contracts.lido.approve(accounting, ETH(2), {"from": manager_address})

    shares = contracts.lido.getSharesByPooledEth(ETH(1))
    accounting.depositStETH(node_operator, ETH(1), (0, 0, 0, 0, 0), {"from": manager_address})
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


def test_csm_wsteth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))
    contracts.lido.submit(ZERO_ADDRESS, {"from": manager_address, "value": ETH(1.5)})
    contracts.lido.approve(contracts.wsteth, ETH(1.5), {"from": manager_address})
    contracts.wsteth.wrap(ETH(1.5), {"from": manager_address})
    contracts.wsteth.approve(accounting, contracts.wsteth.balanceOf(manager_address), {"from": manager_address})

    shares = contracts.lido.getSharesByPooledEth(
        contracts.wsteth.getStETHByWstETH(contracts.wsteth.balanceOf(manager_address))
    )
    bond_shares_before = accounting.getBondShares(node_operator)
    accounting.depositWstETH(
        node_operator, contracts.wsteth.balanceOf(manager_address), (0, 0, 0, 0, 0), {"from": manager_address}
    )
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


def test_csm_claim_rewards_steth(csm, accounting, node_operator, ref_slot):
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    shares_before = contracts.lido.sharesOf(reward_address)

    distributed_shares, tree = distribute_reward_tree(node_operator, ref_slot)
    cumulative_shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, cumulative_shares)))))
    claimable_bond_shares_before = accounting.getClaimableBondShares(node_operator)

    accounting.claimRewardsStETH(node_operator, ETH(999), cumulative_shares, proof, {"from": reward_address})

    shares_after = contracts.lido.sharesOf(reward_address)
    assert shares_after == shares_before + distributed_shares + claimable_bond_shares_before


def test_csm_claim_rewards_wsteth(csm, accounting, node_operator, ref_slot):
    _, tree = distribute_reward_tree(node_operator, ref_slot)
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    wsteth_before = contracts.wsteth.balanceOf(reward_address)

    accounting.claimRewardsWstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})
    assert contracts.wsteth.balanceOf(reward_address) > wsteth_before


def test_csm_claim_rewards_eth(csm, accounting, node_operator, ref_slot):
    _, tree = distribute_reward_tree(node_operator, ref_slot)
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    withdrawal_requests = contracts.withdrawal_queue.getWithdrawalRequests(reward_address)

    accounting.claimRewardsUnstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})

    assert len(contracts.withdrawal_queue.getWithdrawalRequests(reward_address)) == len(withdrawal_requests) + 1


def test_csm_remove_key(csm, parameters_registry, accounting, node_operator):
    csm_upload_keys(csm, accounting, node_operator, 1)

    no = csm.getNodeOperator(node_operator)
    keys_before = no["totalAddedKeys"]
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    tx = csm.removeKeys(node_operator, keys_before - 1, 1, {"from": manager_address})

    assert "KeyRemovalChargeApplied" in tx.events
    assert "BondCharged" in tx.events

    expected_charge_amount = contracts.lido.getPooledEthByShares(
        contracts.lido.getSharesByPooledEth(parameters_registry.getKeyRemovalCharge(accounting.DEFAULT_BOND_CURVE_ID()))
    )
    assert tx.events["BondCharged"]["toChargeAmount"] == expected_charge_amount
    no = csm.getNodeOperator(node_operator)
    assert no["totalAddedKeys"] == keys_before - 1


def test_eject_bad_performer(csm, ejector, strikes, node_operator, stranger):
    index_to_eject = 0
    pubkey_to_eject = csm.getSigningKeys(node_operator, index_to_eject, 1)
    leaf_to_eject = (node_operator, pubkey_to_eject, [1, 1, 1, 0, 0, 0])
    another_pubkey = csm.getSigningKeys(node_operator, index_to_eject + 1, 1)
    strikes_tree = StrikesTree.new(
        [leaf_to_eject, (node_operator, another_pubkey, [1, 1, 0, 0, 0, 0])]
    )
    index_in_tree = strikes_tree.tree.find(strikes_tree.tree.leaf(leaf_to_eject))
    proof, flags = strikes_tree.tree.get_multi_proof([index_in_tree])
    strikes.processOracleReport(
        strikes_tree.root,
        "QmTest123456789",
        {"from": contracts.cs_fee_oracle}
    )

    eject_payment_value = get_sys_fee_to_eject()

    bad_performer = (node_operator, index_to_eject, [1, 1, 1, 0, 0, 0])
    tx = strikes.processBadPerformanceProof(
        [bad_performer],
        proof,
        flags,
        ZERO_ADDRESS,
        {"value": eject_payment_value, "from": stranger}
    )
    assert "StrikesPenaltyProcessed" in tx.events
    assert tx.events["StrikesPenaltyProcessed"]["nodeOperatorId"] == node_operator
    assert tx.events["StrikesPenaltyProcessed"]["pubkey"] == pubkey_to_eject
    penalty = contracts.cs_parameters_registry.defaultBadPerformancePenalty()
    assert tx.events["StrikesPenaltyProcessed"]["strikesPenalty"] == penalty

    assert "TriggeredExitFeeRecorded" in tx.events
    assert tx.events["TriggeredExitFeeRecorded"]["nodeOperatorId"] == node_operator
    assert tx.events["TriggeredExitFeeRecorded"]["pubkey"] == pubkey_to_eject
    assert tx.events["TriggeredExitFeeRecorded"]["exitType"] == 1
    assert tx.events["TriggeredExitFeeRecorded"]["withdrawalRequestPaidFee"] == eject_payment_value
    assert tx.events["TriggeredExitFeeRecorded"]["withdrawalRequestRecordedFee"] == eject_payment_value


def test_voluntary_eject(csm, ejector, node_operator):
    eject_payment_value = get_sys_fee_to_eject()
    operator_address = csm.getNodeOperatorOwner(node_operator)

    tx = ejector.voluntaryEject(
        node_operator, 0, 1, ZERO_ADDRESS, {"value": eject_payment_value, "from": operator_address}
    )
    assert "TriggeredExitFeeRecorded" not in tx.events


def test_report_validator_exit_delay(csm, node_operator):
    pubkey = csm.getSigningKeys(node_operator, 0, 1)
    day_in_seconds = 60 * 60 * 24

    tx = csm.reportValidatorExitDelay(node_operator, 0, pubkey, 7 * day_in_seconds, {"from": contracts.staking_router})
    assert "ValidatorExitDelayProcessed" in tx.events
    assert tx.events["ValidatorExitDelayProcessed"]["nodeOperatorId"] == node_operator
    assert tx.events["ValidatorExitDelayProcessed"]["pubkey"] == pubkey
    penalty = contracts.cs_parameters_registry.defaultExitDelayPenalty()
    assert tx.events["ValidatorExitDelayProcessed"]["delayPenalty"] == penalty


def test_on_validator_exit_triggered(csm, node_operator):
    eject_payment_value = 1
    pubkey = csm.getSigningKeys(node_operator, 0, 1)
    exit_type = 3

    tx = csm.onValidatorExitTriggered(node_operator, pubkey, 1, exit_type, {"from": contracts.staking_router})
    assert "TriggeredExitFeeRecorded" in tx.events
    assert tx.events["TriggeredExitFeeRecorded"]["nodeOperatorId"] == node_operator
    assert tx.events["TriggeredExitFeeRecorded"]["pubkey"] == pubkey
    assert tx.events["TriggeredExitFeeRecorded"]["exitType"] == exit_type
    assert tx.events["TriggeredExitFeeRecorded"]["withdrawalRequestPaidFee"] == eject_payment_value
    assert tx.events["TriggeredExitFeeRecorded"]["withdrawalRequestRecordedFee"] == eject_payment_value


def test_easy_track_csm_settle_el_stealing_penalty(csm, accounting, node_operator, stranger):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))
    accounting.depositETH(node_operator, {"from": manager_address, "value": ETH(1)})

    csm.reportELRewardsStealingPenalty(node_operator, b'\x00' * 32, ETH(0.5), {"from": CSM_COMMITTEE_MS})

    motions_before = contracts.easy_track.getMotions()

    calldata = _encode_calldata(["uint256[]"], [[node_operator]])
    tx = contracts.easy_track.createMotion(EASYTRACK_CSM_SETTLE_EL_REWARDS_STEALING_PENALTY_FACTORY, calldata, {"from": CSM_COMMITTEE_MS})

    motions = contracts.easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    bond_before = accounting.getBond(node_operator)

    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    bond_after = accounting.getBond(node_operator)

    assert bond_before > bond_after, "Bond should be decreased after settling penalty"


def test_easy_track_csm_set_vetted_gate_tree(
    csm, accounting, node_operator, stranger
):
    motions_before = contracts.easy_track.getMotions()

    new_tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    new_tree_cid = "QmTest123456789"
    calldata = _encode_calldata(["bytes32", "string"], [new_tree_root, new_tree_cid])

    tx = contracts.easy_track.createMotion(EASYTRACK_CS_SET_VETTED_GATE_TREE_FACTORY, calldata, {"from": CSM_COMMITTEE_MS})

    motions = contracts.easy_track.getMotions()
    assert len(motions) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    vetted_gate_tree_root_after = contracts.cs_vetted_gate.treeRoot()
    vetted_gate_tree_cid_after = contracts.cs_vetted_gate.treeCid()

    assert vetted_gate_tree_root_after == ("0x" + new_tree_root.hex()), "Tree root not updated"
    assert vetted_gate_tree_cid_after == new_tree_cid, "Tree CID not updated"
