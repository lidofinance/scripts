"""
Tests for voting 23/04/2024

"""

from brownie import Contract, web3, chain  # type: ignore
from brownie import reverts, accounts, interface
from scripts.vote_2024_04_23 import start_vote
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import (
    contracts,
    network_name,

    GATE_SEAL_PAUSE_DURATION, 
    GATE_SEAL_COMMITTEE,
)
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event
)

PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d" # web3.keccak(text="PAUSE_ROLE")
old_gate_seal = "0x1ad5cb2955940f998081c1ef5f5f00875431aa90"
new_gate_seal = "0x79243345eDbe01A7E42EDfF5900156700d22611c"

def _check_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"

def _check_no_role(contract: Contract, role: str, holder: str):
    role_bytes = web3.keccak(text=role).hex()
    assert contract.getRoleMemberCount(role_bytes) == 1, f"Role {role} on {contract} should have exactly one holder"
    assert not contract.getRoleMember(role_bytes, 0) == holder, f"Role {role} holder on {contract} should be {holder}"

def test_vote(helpers, vote_ids_from_env, bypass_events_decoding, accounts):

    #parameter
    agent = contracts.agent

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

    new_gate_seal_contract.seal(sealables, {"from": GATE_SEAL_COMMITTEE})
    print("Sealed")

    expiry_timestamp = chain.time()
    assert new_gate_seal_contract.is_expired()
    assert expiry_timestamp - new_gate_seal_contract.get_expiry_timestamp() <= 2
    print("Expired")

    for sealable in sealables:
        assert interface.IPausable(sealable).isPaused()
    print("Sealables paused")

    chain.sleep(6 * 60 * 60 * 24+100)
    chain.mine()

    for sealable in sealables:
        assert not interface.IPausable(sealable).isPaused()
    print(f"Sealables unpaused in {new_gate_seal_contract.get_seal_duration_seconds()}")

    #Try to use the Old gate seal to pause the contracts
    print("Try to use the Old gate seal to pause the contracts")
    with reverts("10"): # converted into string list of sealed indexes (in sealables) in which the error occurred, in the descending order
        contracts.gate_seal.seal(sealables, {"from": GATE_SEAL_COMMITTEE})

    print("GateSeal is good to go!")

    # Validating events
    assert count_vote_items_by_events(vote_tx, contracts.voting) == 4, "Incorrect voting items count"
    
    metadata = find_metadata_by_vote_id(vote_id)
    #assert get_lido_vote_cid_from_str(metadata) == "" TODO: add ipfs cid
    
    display_voting_events(vote_tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(vote_tx)

    # Grant PAUSE_ROLE on WithdrawalQueue for the new GateSeal
    validate_grant_role_event(evs[0], PAUSE_ROLE, new_gate_seal, agent)

    # Grant PAUSE_ROLE on ValidatorExitBusOracle for the new GateSeal
    validate_grant_role_event(evs[1], PAUSE_ROLE, new_gate_seal, agent)

    # Revoke PAUSE_ROLE on WithdrawalQueue from the old GateSeal
    validate_revoke_role_event(evs[2], PAUSE_ROLE, old_gate_seal, agent)

    # Revoke PAUSE_ROLE on ValidatorExitBusOracle from the old GateSeal
    validate_revoke_role_event(evs[3], PAUSE_ROLE, old_gate_seal, agent)