import json
from typing import List

import brownie.exceptions
import pytest

from brownie import chain, interface, web3, network
from brownie.network import state
from brownie.network.contract import Contract

from utils.evm_script import EMPTY_CALLSCRIPT

from utils.config import contracts, network_name, get_vote_duration

from utils.config import *
from utils.txs.deploy import deploy_from_prepared_tx
from utils.test.helpers import ETH
from utils.balance import set_balance, set_balance_in_wei
from functools import wraps

ENV_OMNIBUS_BYPASS_EVENTS_DECODING = "OMNIBUS_BYPASS_EVENTS_DECODING"
ENV_PARSE_EVENTS_FROM_LOCAL_ABI = "PARSE_EVENTS_FROM_LOCAL_ABI"
ENV_OMNIBUS_VOTE_IDS = "OMNIBUS_VOTE_IDS"
ENV_DG_PROPOSAL_IDS = "DG_PROPOSAL_IDS"


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="session", autouse=True)
def network_gas_price():
    network.gas_price("2 gwei")


@pytest.fixture(scope="function")
def deployer():
    return accounts[0]


@pytest.fixture()
def steth_holder(accounts):
    steth_holder = accounts.at("0x176F3DAb24a159341c0509bB36B833E7fdd0a131", force=True)
    set_balance(steth_holder.address, 100000)
    steth_holder.transfer(contracts.lido, ETH(10000))
    return steth_holder


@pytest.fixture(scope="module")
def ldo_holder(accounts):
    return accounts.at(LDO_HOLDER_ADDRESS_FOR_TESTS, force=True)


@pytest.fixture(scope="session")
def stranger():
    return set_balance("0x98eC059dC3aDFbdd63429454aeB0C990fbA4a124", 100000)


@pytest.fixture(scope="function")
def delegate1():
    return set_balance("0xa70B0AfdF44cEccCF02E76486a6DE4F4B7fd1e52", 100000)


@pytest.fixture(scope="function")
def delegate2():
    return set_balance("0x100b896F2Dd8c4Ca619db86BCDDb7E085143C1C5", 100000)


@pytest.fixture(scope="module")
def trp_recipient(accounts):
    return set_balance("0x228cCaFeA1fa21B74257Af975A9D84d87188c61B", 100000)


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
    def execute_vote(accounts, vote_id, dao_voting, topup="10 ether"):
        (tx,) = Helpers.execute_votes(accounts, [vote_id], dao_voting, topup)
        return tx

    @staticmethod
    def execute_votes(accounts, vote_ids, dao_voting, topup="10 ether"):
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
        # time_to_end = dao_voting.getVote(vote_id)["startDate"] + get_vote_duration() - chain.time()
        chain.sleep(get_vote_duration())
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

        Helpers.prefetch_contracts_from_etherscan()

        return execution_transactions

    @staticmethod
    def is_executed(vote_id, dao_voting):
        vote_status = dao_voting.getVote(vote_id)
        return vote_status[1]

    @staticmethod
    def prefetch_contracts_from_etherscan():
        if not Helpers._etherscan_is_fetched:
            print(f"prefetch contracts from Etherscan to parse events")
            # In case of issue with events parsing from local abi
            # add contracts here to fetch the abis from etherscan
            # Use next format to fetch the abi:
            # Contract.from_explorer(<contract_address>)
            Contract.from_explorer(contracts.cs_exit_penalties.address)

            Helpers._etherscan_is_fetched = True


@pytest.fixture(scope="session")
def helpers():
    return Helpers


@pytest.fixture(scope="session")
def vote_ids_from_env() -> [int]:
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
def dg_proposal_ids_from_env() -> [int]:
    return get_active_proposals_from_env()


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
    print("os.getenv(ENV_PARSE_EVENTS_FROM_LOCAL_ABI):", os.getenv(ENV_PARSE_EVENTS_FROM_LOCAL_ABI))

    if os.getenv(ENV_OMNIBUS_BYPASS_EVENTS_DECODING):
        return

    if not os.getenv(ENV_PARSE_EVENTS_FROM_LOCAL_ABI):
        return

    print("parse_events_from_local_abi...")

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
        "VaultHub": [VAULT_HUB_IMPL],
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


@pytest.fixture(scope="session", autouse=True)
def add_balance_check_middleware():
    web3.middleware_onion.add(balance_check_middleware, name="balance_check")


# TODO: Such implicit manipulation of the balances may lead to hard-debugging errors in the future.
def ensure_balance(address) -> int:
    old_balance = web3.eth.get_balance(address)
    if old_balance < ETH(999):
        set_balance_in_wei(address, ETH(1000000))
    return web3.eth.get_balance(address) - old_balance


def balance_check_middleware(make_request, web3):
    @wraps(make_request)
    def middleware(method, params):
        from_address = None
        result = None
        balance_diff = 0

        if method in ["eth_sendTransaction", "eth_sendRawTransaction"]:
            transaction = params[0]
            from_address = transaction.get("from")
            if from_address:
                balance_diff = ensure_balance(from_address)

        try:
            result = make_request(method, params)
        finally:
            if balance_diff > 0:
                new_balance = max(0, web3.eth.get_balance(from_address) - balance_diff)
                set_balance_in_wei(from_address, new_balance)

        return result

    return middleware


def get_active_proposals_from_env() -> [int]:
    if os.getenv(ENV_DG_PROPOSAL_IDS):
        try:
            proposal_ids_str = os.getenv(ENV_DG_PROPOSAL_IDS)
            proposal_ids = [int(s) for s in proposal_ids_str.split(",")]
            print(f"DG_PROPOSAL_IDS env var is set, skipping the vote, using existing proposals {proposal_ids}")
            return proposal_ids
        except:
            raise Exception("DG_PROPOSAL_IDS env var is set, but it is invalid. Valid format: DG_PROPOSAL_IDS=1,2,3")

    return []
