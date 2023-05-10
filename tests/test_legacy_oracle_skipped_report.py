import os
from datetime import datetime

import pytest
from brownie import accounts, web3, chain, interface, reverts
from utils.test.oracle_report_helpers import oracle_report
from utils.import_current_votes import get_vote_script_file_by_name
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import (
    contracts,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    LDO_VOTE_EXECUTORS_FOR_TESTS,
    MAINNET_VOTE_DURATION,
    lido_dao_legacy_oracle,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
)

ONE_HOUR = 1 * 60 * 60
SECONDS_PER_EPOCH = CHAIN_SLOTS_PER_EPOCH * CHAIN_SECONDS_PER_SLOT


def start_vote_by_name(vote_name):
    vote_file = get_vote_script_file_by_name(vote_name)

    script_name = os.path.splitext(os.path.basename(vote_file))[0]
    name_for_import = "scripts." + script_name
    start_vote_name = f"start_vote_{script_name}"
    exec(f"from {name_for_import} import start_vote as {start_vote_name}")
    start_vote = locals()[start_vote_name]

    vote_id, _ = start_vote({"from": LDO_HOLDER_ADDRESS_FOR_TESTS}, silent=True)

    topup = "0.5 ether"
    print(f"Vote #{vote_id}")
    for holder_addr in LDO_VOTE_EXECUTORS_FOR_TESTS:
        print("voting from acct:", holder_addr)
        if accounts.at(holder_addr, force=True).balance() < topup:
            accounts[0].transfer(holder_addr, topup)
        account = accounts.at(holder_addr, force=True)
        contracts.voting.vote(vote_id, True, False, {"from": account})

    return vote_id


def execute_vote_by_id(vote_id):
    assert contracts.voting.canExecute(vote_id)
    executor_addr = contracts.voting.getEVMScriptExecutor(EMPTY_CALLSCRIPT)
    try:
        _ = interface.CallsScript(executor_addr)
    except:
        print("Unable to instantiate CallsScript")
        print("Trying to proceed further as is...")

    execution_transactions = []
    tx = contracts.voting.executeVote(vote_id, {"from": accounts[0]})
    print(f"vote #{vote_id} executed")
    execution_transactions.append(tx)
    return execution_transactions


def legacy_report(_epochId, _beaconBalance, _beaconValidators):
    oracle = interface.LidoOracle(lido_dao_legacy_oracle)
    quorum = oracle.getQuorum()
    members = oracle.getOracleMembers()

    for i in range(quorum):
        member = accounts.at(members[i], force=True)
        oracle.reportBeacon(_epochId, _beaconBalance, _beaconValidators, {"from": member})

@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def test_legacy_oracle_report_skipped():
    # we don't track real reference slots in this tests purposefully
    # because this test doesn't rely on exact slot numbers
    # the only meaningful check — trying to send first oracle report using an arbitrary reference slot
    # BEFORE the upgraded contracts were activated via the upgrade vote

    # start voting, but not sleep — only start and do votes
    vote_id = start_vote_by_name("shapella")

    # mine block in a hour before upgrade
    chain.sleep(MAINNET_VOTE_DURATION)
    chain.mine(1)

    # remember this block
    block_number_hour_before_upgrade = web3.eth.block_number

    # wait for upgrade
    chain.sleep(ONE_HOUR)
    chain.mine(1)

    # execute upgrade voting
    execute_vote_by_id(vote_id)

    # trying report for historical data when was no report from LidoOracle
    with reverts("NON_EMPTY_DATA"):
        oracle_report(simulation_block_identifier=block_number_hour_before_upgrade, wait_to_next_report_time=False)

    # Waiting
    chain.sleep(23 * ONE_HOUR)
    chain.mine(1)
    block_number_23_hours_after_upgrade = web3.eth.block_number
    chain.sleep(ONE_HOUR)
    chain.mine(1)

    # Now oracle report can pass because contracts were upgraded
    oracle_report(simulation_block_identifier=block_number_23_hours_after_upgrade, wait_to_next_report_time=False)

def chain_sleep(slots):
    chain.sleep(CHAIN_SECONDS_PER_SLOT * slots)
    chain.mine(slots)


def wait_for_next_reportable_epoch():
    oracle = interface.LidoOracle(lido_dao_legacy_oracle)

    current_epoch_id = oracle.getCurrentEpochId()
    next_expected_epoch_id = oracle.getExpectedEpochId()
    epochs_to_sleep = next_expected_epoch_id - current_epoch_id

    chain_sleep(CHAIN_SLOTS_PER_EPOCH * epochs_to_sleep)


