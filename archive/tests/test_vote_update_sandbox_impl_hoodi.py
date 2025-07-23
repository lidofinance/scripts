from typing import Optional
from scripts.vote_update_sandbox_impl_hoodi import start_vote
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
    ARAGON_KERNEL,
    AGENT,
    VOTING,
    contracts,
)

# Implementation address from vote script
NODE_OPERATORS_REGISTRY_IMPL = "0x95F00b016bB31b7182D96D25074684518246E42a"
NOR_EXIT_DEADLINE_IN_SEC = 172800
SANDBOX_APP_ID = "0x85d2fceef13a6c14c43527594f79fb91a8ef8f15024a43486efac8df2b11e632"

def validate_role_grant_event(event: EventDict, role_name: str, account: str, emitted_by: Optional[str] = None):
    """Validates a permission grant event from ACL"""
    assert "SetPermission" in event, "No SetPermission event found"
    assert event["SetPermission"][0]["allowed"] is True, "Permission was not granted"
    assert event["SetPermission"][0]["entity"] == convert.to_address(account), "Wrong account"

    role_hash = convert.to_uint(web3.keccak(text=role_name))
    assert convert.to_uint(event["SetPermission"][0]["role"]) == role_hash, "Wrong role hash"

    if emitted_by is not None:
        assert convert.to_address(event["SetPermission"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_role_revoke_event(event: EventDict, role_name: str, account: str, emitted_by: Optional[str] = None):
    """Validates a permission revoke event from ACL"""
    assert "SetPermission" in event, "No SetPermission event found"
    assert event["SetPermission"][0]["allowed"] is False, "Permission was not revoked"
    assert event["SetPermission"][0]["entity"] == convert.to_address(account), "Wrong account"

    role_hash = convert.to_uint(web3.keccak(text=role_name))
    assert convert.to_uint(event["SetPermission"][0]["role"]) == role_hash, "Wrong role hash"

    if emitted_by is not None:
        assert convert.to_address(event["SetPermission"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_app_set_event(event: EventDict, app_id: str, app_addr: str, emitted_by: Optional[str] = None):
    """Validates SetApp event from Kernel"""
    assert "SetApp" in event, "No SetApp event found"

    # Convert event appId to hex string for comparison
    actual_app_id = event["SetApp"][0]["appId"]
    if isinstance(actual_app_id, bytes):
        actual_app_id_hex = "0x" + actual_app_id.hex()
    else:
        actual_app_id_hex = str(actual_app_id)
    
    expected_app_id = app_id.lower()
    assert actual_app_id_hex.lower() == expected_app_id, f"Wrong app ID: expected {expected_app_id}, got {actual_app_id_hex.lower()}"
    assert convert.to_address(event["SetApp"][0]["app"]) == convert.to_address(app_addr), "Wrong app address"

    if emitted_by is not None:
        assert convert.to_address(event["SetApp"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_contract_version_set_event(event: EventDict, version: int, emitted_by: Optional[str] = None):
    assert "ContractVersionSet" in event, "No ContractVersionSet event found"
    assert event["ContractVersionSet"][0]["version"] == version, "Wrong version"
    if emitted_by is not None:
        assert convert.to_address(event["ContractVersionSet"][0]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def test_vote_update_sandbox_impl(helpers, accounts, vote_ids_from_env, stranger):
    # Save original state for comparison
    app_manager_role = web3.keccak(text="APP_MANAGER_ROLE")

    # Check initial state
    assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE before upgrade"

    # Get sandbox contract
    sandbox = interface.NodeOperatorsRegistry(contracts.sandbox)

    # Check initial sandbox version
    assert sandbox.getContractVersion() < 4, "Sandbox module version should be less than 4 before upgrade"

    # Get current implementation
    base_namespace = contracts.kernel.APP_BASES_NAMESPACE()
    sandbox_impl_before = contracts.kernel.getApp(base_namespace, SANDBOX_APP_ID)
    assert sandbox_impl_before.lower() != NODE_OPERATORS_REGISTRY_IMPL.lower(), "Sandbox implementation should be different before upgrade"

    timelock = interface.EmergencyProtectedTimelock(TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

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

    # 1. Verify APP_MANAGER_ROLE was granted and then revoked (final state is revoked)
    assert not contracts.acl.hasPermission(AGENT, ARAGON_KERNEL, app_manager_role), "AGENT should not have APP_MANAGER_ROLE after upgrade"

    # 2. Verify Sandbox implementation was updated
    sandbox_impl_after = contracts.kernel.getApp(base_namespace, SANDBOX_APP_ID)
    assert sandbox_impl_after.lower() == NODE_OPERATORS_REGISTRY_IMPL.lower(), "Sandbox implementation should be updated"

    # 3. Verify finalizeUpgrade_v4 was called
    assert sandbox.getContractVersion() == 4, "Sandbox module version should be 4 after upgrade"
    assert sandbox.exitDeadlineThreshold(0) == NOR_EXIT_DEADLINE_IN_SEC, "Sandbox exit deadline threshold should be set correctly"

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
    assert len(dg_execution_events) == 4, "Unexpected number of dual governance events"

    # 0. Grant APP_MANAGER_ROLE to AGENT
    validate_role_grant_event(
        dg_execution_events[0],
        "APP_MANAGER_ROLE",
        AGENT,
        emitted_by=contracts.acl
    )

    # 1. Update Sandbox Module implementation
    validate_app_set_event(
        dg_execution_events[1],
        SANDBOX_APP_ID,
        NODE_OPERATORS_REGISTRY_IMPL,
        emitted_by=contracts.kernel
    )

    # 2. Call finalizeUpgrade_v4 on Sandbox Module
    validate_contract_version_set_event(
        dg_execution_events[2],
        version=4,
        emitted_by=contracts.sandbox
    )

    # Check that ExitDeadlineThresholdChanged event was emitted
    assert 'ExitDeadlineThresholdChanged' in dg_execution_events[2], "ExitDeadlineThresholdChanged event not found"
    assert dg_execution_events[2]['ExitDeadlineThresholdChanged'][0]['threshold'] == NOR_EXIT_DEADLINE_IN_SEC, "Wrong exit deadline threshold"

    # 3. Revoke APP_MANAGER_ROLE from AGENT
    validate_role_revoke_event(
        dg_execution_events[3],
        "APP_MANAGER_ROLE",
        AGENT,
        emitted_by=contracts.acl
    )

