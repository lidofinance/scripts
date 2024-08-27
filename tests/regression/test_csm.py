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
from utils.test.oracle_report_helpers import oracle_report
from utils.test.staking_router_helpers import set_staking_module_status, StakingModuleStatus

contracts: ContractsLazyLoader = contracts

CSM_MODULE_ID = 3


@pytest.fixture(scope="module")
def csm():
    return contracts.csm


@pytest.fixture(scope="module")
def accounting():
    return contracts.cs_accounting


@pytest.fixture(scope="module")
def fee_distributor():
    return contracts.cs_fee_distributor


@pytest.fixture()
def node_operator(csm, accounting) -> int:
    address, proof = get_ea_member()
    return csm_add_node_operator(csm, accounting, address, proof)


@pytest.fixture()
def pause_modules():
    # pause deposit to all modules except csm
    # to be sure that all deposits go to csm
    modules = contracts.staking_router.getStakingModules()
    for module in modules:
        if module[0] != CSM_MODULE_ID:
            set_staking_module_status(module[0], StakingModuleStatus.Stopped)


@pytest.fixture()
def deposits_to_csm(csm, pause_modules, node_operator):
    (_, _, depositable) = csm.getStakingModuleSummary()
    fill_deposit_buffer(depositable)
    contracts.lido.deposit(depositable, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})


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
    address, _ = get_ea_member()
    csm_upload_keys(csm, accounting, node_operator, address, new_keys)
    fill_deposit_buffer(deposits_count)
    contracts.lido.deposit(deposits_count, CSM_MODULE_ID, "0x", {"from": contracts.deposit_security_module})

    (exited_after, deposited_after, depositable_after) = contracts.staking_router.getStakingModuleSummary(CSM_MODULE_ID)

    assert exited_after == exited_before + exited_keys
    assert deposited_after == deposited_before + deposits_count
    assert depositable_after == depositable_before + new_depositable


@pytest.mark.usefixtures("deposits_to_csm")
def test_csm_get_node_operator_summary(csm, node_operator, extra_data_service):
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
    assert summary["totalDepositedValidators"] == 5
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

