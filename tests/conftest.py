import os
import json
from typing import List

import brownie.exceptions
import pytest

from brownie import chain, interface, web3
from brownie.network import state
from brownie.network.contract import Contract

from utils.balance import set_balance
from utils.evm_script import EMPTY_CALLSCRIPT

from utils.config import contracts, network_name, MAINNET_VOTE_DURATION

from utils.config import *
from utils.txs.deploy import deploy_from_prepared_tx
from utils.test.helpers import ETH

ENV_OMNIBUS_BYPASS_EVENTS_DECODING = "OMNIBUS_BYPASS_EVENTS_DECODING"
ENV_PARSE_EVENTS_FROM_LOCAL_ABI = "PARSE_EVENTS_FROM_LOCAL_ABI"
ENV_OMNIBUS_VOTE_IDS = "OMNIBUS_VOTE_IDS"


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="function")
def deployer():
    return accounts[0]


@pytest.fixture()
def steth_holder(accounts):
    steth_holder = accounts.at("0x176F3DAb24a159341c0509bB36B833E7fdd0a131", force=True)
    web3.provider.make_request("evm_setAccountBalance", [steth_holder.address, "0x152D02C7E14AF6800000"])
    steth_holder.transfer(contracts.lido, ETH(10000))
    return steth_holder


@pytest.fixture(scope="module")
def ldo_holder(accounts):
    return accounts.at(LDO_HOLDER_ADDRESS_FOR_TESTS, force=True)


@pytest.fixture(scope="function")
def stranger():
    return set_balance("0x98eC059dC3aDFbdd63429454aeB0C990fbA4a124", 100000)


@pytest.fixture(scope="module")
def eth_whale(accounts):
    if network_name() in ("goerli", "goerli-fork"):
        return accounts.at("0xC48E23C5F6e1eA0BaEf6530734edC3968f79Af2e", force=True)
    else:
        return accounts.at("0x00000000219ab540356cBB839Cbe05303d7705Fa", force=True)


@pytest.fixture(scope="module")
def steth_whale(accounts) -> Account:
    # TODO: add steth whale for goerli
    return accounts.at(WSTETH_TOKEN, force=True)


class Helpers:
    _etherscan_is_fetched: bool = False

    @staticmethod
    def filter_events_from(addr, events):
        return list(filter(lambda evt: evt.address == addr, events))

    @staticmethod
    def assert_single_event_named(evt_name, tx, evt_keys_dict):
        receiver_events = Helpers.filter_events_from(tx.receiver, tx.events[evt_name])
        assert len(receiver_events) == 1
        assert dict(receiver_events[0]) == evt_keys_dict

    @staticmethod
    def assert_event_not_emitted(evt_name, tx):
        try:
            _ = tx.events[evt_name]
        except brownie.exceptions.EventLookupError:
            pass
        else:
            raise AssertionError(f"Event {evt_name} was fired")

    @staticmethod
    def execute_vote(accounts, vote_id, dao_voting, topup="0.1 ether", skip_time=MAINNET_VOTE_DURATION):
        (tx,) = Helpers.execute_votes(accounts, [vote_id], dao_voting, topup, skip_time)
        return tx

    @staticmethod
    def execute_votes(accounts, vote_ids, dao_voting, topup="0.1 ether", skip_time=MAINNET_VOTE_DURATION):
        OBJECTION_PHASE_ID = 1
        for vote_id in vote_ids:
            print(f"Vote #{vote_id}")
            if dao_voting.canVote(vote_id, LDO_VOTE_EXECUTORS_FOR_TESTS[0]) and (
                dao_voting.getVotePhase(vote_id) != OBJECTION_PHASE_ID
            ):
                for holder_addr in LDO_VOTE_EXECUTORS_FOR_TESTS:
                    print("voting from acct:", holder_addr)
                    if accounts.at(holder_addr, force=True).balance() < topup:
                        accounts[0].transfer(holder_addr, topup)
                    account = accounts.at(holder_addr, force=True)
                    dao_voting.vote(vote_id, True, False, {"from": account})

        # wait for the vote to end
        chain.sleep(skip_time)
        chain.mine()

        for vote_id in vote_ids:
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

        execution_transactions = []
        for vote_id in vote_ids:
            tx = dao_voting.executeVote(vote_id, {"from": accounts[0]})
            print(f"vote #{vote_id} executed")
            execution_transactions.append(tx)

        # Helpers._prefetch_contracts_from_etherscan()

        return execution_transactions

    @staticmethod
    def is_executed(vote_id, dao_voting):
        vote_status = dao_voting.getVote(vote_id)
        return vote_status[1]

    @staticmethod
    def _prefetch_contracts_from_etherscan():
        if not Helpers._etherscan_is_fetched:
            print(f"prefetch Lido V2 contracts from Etherscan to parse events")

            Contract.from_explorer(VALIDATORS_EXIT_BUS_ORACLE)
            Contract.from_explorer(WITHDRAWAL_QUEUE)
            Contract.from_explorer(STAKING_ROUTER)

            Helpers._etherscan_is_fetched = True


