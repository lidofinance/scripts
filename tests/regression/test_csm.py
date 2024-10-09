import pytest

from brownie import reverts, web3

from utils.config import (
    contracts,
    ContractsLazyLoader,
)
from utils.dsm import UnvetArgs, to_bytes, set_single_guardian
from utils.evm_script import encode_error
from utils.test.csm_helpers import csm_add_node_operator, get_ea_member, csm_upload_keys
from utils.test.deposits_helpers import fill_deposit_buffer
from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import (
    oracle_report, wait_to_next_available_report_time, prepare_csm_report,
    reach_consensus,
)
from utils.test.staking_router_helpers import set_staking_module_status, StakingModuleStatus

contracts: ContractsLazyLoader = contracts

CSM_MODULE_ID = 3

pytestmark = pytest.mark.usefixtures("autoexecute_vote_ms")

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
def deposits_to_csm(csm, pause_modules, node_operator):
    (_, _, depositable) = csm.getStakingModuleSummary()
    fill_deposit_buffer(depositable)
    contracts.lido.deposit(depositable, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})


@pytest.fixture
def ref_slot():
    wait_to_next_available_report_time(contracts.csm_hash_consensus)
    ref_slot, _ = contracts.csm_hash_consensus.getCurrentFrame()
    return ref_slot


@pytest.fixture
def distribute_reward_tree(deposits_to_csm, fee_oracle, fee_distributor, node_operator, ref_slot):
    consensus_version = fee_oracle.getConsensusVersion()
    oracle_version = fee_oracle.getContractVersion()

    rewards = ETH(0.05)
    oracle_report(cl_diff=rewards)
    distributed_shares = contracts.lido.sharesOf(fee_distributor)
    assert distributed_shares > 0

    report, report_hash, tree = prepare_csm_report({node_operator: distributed_shares}, ref_slot)

    submitter = reach_consensus(
        ref_slot,
        report_hash,
        consensus_version,
        contracts.csm_hash_consensus,
    )

    fee_oracle.submitReportData(report, oracle_version, {"from": submitter})
    return tree


@pytest.mark.usefixtures("pause_modules")
def test_deposit(node_operator, csm):
    (_, _, depositable_validators_count) = csm.getStakingModuleSummary()
    deposits_count = depositable_validators_count
    fill_deposit_buffer(deposits_count)

    contracts.lido.deposit(deposits_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    no = csm.getNodeOperator(node_operator)
    assert no["totalDepositedKeys"] == no["totalAddedKeys"]


@pytest.mark.usefixtures("deposits_to_csm")
def test_mint_rewards_happy_path(csm, fee_distributor):
    csm_shares_before = contracts.lido.sharesOf(csm)
    fee_distributor_shares_before = contracts.lido.sharesOf(fee_distributor)

    oracle_report(cl_diff=ETH(1))

    assert csm_shares_before == contracts.lido.sharesOf(csm)
    assert contracts.lido.sharesOf(fee_distributor) > fee_distributor_shares_before


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
    exited_keys = 5
    extra_data = extra_data_service.collect({}, {(CSM_MODULE_ID, node_operator): exited_keys}, exited_keys, exited_keys)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[1],
    )

    no = csm.getNodeOperator(node_operator)
    assert no["totalExitedKeys"] == exited_keys

@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_report_stuck(csm, node_operator, extra_data_service):
    stuck_keys = 5
    extra_data = extra_data_service.collect( {(CSM_MODULE_ID, node_operator): stuck_keys}, {}, stuck_keys, stuck_keys)
    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=1,
        extraDataList=extra_data.extra_data_list,
        stakingModuleIdsWithNewlyExitedValidators=[CSM_MODULE_ID],
        numExitedValidatorsByStakingModule=[1],
    )

    no = csm.getNodeOperator(node_operator)
    assert no["stuckValidatorsCount"] == stuck_keys


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_get_staking_module_summary(csm, accounting, node_operator, extra_data_service):
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
        numExitedValidatorsByStakingModule=[1],
    )

    # Assure there are new deposited keys

    deposits_count = 3
    new_keys = 5
    new_depositable = new_keys - deposits_count
    csm_upload_keys(csm, accounting, node_operator, new_keys)
    fill_deposit_buffer(deposits_count)
    contracts.lido.deposit(deposits_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    (exited_after, deposited_after, depositable_after) = contracts.staking_router.getStakingModuleSummary(CSM_MODULE_ID)

    assert exited_after == exited_before + exited_keys
    assert deposited_after == deposited_before + deposits_count
    assert depositable_after == depositable_before + new_depositable


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_get_node_operator_summary(csm, node_operator, extra_data_service):
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
        numExitedValidatorsByStakingModule=[1],
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
def test_csm_claim_rewards_steth(csm, distribute_reward_tree, node_operator, fee_distributor):
    tree = distribute_reward_tree.tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    shares_before = contracts.lido.sharesOf(reward_address)

    csm.claimRewardsStETH(node_operator, ETH(1), shares, proof, {"from": reward_address})
    # subtract 10 to avoid rounding errors
    assert contracts.lido.sharesOf(reward_address) > shares_before + shares - 10

@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_claim_rewards_wsteth(csm, distribute_reward_tree, node_operator, fee_distributor):
    tree = distribute_reward_tree.tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    wsteth_before = contracts.wsteth.balanceOf(reward_address)

    csm.claimRewardsWstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})
    assert contracts.wsteth.balanceOf(reward_address) > wsteth_before

@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_claim_rewards_eth(csm, distribute_reward_tree, node_operator, fee_distributor):
    tree = distribute_reward_tree.tree
    shares = tree.values[0]["value"][1]
    proof = list(tree.get_proof(tree.find(tree.leaf((node_operator, shares)))))
    reward_address = csm.getNodeOperator(node_operator)["rewardAddress"]
    withdrawal_requests = contracts.withdrawal_queue.getWithdrawalRequests(reward_address)

    csm.claimRewardsUnstETH(node_operator, ETH(1), shares, proof, {"from": reward_address})

    assert len(contracts.withdrawal_queue.getWithdrawalRequests(reward_address)) == len(withdrawal_requests) + 1
