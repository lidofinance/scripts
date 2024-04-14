"""
Tests for voting 23/04/2024

"""

import pytest

from brownie import Contract, web3  # type: ignore
from brownie.network.account import Account
from brownie import accounts, interface, ZERO_ADDRESS
from scripts.vote_2024_04_23 import start_vote
from utils.test.event_validators.vesting_escrow import validate_voting_adapter_upgraded_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import (
    contracts,
    network_name,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    VOTING,

    GATE_SEAL_EXPIRY_TIMESTAMP, 
    GATE_SEAL_PAUSE_DURATION, 
    contracts, 
    GATE_SEAL, 
    GATE_SEAL_COMMITTEE
)
from utils.test.event_validators.aragon import validate_push_to_repo_event, validate_app_update_event
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import Permission

old_trp_voting_adapter_address = "0xCFda8aB0AE5F4Fa33506F9C51650B890E4871Cc1"

updated_trp_voting_adapter_address = "0x5Ea73d6AE9B2E57eF865A3059bdC5C06b8e46072"

@pytest.fixture(scope="module")
def gate_seal_committee(accounts) -> Account:
    return accounts.at(GATE_SEAL_COMMITTEE, force=True)


@pytest.fixture(scope="module")
def contract() -> Contract:
    return interface.GateSeal(GATE_SEAL)


def test_gate_seal(contract: Contract, gate_seal_committee: Account):
    assert contract.get_sealing_committee() == gate_seal_committee

    sealables = contract.get_sealables()
    assert len(sealables) == 2
    assert contracts.validators_exit_bus_oracle.address in sealables
    assert contracts.withdrawal_queue.address in sealables

    _check_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", contract.address)
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", contract.address)

    assert contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert contract.get_expiry_timestamp() == GATE_SEAL_EXPIRY_TIMESTAMP
    assert not contract.is_expired()


def _check_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"

def _check_no_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    #assert not contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert not contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"


old_voting_app = {
    "address": "0x72fb5253AD16307B9E773d2A78CaC58E309d5Ba4",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (3, 0, 0),
}

updated_voting_app = {
    "address": "0x63C7F17210f6a7061e887D05BBF5412085e9DF43",
    "content_uri": "0x697066733a516d506f7478377a484743674265394445684d6f4238336572564a75764d74335971436e6454657a575652706441",
    "id": "0x0abcd104777321a82b010357f20887d61247493d89d2e987ff57bcecbde00e1e",
    "version": (4, 0, 0),
}

deployer_address = "0x64C0fF5C25925aCB33D68F79AD728Fd63361ffce"

old_gate_seal = "0x1ad5cb2955940f998081c1ef5f5f00875431aa90"
new_gate_seal = "0x79243345eDbe01A7E42EDfF5900156700d22611c"


def test_vote(helpers, vote_ids_from_env, bypass_events_decoding):

    # Voting App before
    voting_proxy = interface.AppProxyUpgradeable(contracts.voting.address)
    voting_app_from_repo = contracts.voting_app_repo.getLatest()
    voting_appId = voting_proxy.appId()

    assert voting_app_from_repo[0] == old_voting_app["version"]
    assert voting_app_from_repo[1] == old_voting_app["address"]
    assert voting_proxy.implementation() == old_voting_app["address"]

    # TRP Voting Adapter before
    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    assert trp_voting_adapter_address == old_trp_voting_adapter_address

    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)
    assert trp_voting_adapter.delegation_contract_addr() == ZERO_ADDRESS
    assert trp_voting_adapter.voting_contract_addr() == VOTING

    #old GateSeal permissions before
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", old_gate_seal)
    _check_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", old_gate_seal)
    #new GateSeal permissions before
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", new_gate_seal)
    _check_no_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", new_gate_seal)

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": "0x109b9744397acf987a1abb5bb4eef7362ab9ff66"} #LDO_HOLDER_ADDRESS_FOR_TESTS
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    # Voting App after
    voting_app_from_repo = contracts.voting_app_repo.getLatest()

    assert voting_app_from_repo[0] == updated_voting_app["version"]
    assert voting_app_from_repo[1] == updated_voting_app["address"]
    assert voting_proxy.implementation() == updated_voting_app["address"]

    # TRP Voting Adapter after
    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    assert trp_voting_adapter_address == updated_trp_voting_adapter_address

    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)
    assert trp_voting_adapter.delegation_contract_addr() == VOTING
    assert trp_voting_adapter.voting_contract_addr() == VOTING


    #old GateSeal permissions after
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", old_gate_seal)
    _check_no_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", old_gate_seal)
    #new GateSeal permissions after
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", new_gate_seal)
    _check_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", new_gate_seal)

    # Validating events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 7, "Incorrect voting items count"

    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "" TODO: add ipfs cid
    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    validate_push_to_repo_event(evs[0], updated_voting_app["version"])
    validate_app_update_event(evs[1], voting_appId, updated_voting_app["address"])
    validate_voting_adapter_upgraded_event(evs[2], updated_trp_voting_adapter_address)
