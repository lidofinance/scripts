import pytest
from brownie import chain

from utils.config import (ldo_token_address, lido_dao_voting_address,
                          lido_dao_token_manager_address,
                          lido_dao_node_operators_registry,
                          lido_dao_deposit_security_module_address,
                          lido_dao_steth_address)

from utils.tx_review import tx_call_trace_filtered

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


class Helpers:
    @property
    def tx(self):
        return self._tx

    def execute_vote(self, accounts, vote_id, dao_voting):
        ldo_holders = [
            '0x3e40d73eb977dc6a537af587d48316fee66e9c8c',
            '0xb8d83908aab38a159f3da47a59d84db8e1838712',
            '0xa2dfc431297aee387c05beef507e5335e684fbcd'
        ]

        for holder_addr in ldo_holders:
            print('voting from acct:', holder_addr)
            accounts[0].transfer(holder_addr, '0.1 ether')
            account = accounts.at(holder_addr, force=True)
            dao_voting.vote(vote_id, True, False, {'from': account})

        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert dao_voting.canExecute(vote_id)
        self._tx = dao_voting.executeVote(vote_id, {'from': accounts[0]})

        print(f'vote executed')

    def print_tx_call_trace(self):
        tx_call_trace_filtered(self._tx,
            lambda trace_item: any(s in trace_item['fn'] for s in
                ['KernelProxy.',
                'Voting._executeVote',
                'EVMScriptRunner.getEVMScriptExecutor',
                'Initializable.',
                'TimeHelpers.',
                'AppStorage.',
                'ScriptHelpers.']))

    def print_tx_events(self):
        self._tx.info()

@pytest.fixture(scope='module')
def helpers():
    return Helpers()