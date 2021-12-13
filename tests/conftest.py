import pytest

from typing import Optional, List

from brownie import chain
from brownie.network.transaction import TransactionReceipt
from brownie.network.event import EventDict, _EventItem

from utils.config import (ldo_token_address, lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          lido_dao_deposit_security_module_address,
                          lido_dao_steth_address, lido_dao_acl_address,
                          lido_dao_finance_address)

@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope='module')
def ldo_holder(accounts):
    return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da',
                       force=True)


@pytest.fixture(scope='module')
def dao_voting(interface):
    return interface.Voting(lido_dao_voting_address)


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
def finance(interface):
    return interface.Finance(lido_dao_finance_address)

class Helpers:
    @staticmethod
    def execute_vote(accounts, vote_id, dao_voting, topup = '0.1 ether'):
        ldo_holders = [
            '0x3e40d73eb977dc6a537af587d48316fee66e9c8c',
            '0xb8d83908aab38a159f3da47a59d84db8e1838712',
            '0xa2dfc431297aee387c05beef507e5335e684fbcd'
        ]

        if dao_voting.getVote(vote_id)[0]:
            for holder_addr in ldo_holders:
                        print('voting from acct:', holder_addr)
                        accounts[0].transfer(holder_addr, topup)
                        account = accounts.at(holder_addr, force=True)
                        dao_voting.vote(vote_id, True, False, {'from': account})


        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert dao_voting.canExecute(vote_id)
        tx = dao_voting.executeVote(vote_id, {'from': accounts[0]})

        print(f'vote executed')
        return tx

@pytest.fixture(scope='module')
def helpers():
    return Helpers()
