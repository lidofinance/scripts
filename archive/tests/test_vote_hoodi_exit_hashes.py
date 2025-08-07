from typing import Optional
from scripts.vote_hoodi_exit_hashes import start_vote, EXIT_HASH_TO_SUBMIT
from brownie import interface, chain, convert, web3  # type: ignore
from brownie.network.event import EventDict
from utils.test.tx_tracing_helpers import group_voting_events_from_receipt, group_dg_events_from_receipt
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.dual_governance import wait_for_noon_utc_to_satisfy_time_constrains
from utils.config import (
    DUAL_GOVERNANCE,
    TIMELOCK,
    DUAL_GOVERNANCE_EXECUTORS,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    AGENT,
    VOTING,
    contracts,
)


def validate_role_grant_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    """Validates an OpenZeppelin AccessControl role grant event"""
    assert "RoleGranted" in event, "No RoleGranted event found"
    assert event["RoleGranted"][0]["role"] == role_hash, f"Wrong role hash. Expected: {role_hash}, Got: {event['RoleGranted'][0]['role']}"
    assert event["RoleGranted"][0]["account"] == convert.to_address(account), f"Wrong account. Expected: {account}, Got: {event['RoleGranted'][0]['account']}"
    
    if emitted_by is not None:
        assert convert.to_address(event["RoleGranted"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_revoke_event(event: EventDict, role_hash: str, account: str, emitted_by: Optional[str] = None):
    """Validates an OpenZeppelin AccessControl role revoke event"""
    assert "RoleRevoked" in event, "No RoleRevoked event found"
    assert event["RoleRevoked"][0]["role"] == role_hash, f"Wrong role hash. Expected: {role_hash}, Got: {event['RoleRevoked'][0]['role']}"
    assert event["RoleRevoked"][0]["account"] == convert.to_address(account), f"Wrong account. Expected: {account}, Got: {event['RoleRevoked'][0]['account']}"
    
    if emitted_by is not None:
        assert convert.to_address(event["RoleRevoked"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_submit_exit_requests_hash_event(event: EventDict, expected_hash: str, emitted_by: Optional[str] = None):
    """Validates RequestsHashSubmitted event from ValidatorsExitBus"""
    assert "RequestsHashSubmitted" in event, "No RequestsHashSubmitted event found"
    assert event["RequestsHashSubmitted"][0]["exitRequestsHash"] == expected_hash, f"Wrong hash. Expected: {expected_hash}, Got: {event['RequestsHashSubmitted'][0]['exitRequestsHash']}"
    
    if emitted_by is not None:
        assert convert.to_address(event["RequestsHashSubmitted"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def test_vote_hoodi_exit_hashes(helpers, accounts, vote_ids_from_env, stranger):
    """Test the vote that grants SUBMIT_REPORT_HASH_ROLE temporarily to agent, uses it, then revokes it"""
    
    # Calculate the role hash for SUBMIT_REPORT_HASH_ROLE
    SUBMIT_REPORT_HASH_ROLE = web3.keccak(text="SUBMIT_REPORT_HASH_ROLE")
    
    # Get contracts
    validators_exit_bus = interface.ValidatorsExitBus(contracts.validators_exit_bus_oracle)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    
    # Check initial state - agent should not have the role
    assert not validators_exit_bus.hasRole(SUBMIT_REPORT_HASH_ROLE, AGENT), "Agent should not have SUBMIT_REPORT_HASH_ROLE before vote"
    
    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)
    print(f"voteId = {vote_id}")

    proposal_id = vote_tx.events["ProposalSubmitted"][1]["proposalId"]
    print(f"proposalId = {proposal_id}")

    chain.sleep(timelock.getAfterSubmitDelay() + 1)
    dual_governance.scheduleProposal(proposal_id, {"from": stranger})

    chain.sleep(timelock.getAfterScheduleDelay() + 1)
    wait_for_noon_utc_to_satisfy_time_constrains()

    dg_tx = timelock.execute(proposal_id, {"from": stranger})

    # --- VALIDATE EXECUTION RESULTS ---

    # 1. Verify SUBMIT_REPORT_HASH_ROLE was granted and then revoked (final state is revoked)
    assert not validators_exit_bus.hasRole(SUBMIT_REPORT_HASH_ROLE, AGENT), "Agent should not have SUBMIT_REPORT_HASH_ROLE after vote"

    # --- VALIDATE EVENTS ---
    voting_events = group_voting_events_from_receipt(vote_tx)
    assert len(voting_events) >= 1, "No voting events found"

    validate_dual_governance_submit_event(
        voting_events[0],
        proposal_id,
        proposer=VOTING,
        executor=DUAL_GOVERNANCE_EXECUTORS[0],
    )

    dg_execution_events = group_dg_events_from_receipt(dg_tx, timelock=TIMELOCK, admin_executor=DUAL_GOVERNANCE_EXECUTORS[0])
    assert len(dg_execution_events) == 3, f"Expected 3 dual governance events, got {len(dg_execution_events)}"

    # 0. Grant SUBMIT_REPORT_HASH_ROLE to agent
    validate_role_grant_event(
        dg_execution_events[0],
        role_hash=SUBMIT_REPORT_HASH_ROLE.hex(),
        account=AGENT,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 1. Submit exit requests hash
    validate_submit_exit_requests_hash_event(
        dg_execution_events[1],
        expected_hash=EXIT_HASH_TO_SUBMIT,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    # 2. Revoke SUBMIT_REPORT_HASH_ROLE from agent
    validate_role_revoke_event(
        dg_execution_events[2],
        role_hash=SUBMIT_REPORT_HASH_ROLE.hex(),
        account=AGENT,
        emitted_by=contracts.validators_exit_bus_oracle
    )

    print("✅ Vote executed successfully:")
    print(f"  - SUBMIT_REPORT_HASH_ROLE granted and revoked to/from agent")
    print(f"  - Exit hash {EXIT_HASH_TO_SUBMIT} submitted")
    print(f"  - All events validated correctly")