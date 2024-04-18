"""
Tests for voting 23/04/2024

"""

from brownie import Contract, web3, chain  # type: ignore
from brownie import accounts, interface, ZERO_ADDRESS
from scripts.vote_2024_04_23 import start_vote
from utils.config import (
    contracts,
    network_name,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    VOTING,

    GATE_SEAL_PAUSE_DURATION, 
    contracts, 
    GATE_SEAL_COMMITTEE
)
from utils.test.tx_tracing_helpers import *

def _check_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"

def _check_no_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert not contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"

old_gate_seal = "0x1ad5cb2955940f998081c1ef5f5f00875431aa90"
new_gate_seal = "0x79243345eDbe01A7E42EDfF5900156700d22611c"


def test_vote(helpers, vote_ids_from_env, bypass_events_decoding, accounts):

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

    #old GateSeal permissions after
    _check_no_role(contracts.withdrawal_queue, "PAUSE_ROLE", old_gate_seal)
    _check_no_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", old_gate_seal)
    #new GateSeal permissions after
    _check_role(contracts.withdrawal_queue, "PAUSE_ROLE", new_gate_seal)
    _check_role(contracts.validators_exit_bus_oracle, "PAUSE_ROLE", new_gate_seal)

    #Асceptance test
    new_gate_seal_contract = interface.GateSeal(new_gate_seal)
    assert new_gate_seal_contract.get_sealing_committee() == GATE_SEAL_COMMITTEE
    sealables = new_gate_seal_contract.get_sealables()
    assert len(sealables) == 2
    assert contracts.validators_exit_bus_oracle.address in sealables
    assert contracts.withdrawal_queue.address in sealables

    assert new_gate_seal_contract.get_seal_duration_seconds() == GATE_SEAL_PAUSE_DURATION
    assert new_gate_seal_contract.get_expiry_timestamp() == 1743465600
    assert not new_gate_seal_contract.is_expired()
    
    #Scenario test
    print(f"Simulating GateSeal flow")

    sealing_committee = new_gate_seal_contract.get_sealing_committee()
    new_gate_seal_contract.seal(sealables, {"from": sealing_committee})
    print("Sealed")

    expiry_timestamp = chain.time()
    assert new_gate_seal_contract.is_expired()
    assert new_gate_seal_contract.get_expiry_timestamp() == expiry_timestamp
    print("Expired")

    for sealable in sealables:
        assert interface.SealableMock(sealable).isPaused()
    print("Sealables paused")

    chain.sleep(expiry_timestamp + new_gate_seal_contract.get_seal_duration_seconds())

    for sealable in sealables:
        assert interface.SealableMock(sealable).isPaused()
    print(f"Sealables unpaused in {new_gate_seal_contract.get_seal_duration_seconds()}")

    print("GateSeal is good to go!")

    # Validating events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 4, "Incorrect voting items count"

    # metadata = find_metadata_by_vote_id(vote_id)
    # assert get_lido_vote_cid_from_str(metadata) == "" TODO: add ipfs cid
    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)