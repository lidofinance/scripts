import pytest

from brownie import reverts, web3, ZERO_ADDRESS, accounts

from utils.balance import set_balance_in_wei
from utils.config import (
    contracts,
    ContractsLazyLoader,
)
from utils.dsm import UnvetArgs, to_bytes, set_single_guardian
from utils.evm_script import encode_error
from utils.staking_module import calc_module_reward_shares
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member, csm_upload_keys, get_ea_members
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import (
    oracle_report, wait_to_next_available_report_time, prepare_csm_report,
    reach_consensus,
)
from utils.test.staking_router_helpers import (
    set_staking_module_status, StakingModuleStatus,
    increase_staking_module_share,
)

contracts: ContractsLazyLoader = contracts

CSM_MODULE_ID = 3
MAX_DEPOSITS = 50


@pytest.fixture(scope="module")
def csm():
    return contracts.csm


@pytest.fixture(scope="module")
def accounting():
    return contracts.cs_accounting


@pytest.fixture(scope="module")
def fee_distributor():
    return contracts.cs_fee_distributor


@pytest.fixture(scope="module")
def fee_oracle():
    return contracts.cs_fee_oracle


@pytest.fixture(scope="module")
def early_adoption():
    return contracts.cs_early_adoption


@pytest.fixture
def node_operator(csm, accounting) -> int:
    address, proof = get_ea_member()
    return csm_add_node_operator(csm, accounting, address, proof)


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
    contracts.lido.removeStakingLimit({"from": accounts.at(contracts.voting, force=True)})


@pytest.fixture
def deposits_to_csm(csm, pause_modules, node_operator, remove_stake_limit):
    (_, _, depositable) = csm.getStakingModuleSummary()
    fill_deposit_buffer(depositable)
    increase_staking_module_share(module_id=CSM_MODULE_ID, share_multiplier=2)
    for i in range(0, depositable, MAX_DEPOSITS):
        contracts.lido.deposit(MAX_DEPOSITS, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})


@pytest.fixture
def ref_slot():
    wait_to_next_available_report_time(contracts.csm_hash_consensus)
    ref_slot, _ = contracts.csm_hash_consensus.getCurrentFrame()
    return ref_slot


def distribute_reward_tree(node_operator, ref_slot):
    consensus_version = contracts.cs_fee_oracle.getConsensusVersion()
    oracle_version = contracts.cs_fee_oracle.getContractVersion()
    claimable_shares = contracts.cs_fee_distributor.totalClaimableShares()

    rewards = ETH(0.05)
    oracle_report(cl_diff=rewards)
    distributed_shares = contracts.lido.sharesOf(contracts.cs_fee_distributor) - claimable_shares
    assert distributed_shares > 0

    report, report_hash, tree = prepare_csm_report({node_operator: distributed_shares}, ref_slot)

    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.csm_hash_consensus,
    )

    contracts.cs_fee_oracle.submitReportData(report, oracle_version, {"from": submitter})
    return tree


@pytest.mark.parametrize("address, proof", get_ea_members())
def test_add_ea_node_operator(csm, accounting, early_adoption, address, proof):
    no_id = csm_add_node_operator(csm, accounting, address, proof)
    no = csm.getNodeOperator(no_id)

    assert no['managerAddress'] == address
    assert no['rewardAddress'] == address
    assert accounting.getBondCurveId(no_id) == early_adoption.CURVE_ID()


def test_add_node_operator_permissionless(csm, accounting, accounts):
    address = accounts[8].address
    no_id = csm_add_node_operator(csm, accounting, address, proof=[])
    no = csm.getNodeOperator(no_id)

    assert no['managerAddress'] == address
    assert no['rewardAddress'] == address
    assert accounting.getBondCurveId(no_id) == accounting.DEFAULT_BOND_CURVE_ID()


def test_add_node_operator_keys_more_than_limit(csm, accounting):
    address, proof = get_ea_member()
    keys_count = csm.MAX_SIGNING_KEYS_PER_OPERATOR_BEFORE_PUBLIC_RELEASE() + 1
    no_id = csm_add_node_operator(csm, accounting, address, proof, keys_count=keys_count)
    no = csm.getNodeOperator(no_id)

    assert no["totalAddedKeys"] == keys_count


def test_add_node_operator_permissionless_keys_more_than_limit(csm, accounting, accounts):
    keys_count = csm.MAX_SIGNING_KEYS_PER_OPERATOR_BEFORE_PUBLIC_RELEASE() + 1
    address = accounts[8].address
    no_id = csm_add_node_operator(csm, accounting, address, proof=[], keys_count=keys_count)
    no = csm.getNodeOperator(no_id)

    assert no["totalAddedKeys"] == keys_count