def test_legacy_oracle_happy_path():
    oracle = interface.LidoOracle(lido_dao_legacy_oracle)

    # Align chain to next oracle report
    wait_for_next_reportable_epoch()

    expected_epoch_id = oracle.getExpectedEpochId()
    beacon_stats = contracts.lido.getBeaconStat()
    legacy_report(expected_epoch_id, beacon_stats["beaconBalance"]//10 ** 9, beacon_stats["beaconValidators"])
    print("Legacy report ", datetime.fromtimestamp(chain.time()))

    ## Wait for 2 hours after oracle report
    slots_to_mine = 2 * ONE_HOUR // CHAIN_SECONDS_PER_SLOT
    chain_sleep(slots_to_mine)

    # prepare upgrade
    prepare_for_shapella_upgrade_voting(silent=True)

    # start voting, but not sleep — only start and do votes
    vote_id = start_vote_by_name("shapella")
    print("Vote started ", datetime.fromtimestamp(chain.time()))


    # Regular reports
    for i in range(3):
        wait_for_next_reportable_epoch()
        expected_epoch_id = oracle.getExpectedEpochId()
        beacon_stats = contracts.lido.getBeaconStat()
        legacy_report(expected_epoch_id, beacon_stats["beaconBalance"]//10 ** 9, beacon_stats["beaconValidators"])
        print("Legacy report ", datetime.fromtimestamp(chain.time()))


    ## Wait for 2 hours after oracle report
    slots_to_mine = 2 * ONE_HOUR // CHAIN_SECONDS_PER_SLOT
    chain_sleep(slots_to_mine + 32)

    assert contracts.voting.canExecute(vote_id)

    # execute upgrade voting
    execute_vote_by_id(vote_id)
    print("Vote executed ", datetime.fromtimestamp(chain.time()))

    # wait for 1 slot before next reportable epoch
    consensus_current_slot = (chain.time() - CHAIN_GENESIS_TIME) // CHAIN_SECONDS_PER_SLOT
    consensus_initial_ref_slot = contracts.hash_consensus_for_accounting_oracle.getInitialRefSlot()
    chain_sleep(consensus_initial_ref_slot - consensus_current_slot - 2)
    print("Sleep before report ability ", datetime.fromtimestamp(chain.time()))

    with reverts():
        contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()

    with reverts():
        oracle_report(wait_to_next_report_time=False, skip_withdrawals=True, refSlot=consensus_initial_ref_slot)

    # Accounting oracle report
    chain_sleep(2)
    oracle_report(wait_to_next_report_time=False, skip_withdrawals=True)
    print("Accounting oracle report ", datetime.fromtimestamp(chain.time()))


@pytest.mark.parametrize("legacy_reports", [0, 1, 2])
def test_legacy_oracle_report_skipped(legacy_reports):
    oracle = interface.LidoOracle(lido_dao_legacy_oracle)

    # Align chain to next oracle report
    wait_for_next_reportable_epoch()

    expected_epoch_id = oracle.getExpectedEpochId()
    beacon_stats = contracts.lido.getBeaconStat()
    legacy_report(expected_epoch_id, beacon_stats["beaconBalance"]//10 ** 9, beacon_stats["beaconValidators"])
    print("Legacy report ", datetime.fromtimestamp(chain.time()))

    ## Wait for 2 hours after oracle report
    slots_to_mine = 2 * ONE_HOUR // CHAIN_SECONDS_PER_SLOT
    chain_sleep(slots_to_mine)

    # prepare upgrade
    prepare_for_shapella_upgrade_voting(silent=True)

    # start voting, but not sleep — only start and do votes
    vote_id = start_vote_by_name("shapella")
    print("Vote started ", datetime.fromtimestamp(chain.time()))
    vote_start_block = chain.height

    # Regular reports
    for i in range(legacy_reports):
        wait_for_next_reportable_epoch()
        expected_epoch_id = oracle.getExpectedEpochId()
        beacon_stats = contracts.lido.getBeaconStat()
        legacy_report(expected_epoch_id, beacon_stats["beaconBalance"]//10 ** 9, beacon_stats["beaconValidators"])
        print("Legacy report ", datetime.fromtimestamp(chain.time()))

    print(vote_start_block + 72 * ONE_HOUR // CHAIN_SECONDS_PER_SLOT - chain.height + 1)

    chain_sleep(vote_start_block + 72 * ONE_HOUR // CHAIN_SECONDS_PER_SLOT - chain.height + 2)

    assert contracts.voting.canExecute(vote_id)

    # execute upgrade voting
    execute_vote_by_id(vote_id)
    print("Vote executed ", datetime.fromtimestamp(chain.time()))

    # Accounting oracle report
    chain_sleep(1)
    oracle_report(wait_to_next_report_time=False, skip_withdrawals=True)
    print("Accounting oracle report ", datetime.fromtimestamp(chain.time()))
