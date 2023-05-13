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
    LEGACY_ORACLE,
    CHAIN_SLOTS_PER_EPOCH,
    CHAIN_SECONDS_PER_SLOT,
    CHAIN_GENESIS_TIME,
    VOTING,
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
    oracle = interface.LidoOracle(LEGACY_ORACLE)
    quorum = oracle.getQuorum()
    members = oracle.getOracleMembers()

    for i in range(quorum):
        member = accounts.at(members[i], force=True)
        oracle.reportBeacon(_epochId, _beaconBalance, _beaconValidators, {"from": member})

@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def chain_sleep(slots):
    chain.sleep(CHAIN_SECONDS_PER_SLOT * slots)
    chain.mine(slots)


def wait_for_next_reportable_epoch():
    oracle = interface.LidoOracle(LEGACY_ORACLE)

    current_epoch_id = oracle.getCurrentEpochId()
    next_expected_epoch_id = oracle.getExpectedEpochId()
    epochs_to_sleep = next_expected_epoch_id - current_epoch_id

    chain_sleep(CHAIN_SLOTS_PER_EPOCH * epochs_to_sleep)


def test_legacy_oracle_happy_path(vote_ids_from_env):
    oracle = interface.LidoOracle(LEGACY_ORACLE)
    voting = interface.Voting(VOTING)

    vote = voting.getVote(vote_ids_from_env[0])

    if vote["startDate"] + 72 * ONE_HOUR - chain.time() < 26 * ONE_HOUR:
        pytest.skip("all reports already done!")

    slots_to_sleep = (vote["startDate"] + 70 * ONE_HOUR - chain.time()) // CHAIN_SECONDS_PER_SLOT
    chain_sleep(slots_to_sleep)

    print("Wait for reportable epoch ", datetime.fromtimestamp(chain.time()))
    wait_for_next_reportable_epoch()
    (epoch_id, _, _) = oracle.getCurrentFrame()
    beacon_stats = contracts.lido.getBeaconStat()
    legacy_report(epoch_id, beacon_stats["beaconBalance"]//10 ** 9, beacon_stats["beaconValidators"])
    print("Legacy report ", datetime.fromtimestamp(chain.time()))

    slots_to_sleep = (vote["startDate"] +  72 * ONE_HOUR - chain.time()) // CHAIN_SECONDS_PER_SLOT + 10
    chain_sleep(slots_to_sleep)

    assert contracts.voting.canExecute(vote_ids_from_env[0])

    # execute upgrade voting
    execute_vote_by_id(vote_ids_from_env[0])
    print("Vote executed ", datetime.fromtimestamp(chain.time()))

    # wait for 1 slot before next reportable epoch
    consensus_current_slot = (chain.time() - CHAIN_GENESIS_TIME) // CHAIN_SECONDS_PER_SLOT
    consensus_initial_ref_slot = contracts.hash_consensus_for_accounting_oracle.getInitialRefSlot()
    print(consensus_initial_ref_slot, consensus_current_slot)
    chain_sleep(consensus_initial_ref_slot - consensus_current_slot - 2)

    with reverts():
        contracts.hash_consensus_for_accounting_oracle.getCurrentFrame()

    with reverts():
        oracle_report(wait_to_next_report_time=False, skip_withdrawals=True, refSlot=consensus_initial_ref_slot)

    # Accounting oracle report
    chain_sleep(2)
    oracle_report(wait_to_next_report_time=False, skip_withdrawals=True)
    print("Accounting oracle report ", datetime.fromtimestamp(chain.time()))


def test_legacy_oracle_report_skipped(vote_ids_from_env):
    oracle = interface.LidoOracle(LEGACY_ORACLE)
    voting = interface.Voting(VOTING)

    vote = voting.getVote(vote_ids_from_env[0])

    if vote["startDate"] + 72 * ONE_HOUR - chain.time() < 26 * ONE_HOUR:
        pytest.skip("all reports already done!")

    slots_to_sleep = (vote["startDate"] +  72 * ONE_HOUR - chain.time()) // CHAIN_SECONDS_PER_SLOT + 10
    chain_sleep(slots_to_sleep)

    print("Wait for vote can be executed ", datetime.fromtimestamp(chain.time()))
    assert contracts.voting.canExecute(vote_ids_from_env[0])

    # execute upgrade voting
    execute_vote_by_id(vote_ids_from_env[0])
    print("Vote executed ", datetime.fromtimestamp(chain.time()))

    # Accounting oracle report
    chain_sleep(1)
    oracle_report(wait_to_next_report_time=False, skip_withdrawals=True)
    print("Accounting oracle report ", datetime.fromtimestamp(chain.time()))