def test_upload_keys_more_than_limit(csm, accounting, node_operator):
    no = csm.getNodeOperator(node_operator)
    keys_before = no["totalAddedKeys"]
    keys_count = csm.MAX_SIGNING_KEYS_PER_OPERATOR_BEFORE_PUBLIC_RELEASE() - keys_before + 1
    csm_upload_keys(csm, accounting, node_operator, keys_count)

    no = csm.getNodeOperator(node_operator)
    assert no["totalAddedKeys"] == keys_count + keys_before


@pytest.mark.usefixtures("pause_modules")
def test_deposit(node_operator, csm, remove_stake_limit):
    (_, _, depositable_validators_count) = csm.getStakingModuleSummary()
    deposits_count = depositable_validators_count
    fill_deposit_buffer(deposits_count)
    increase_staking_module_share(module_id=CSM_MODULE_ID, share_multiplier=2)

    for i in range(0, deposits_count, MAX_DEPOSITS):
        contracts.lido.deposit(MAX_DEPOSITS, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    no = csm.getNodeOperator(node_operator)
    assert no["totalDepositedKeys"] == no["totalAddedKeys"]


@pytest.mark.usefixtures("deposits_to_csm")
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
        CSM_MODULE_ID,
        node_operator,
        target_limit_mode,
        target_limit,
        {"from": contracts.agent}
    )

    no = csm.getNodeOperator(node_operator)
    assert no["targetLimitMode"] == target_limit_mode
    assert no["targetLimit"] == target_limit


