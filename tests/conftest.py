import pytest

import os

from typing import Optional

from brownie import chain, interface

from utils.evm_script import EMPTY_CALLSCRIPT

from datetime import datetime

from utils.config import contracts
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes

from utils.config import (
    ldo_holder_address_for_tests,
    ldo_vote_executors_for_tests,
)
from utils.txs.deploy import deploy_from_prepared_tx


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def ldo_holder(accounts):
    return accounts.at(ldo_holder_address_for_tests, force=True)


@pytest.fixture(scope="module")
def unknown_person(accounts):
    return accounts.at("0x98ec059dc3adfbdd63429454aeb0c990fba4a128", force=True)


class Helpers:
    @staticmethod
    def filter_events_from(addr, events):
        return list(filter(lambda evt: evt.address == addr, events))

    @staticmethod
    def assert_single_event_named(evt_name, tx, evt_keys_dict):
        receiver_events = Helpers.filter_events_from(tx.receiver, tx.events[evt_name])
        assert len(receiver_events) == 1
        assert dict(receiver_events[0]) == evt_keys_dict

    @staticmethod
    def execute_vote(accounts, vote_id, dao_voting, topup="0.1 ether", skip_time=3 * 60 * 60 * 24):
        OBJECTION_PHASE_ID = 1
        if dao_voting.canVote(vote_id, ldo_vote_executors_for_tests[0]) and (
            dao_voting.getVotePhase(vote_id) != OBJECTION_PHASE_ID
        ):
            for holder_addr in ldo_vote_executors_for_tests:
                print("voting from acct:", holder_addr)
                if accounts.at(holder_addr, force=True).balance() < topup:
                    accounts[0].transfer(holder_addr, topup)
                account = accounts.at(holder_addr, force=True)
                dao_voting.vote(vote_id, True, False, {"from": account})

        # wait for the vote to end
        chain.sleep(skip_time)
        chain.mine()

        assert dao_voting.canExecute(vote_id)

        # try to instantiate script executor
        # to deal with events parsing properly
        # on fresh brownie setup cases (mostly for CI)
        executor_addr = dao_voting.getEVMScriptExecutor(EMPTY_CALLSCRIPT)
        try:
            _ = interface.CallsScript(executor_addr)
        except:
            print("Unable to instantiate CallsScript")
            print("Trying to proceed further as is...")

        tx = dao_voting.executeVote(vote_id, {"from": accounts[0]})

        print(f"vote #{vote_id} executed")
        return tx

    @staticmethod
    def is_executed(vote_id, dao_voting):
        vote_status = dao_voting.getVote(vote_id)
        return vote_status[1]


@pytest.fixture(scope="session")
def helpers():
    return Helpers


@pytest.fixture(scope="session")
def vote_id_from_env() -> Optional[int]:
    _env_name = "OMNIBUS_VOTE_ID"
    if os.getenv(_env_name):
        try:
            vote_id = int(os.getenv(_env_name))
            print(f"OMNIBUS_VOTE_ID env var is set, using existing vote #{vote_id}")
            return vote_id
        except:
            pass

    return None


@pytest.fixture(scope="module")
def bypass_events_decoding() -> bool:
    _env_name = "OMNIBUS_BYPASS_EVENTS_DECODING"
    if os.getenv(_env_name):
        print(f"Warning: OMNIBUS_BYPASS_EVENTS_DECODING env var is set, events decoding disabled")
        return True

    return False


@pytest.fixture(scope="module")
def autodeploy_contract(accounts):
    address = deploy_from_prepared_tx(accounts[0], "./utils/txs/tx-deploy-voting_for_upgrade.json")


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[0]


@pytest.fixture(scope="session", autouse=is_there_any_vote_scripts())
def autoexecute_vote(helpers, vote_id_from_env, accounts):
    if vote_id_from_env:
        helpers.execute_vote(vote_id=vote_id_from_env, accounts=accounts, dao_voting=contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)
