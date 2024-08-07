import pytest
from utils.test.extra_data import ExtraDataService
from utils.test.node_operators_helpers import RewardDistributionState
from utils.test.oracle_report_helpers import oracle_report, reach_consensus
from utils.config import contracts


@pytest.fixture()
def extra_data_service():
    return ExtraDataService()

@pytest.fixture(scope="module")
def accounting_oracle(interface):
    return interface.AccountingOracle(contracts.accounting_oracle)


@pytest.fixture
def nor(interface):
    return interface.NodeOperatorsRegistry(contracts.node_operators_registry.address)

def get_exited_count(node_operator_id):
    no = contracts.node_operators_registry.getNodeOperator(node_operator_id, False)
    return no["totalExitedValidators"]

def test_accounting_oracle_too_node_ops_per_extra_data_item(extra_data_service):
    nos_per_item_count = 10
    item_count = 2

    extra_data = extra_data_service.collect(
        {(1, i): i for i in range(20, 20 + nos_per_item_count)},
        {(1, i): get_exited_count(i) for i in range(20, 20 + nos_per_item_count)},
        item_count,
        nos_per_item_count,
    )

    oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=item_count,
        extraDataList=extra_data.extra_data_list,
    )

def test_accounting_oracle_extra_data_splitted_on_multiple_chunks(extra_data_service, accounting_oracle, nor):
    staking_module_id = 1
    max_no_in_payload_count = 3
    max_items_count = 1

    extra_data = extra_data_service.collect(
        {(staking_module_id, i): i for i in range(20, 20 + max_no_in_payload_count)},
        {(staking_module_id, i): get_exited_count(i) for i in range(20, 20 + max_no_in_payload_count)},
        max_items_count,
        max_no_in_payload_count,
    )

    assert extra_data.format == 1
    assert extra_data.items_count ==2
    assert len(extra_data.extra_data_list) == 2
    assert len(extra_data.extra_data_hash_list) == 2

    report = oracle_report(
        extraDataFormat=1,
        extraDataHashList=extra_data.extra_data_hash_list,
        extraDataItemsCount=extra_data.items_count,
        extraDataList=extra_data.extra_data_list,
        dry_run=True,
    )

    consensusVersion = accounting_oracle.getConsensusVersion()
    oracleVersion = accounting_oracle.getContractVersion()

    submitter = reach_consensus(
        report.refSlot,
        report.hash,
        consensusVersion,
        contracts.hash_consensus_for_accounting_oracle
    )

    accounting_oracle.submitReportData(report.items, oracleVersion, {"from": submitter})

    processing_state_after_main_report_submitted = accounting_oracle.getProcessingState()
    assert processing_state_after_main_report_submitted["extraDataSubmitted"] == False
    assert processing_state_after_main_report_submitted["extraDataItemsCount"] == 2
    assert processing_state_after_main_report_submitted["extraDataItemsSubmitted"] == 0
    assert nor.getRewardDistributionState() == RewardDistributionState.TransferredToModule.value

    accounting_oracle.submitReportExtraDataList(extra_data.extra_data_list[0], {"from": submitter})

    processing_state_after_first_extra_data_submitted = accounting_oracle.getProcessingState()
    assert processing_state_after_first_extra_data_submitted["extraDataSubmitted"] == False
    assert processing_state_after_first_extra_data_submitted["extraDataItemsCount"] == 2
    assert processing_state_after_first_extra_data_submitted["extraDataItemsSubmitted"] == 1
    assert nor.getRewardDistributionState() == RewardDistributionState.TransferredToModule.value

    accounting_oracle.submitReportExtraDataList(extra_data.extra_data_list[1], {"from": submitter})

    processing_state_after_second_extra_data_submitted = accounting_oracle.getProcessingState()
    assert processing_state_after_second_extra_data_submitted["extraDataSubmitted"] == True
    assert processing_state_after_second_extra_data_submitted["extraDataItemsCount"] == 2
    assert processing_state_after_second_extra_data_submitted["extraDataItemsSubmitted"] == 2
    assert nor.getRewardDistributionState() == RewardDistributionState.ReadyForDistribution.value