@pytest.fixture(scope="session")
def helpers():
    return Helpers


@pytest.fixture(scope="session")
def vote_ids_from_env() -> List[int]:
    if os.getenv(ENV_OMNIBUS_VOTE_IDS):
        try:
            vote_ids_str = os.getenv(ENV_OMNIBUS_VOTE_IDS)
            vote_ids = [int(s) for s in vote_ids_str.split(",")]
            print(f"OMNIBUS_VOTE_IDS env var is set, using existing votes {vote_ids}")
            return vote_ids
        except:
            pass

    return []


@pytest.fixture(scope="module")
def bypass_events_decoding() -> bool:
    if os.getenv(ENV_OMNIBUS_BYPASS_EVENTS_DECODING):
        print(f"Warning: {ENV_OMNIBUS_BYPASS_EVENTS_DECODING} env var is set, events decoding disabled")
        return True

    return False


@pytest.fixture(scope="module")
def autodeploy_contract(accounts):
    address = deploy_from_prepared_tx(accounts[0], "./utils/txs/tx-deploy-voting_for_upgrade.json")


@pytest.fixture(scope="session", autouse=True)
def parse_events_from_local_abi():
    if os.getenv(ENV_OMNIBUS_BYPASS_EVENTS_DECODING):
        return

    if not os.getenv(ENV_PARSE_EVENTS_FROM_LOCAL_ABI):
        return

    # Used if env variable PARSE_EVENTS_FROM_LOCAL_ABI is set
    # Needed to enable events checking if ABI from Etherscan not available for any reason
    contract_address_mapping = {
        "AccountingOracle": [ACCOUNTING_ORACLE, ACCOUNTING_ORACLE_IMPL],
        "ACL": [ACL_IMPL],
        "Burner": [BURNER],
        "CallsScript": [ARAGON_CALLS_SCRIPT],
        "DepositSecurityModule": [DEPOSIT_SECURITY_MODULE],
        "EIP712StETH": [EIP712_STETH],
        "HashConsensus": [
            HASH_CONSENSUS_FOR_AO,
            HASH_CONSENSUS_FOR_VEBO,
        ],
        "LegacyOracle": [LEGACY_ORACLE, LEGACY_ORACLE_IMPL],
        "Lido": [LIDO, LIDO_IMPL],
        "LidoLocator": [LIDO_LOCATOR],
        "LidoExecutionLayerRewardsVault": [EXECUTION_LAYER_REWARDS_VAULT],
        "Kernel": [ARAGON_KERNEL_IMPL],
        "NodeOperatorsRegistry": [NODE_OPERATORS_REGISTRY, NODE_OPERATORS_REGISTRY_IMPL],
        "SimpleDVT": [SIMPLE_DVT, SIMPLE_DVT_IMPL],
        "OracleDaemonConfig": [ORACLE_DAEMON_CONFIG],
        "OracleReportSanityChecker": [ORACLE_REPORT_SANITY_CHECKER],
        "Repo": [ARAGON_COMMON_REPO_IMPL],
        "StakingRouter": [STAKING_ROUTER, STAKING_ROUTER_IMPL],
        "ValidatorsExitBusOracle": [
            VALIDATORS_EXIT_BUS_ORACLE,
            VALIDATORS_EXIT_BUS_ORACLE_IMPL,
        ],
        "Voting": [VOTING_IMPL],
        "WithdrawalQueueERC721": [WITHDRAWAL_QUEUE, WITHDRAWAL_QUEUE_IMPL],
        "WithdrawalVault": [WITHDRAWAL_VAULT, WITHDRAWAL_VAULT_IMPL],
    }

    interface_path_template = "interfaces/{}.json"
    for contract_name, addresses in contract_address_mapping.items():
        for addr in addresses:
            with open(interface_path_template.format(contract_name)) as fp:
                abi = json.load(fp)
            contract = Contract.from_abi(contract_name, addr, abi)
            # See https://eth-brownie.readthedocs.io/en/stable/api-network.html?highlight=_add_contract#brownie.network.state._add_contract
            # Added contract will resolve from address during state._find_contract without a request to Etherscan
            state._add_contract(contract)