def test_csm_update_refunded(node_operator):
    refunded_validators_count = 1
    with reverts(encode_error("NotSupported()")):
        contracts.staking_router.updateRefundedValidatorsCount(
            CSM_MODULE_ID,
            node_operator,
            refunded_validators_count,
            {"from": contracts.agent}
        )


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_report_exited(csm, node_operator, extra_data_service):
    total_exited = csm.getStakingModuleSummary()["totalExitedValidators"]
    exited_keys = 5
    extra_data = extra_data_service.collect({}, {(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys)
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


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_report_stuck(csm, node_operator, extra_data_service):
    total_exited = csm.getStakingModuleSummary()["totalExitedValidators"]
    stuck_keys = 5
    extra_data = extra_data_service.collect( {(CSM_MODULE_ID, node_operator): stuck_keys}, {}, stuck_keys, stuck_keys)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[total_exited],
    )

    no = csm.getNodeOperator(node_operator)
    assert no["stuckValidatorsCount"] == stuck_keys


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_get_staking_module_summary(csm, accounting, node_operator, extra_data_service, remove_stake_limit):
    (exited_before, deposited_before, depositable_before) = contracts.staking_router.getStakingModuleSummary(CSM_MODULE_ID)

    # Assure there are new exited keys
    exited_keys = 5
    extra_data = extra_data_service.collect({}, {(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys)
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
    for i in range(0, deposits_count, MAX_DEPOSITS):
        contracts.lido.deposit(MAX_DEPOSITS, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    (exited_after, deposited_after, depositable_after) = contracts.staking_router.getStakingModuleSummary(CSM_MODULE_ID)

    assert exited_after == exited_before + exited_keys
    assert deposited_after == deposited_before + deposits_count
    assert depositable_after == depositable_before + new_depositable


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_get_node_operator_summary(csm, node_operator, extra_data_service):
    total_exited = csm.getStakingModuleSummary()["totalExitedValidators"]
    no = csm.getNodeOperator(node_operator)
    exited_keys = 1
    stuck_keys = 1
    extra_data = extra_data_service.collect({(CSM_MODULE_ID, node_operator): stuck_keys}, {(CSM_MODULE_ID, node_operator): exited_keys}, 2, 2)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=2,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[total_exited],
    )

    summary = contracts.staking_router.getNodeOperatorSummary(CSM_MODULE_ID, node_operator)
    assert summary["targetLimitMode"] == 0
    assert summary["targetValidatorsCount"] == 0
    assert summary["stuckValidatorsCount"] == stuck_keys
    assert summary["refundedValidatorsCount"] == 0
    assert summary["stuckPenaltyEndTimestamp"] == 0
    assert summary["totalExitedValidators"] == exited_keys
    assert summary["totalDepositedValidators"] == no["totalDepositedKeys"]
    assert summary["depositableValidatorsCount"] == 0


def test_csm_decrease_vetted_keys(csm, node_operator, stranger):
    block_number = web3.eth.get_block_number()
    block = web3.eth.get_block(block_number)
    staking_module_nonce = contracts.staking_router.getStakingModuleNonce(CSM_MODULE_ID)
    unvet_args = UnvetArgs(
        block_number=block_number,
        block_hash=block.hash,
        staking_module_id=CSM_MODULE_ID,
        nonce=staking_module_nonce,
        node_operator_ids=to_bytes(node_operator, 16),
        vetted_signing_keys_counts=to_bytes(1, 32),
    )

    set_single_guardian(contracts.deposit_security_module, contracts.agent, stranger)

    contracts.deposit_security_module.unvetSigningKeys(*unvet_args.to_tuple(), (0, 0), {"from": stranger.address})

    no = csm.getNodeOperator(node_operator)
    assert no["totalVettedKeys"] == 1


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_penalize_node_operator(csm, accounting, node_operator, helpers):
    bond_shares_before = accounting.getBondShares(node_operator)
    tx = csm.submitInitialSlashing(node_operator, 0, {"from": contracts.cs_verifier})
    assert "StETHBurnRequested" in tx.events
    burnt_shares = tx.events["StETHBurnRequested"]["amountOfShares"]
    assert accounting.getBondShares(node_operator) == bond_shares_before - burnt_shares


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_eth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))

    bond_shares_before = accounting.getBondShares(node_operator)
    shares = contracts.lido.getSharesByPooledEth(ETH(1))
    csm.depositETH(node_operator, {"from": manager_address, "value": ETH(1)})
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_steth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))

    bond_shares_before = accounting.getBondShares(node_operator)
    contracts.lido.submit(ZERO_ADDRESS, {"from": manager_address, "value": ETH(1.5)})
    contracts.lido.approve(accounting, ETH(2), {"from": manager_address})

    shares = contracts.lido.getSharesByPooledEth(ETH(1))
    csm.depositStETH(node_operator, ETH(1), (0, 0, 0, 0, 0), {"from": manager_address})
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_wsteth_bond(csm, accounting, node_operator):
    manager_address = csm.getNodeOperator(node_operator)["managerAddress"]
    set_balance_in_wei(manager_address, ETH(2))
    contracts.lido.submit(ZERO_ADDRESS, {"from": manager_address, "value": ETH(1.5)})
    contracts.lido.approve(contracts.wsteth, ETH(1.5), {"from": manager_address})
    contracts.wsteth.wrap(ETH(1.5), {"from": manager_address})
    contracts.wsteth.approve(accounting, contracts.wsteth.balanceOf(manager_address), {"from": manager_address})

    shares = contracts.lido.getSharesByPooledEth(contracts.wsteth.getStETHByWstETH(contracts.wsteth.balanceOf(manager_address)))
    bond_shares_before = accounting.getBondShares(node_operator)
    csm.depositWstETH(node_operator, contracts.wsteth.balanceOf(manager_address), (0, 0, 0, 0, 0), {"from": manager_address})
    assert accounting.getBondShares(node_operator) == bond_shares_before + shares


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_claim_rewards_steth(csm, node_operator, ref_slot):
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    shares_before = contracts.lido.sharesOf(reward_address)
    accounting_shares_before = contracts.lido.sharesOf(contracts.cs_accounting)

    tree = distribute_reward_tree(node_operator, ref_slot).tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))

    csm.claimRewardsStETH(node_operator, ETH(1), shares, proof, {"from": reward_address})
    shares_after = contracts.lido.sharesOf(reward_address)
    accounting_shares_after = contracts.lido.sharesOf(contracts.cs_accounting)
    assert shares_after == shares_before + (accounting_shares_before + shares - accounting_shares_after)

@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_claim_rewards_wsteth(csm, node_operator, ref_slot):
    tree = distribute_reward_tree(node_operator, ref_slot).tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    wsteth_before = contracts.wsteth.balanceOf(reward_address)

    csm.claimRewardsWstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})
    assert contracts.wsteth.balanceOf(reward_address) > wsteth_before

@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_claim_rewards_eth(csm, node_operator, ref_slot):
    tree = distribute_reward_tree(node_operator, ref_slot).tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    withdrawal_requests = contracts.withdrawal_queue.getWithdrawalRequests(reward_address)

    csm.claimRewardsUnstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})

    assert len(contracts.withdrawal_queue.getWithdrawalRequests(reward_address)) == len(withdrawal_requests) + 1
