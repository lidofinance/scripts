from typing import Optional
from scripts.vote_tw_upgrade_verifier_hoodi import start_vote, OLD_VALIDATOR_EXIT_VERIFIER, LIDO_LOCATOR_IMPL
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


def validate_proxy_upgrade_event(event: EventDict, expected_implementation: str, emitted_by: Optional[str] = None):
    """Validates Upgraded event from OssifiableProxy"""
    assert "Upgraded" in event, "No Upgraded event found"
    assert event["Upgraded"][0]["implementation"] == convert.to_address(expected_implementation), f"Wrong implementation. Expected: {expected_implementation}, Got: {event['Upgraded'][0]['implementation']}"

    if emitted_by is not None:
        assert convert.to_address(event["Upgraded"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def test_vote_tw_upgrade_verifier_hoodi(helpers, accounts, vote_ids_from_env, stranger):
    """Test the TW upgrade validator exit verifier vote that upgrades locator and manages validator roles"""

    # Calculate role hash
    REPORT_VALIDATOR_EXITING_STATUS_ROLE = web3.keccak(text="REPORT_VALIDATOR_EXITING_STATUS_ROLE")

    # Get contracts
    staking_router = interface.StakingRouter(contracts.staking_router)
    lido_locator_proxy = interface.OssifiableProxy(contracts.lido_locator)
    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    # Check initial state
    initial_implementation = lido_locator_proxy.proxy__getImplementation()
    
    # Check role states before vote
    old_verifier_has_role_before = staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, OLD_VALIDATOR_EXIT_VERIFIER)
    new_verifier_has_role_before = staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, contracts.validator_exit_verifier)

    print(f"Initial Lido Locator implementation: {initial_implementation}")
    print(f"Old validator exit verifier ({OLD_VALIDATOR_EXIT_VERIFIER}) has role before vote: {old_verifier_has_role_before}")
    print(f"New validator exit verifier ({contracts.validator_exit_verifier}) has role before vote: {new_verifier_has_role_before}")

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

    # 1. Verify Lido Locator was upgraded
    final_implementation = lido_locator_proxy.proxy__getImplementation()
    assert final_implementation == LIDO_LOCATOR_IMPL, f"Locator implementation not upgraded. Expected: {LIDO_LOCATOR_IMPL}, Got: {final_implementation}"
    assert final_implementation != initial_implementation, "Implementation should have changed"

    # 2. Verify validator roles were updated
    new_verifier_has_role_after = staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, contracts.validator_exit_verifier)
    old_verifier_has_role_after = staking_router.hasRole(REPORT_VALIDATOR_EXITING_STATUS_ROLE, OLD_VALIDATOR_EXIT_VERIFIER)
    
    assert new_verifier_has_role_after, f"New verifier ({contracts.validator_exit_verifier}) should have role after vote"
    assert not old_verifier_has_role_after, f"Old verifier ({OLD_VALIDATOR_EXIT_VERIFIER}) should not have role after vote"

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
    expected_events = 3  # 1 proxy upgrade + 1 role grant + 1 role revoke
    assert len(dg_execution_events) == expected_events, f"Expected {expected_events} dual governance events, got {len(dg_execution_events)}"

    event_idx = 0

    # Step 1: Upgrade Lido Locator implementation
    validate_proxy_upgrade_event(
        dg_execution_events[event_idx],
        expected_implementation=LIDO_LOCATOR_IMPL,
        emitted_by=contracts.lido_locator
    )
    event_idx += 1

    # Step 2: Grant REPORT_VALIDATOR_EXITING_STATUS_ROLE to new validator exit verifier
    validate_role_grant_event(
        dg_execution_events[event_idx],
        role_hash=REPORT_VALIDATOR_EXITING_STATUS_ROLE.hex(),
        account=contracts.validator_exit_verifier,
        emitted_by=contracts.staking_router
    )
    event_idx += 1

    # Step 3: Revoke REPORT_VALIDATOR_EXITING_STATUS_ROLE from old validator exit verifier
    validate_role_revoke_event(
        dg_execution_events[event_idx],
        role_hash=REPORT_VALIDATOR_EXITING_STATUS_ROLE.hex(),
        account=OLD_VALIDATOR_EXIT_VERIFIER,
        emitted_by=contracts.staking_router
    )

    print("✅ Vote executed successfully:")
    print(f"  - Lido Locator upgraded from {initial_implementation} to {LIDO_LOCATOR_IMPL}")
    print(f"  - REPORT_VALIDATOR_EXITING_STATUS_ROLE granted to new verifier: {contracts.validator_exit_verifier}")
    print(f"  - REPORT_VALIDATOR_EXITING_STATUS_ROLE revoked from old verifier: {OLD_VALIDATOR_EXIT_VERIFIER}")
    print(f"  - All {expected_events} events validated correctly")
