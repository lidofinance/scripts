import os

import pytest
from brownie import accounts, web3, chain, interface, reverts
from utils.test.oracle_report_helpers import oracle_report
from utils.import_current_votes import get_vote_script_file_by_name
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import (
    contracts,
    deployer_eoa,
    ldo_holder_address_for_tests,
    ldo_vote_executors_for_tests,
    MAINNET_VOTE_DURATION,
)
from utils.shapella_upgrade import prepare_for_shapella_upgrade_voting

ONE_HOUR = 1 * 60 * 60

def start_vote_by_name(vote_name):
    vote_file = get_vote_script_file_by_name(vote_name)

    script_name = os.path.splitext(os.path.basename(vote_file))[0]
    name_for_import = "scripts." + script_name
    start_vote_name = f"start_vote_{script_name}"
    exec(f"from {name_for_import} import start_vote as {start_vote_name}")
    start_vote = locals()[start_vote_name]

    vote_id, _ = start_vote({"from": ldo_holder_address_for_tests}, silent=True)

    topup = "0.5 ether"
    print(f"Vote #{vote_id}")
    for holder_addr in ldo_vote_executors_for_tests:
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


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


def test_legacy_oracle_report_skipped(helpers, vote_ids_from_env, accounts):
    # we don't track real reference slots in this tests purposefully
    # because this test doesn't rely on exact slot numbers
    # the only meaningful check — trying to send first oracle report using an arbitrary reference slot
    # BEFORE the upgraded contracts were activated via the upgrade vote

    # prepare upgrade
    prepare_for_shapella_upgrade_voting(deployer_eoa, silent=True)

    # start voting, but not sleep — only start and do votes
    vote_id = start_vote_by_name("shapella_1")

    # mine block in a hour before upgrade
    chain.sleep(MAINNET_VOTE_DURATION - ONE_HOUR)
    chain.mine(1)

    # remember thisblock
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
