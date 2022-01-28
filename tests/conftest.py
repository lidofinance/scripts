import pytest
import os

from typing import Optional

from brownie import chain

from utils.config import *

@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope='module')
def ldo_holder(accounts):
    return accounts.at(ldo_holder_address_for_tests, force=True)


@pytest.fixture(scope='module')
def dao_voting(interface):
    return interface.Voting(lido_dao_voting_address)

@pytest.fixture(scope='module')
def dao_agent(interface):
    return interface.Agent(lido_dao_agent_address)

@pytest.fixture(scope='module')
def node_operators_registry(interface):
    return interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)


@pytest.fixture(scope='module')
def dao_token_manager(interface):
    return interface.TokenManager(lido_dao_token_manager_address)


@pytest.fixture(scope='module')
def deposit_security_module(interface):
    return interface.DepositSecurityModule(lido_dao_deposit_security_module_address)


@pytest.fixture(scope='module')
def ldo_token(interface):
    return interface.ERC20(ldo_token_address)

@pytest.fixture(scope='module')
def lido(interface):
    return interface.Lido(lido_dao_steth_address)

@pytest.fixture(scope="module")
def acl(interface):
    return interface.ACL(lido_dao_acl_address)

@pytest.fixture(scope="module")
def oracle(interface):
    return interface.LidoOracle(lido_dao_oracle_address)

@pytest.fixture(scope="module")
def finance(interface):
    return interface.Finance(lido_dao_finance_address)

class Helpers:
    @staticmethod
    def execute_vote(accounts, vote_id, dao_voting, topup = '0.1 ether'):
        if dao_voting.getVote(vote_id)[0]:
            for holder_addr in ldo_vote_executors_for_tests:
                print('voting from acct:', holder_addr)
                accounts[0].transfer(holder_addr, topup)
                account = accounts.at(holder_addr, force=True)
                dao_voting.vote(vote_id, True, False, {'from': account})


        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert dao_voting.canExecute(vote_id)
        tx = dao_voting.executeVote(vote_id, {'from': accounts[0]})

        print(f'vote #{vote_id} executed')
        return tx

@pytest.fixture(scope='module')
def helpers():
    return Helpers

@pytest.fixture(scope='module')
def vote_id_from_env() -> Optional[int]:
    _env_name = "OMNIBUS_VOTE_ID"
    if os.getenv(_env_name):
        try:
            vote_id = int(os.getenv(_env_name))
            print(f'OMNIBUS_VOTE_ID env var is set, using existing vote #{vote_id}')
            return vote_id
        except:
            pass

    return None

@pytest.fixture(scope='module')
def bypass_events_decoding() -> bool:
    _env_name = "OMNIBUS_BYPASS_EVENTS_DECODING"
    if os.getenv(_env_name):
        print(f'Warning: OMNIBUS_BYPASS_EVENTS_DECODING env var is set, events decoding disabled')
        return True

    return False
