import pytest
from brownie import ZERO_ADDRESS, accounts, chain, interface, reverts, web3  # type: ignore
from brownie.network.account import Account

from utils.config import (
    AGENT,
    CIRCUIT_BREAKER,
    CIRCUIT_BREAKER_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_PAUSE_DURATION,
    CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MIN_PAUSE_DURATION,
    CIRCUIT_BREAKER_PAUSE_DURATION,
    CS_ACCOUNTING_ADDRESS,
    CS_EJECTOR_ADDRESS,
    CS_FEE_ORACLE_ADDRESS,
    CS_VERIFIER_V2_ADDRESS,
    CS_VETTED_GATE_ADDRESS,
    CSM_ADDRESS,
    CSM_COMMITTEE_MS,
    GATE_SEAL_COMMITTEE,
    PREDEPOSIT_GUARANTEE,
    RESEAL_MANAGER,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    VALIDATORS_EXIT_BUS_ORACLE,
    VAULT_HUB,
    VOTING,
    WITHDRAWAL_QUEUE,
    contracts,
)
from utils.agent import agent_forward
from utils.dual_governance import process_proposals
from utils.evm_script import encode_error


PAUSE_ROLE = web3.keccak(text="PAUSE_ROLE")
PAUSE_INFINITELY = 2**256 - 1


# Test subjects: one pausable per pauser group, picked to be the cheapest to drive.
WQ_PAUSABLE = WITHDRAWAL_QUEUE
CSM_PAUSABLE = CSM_ADDRESS


@pytest.fixture(scope="module")
def circuit_breaker():
    return interface.CircuitBreaker(CIRCUIT_BREAKER)


@pytest.fixture(scope="module")
def agent_account() -> Account:
    return accounts.at(AGENT, force=True)


@pytest.fixture(scope="module")
def voting_account() -> Account:
    return accounts.at(VOTING, force=True)


@pytest.fixture(scope="module")
def reseal_manager_account() -> Account:
    return accounts.at(RESEAL_MANAGER, force=True)


@pytest.fixture(scope="module")
def gate_seal_committee_account() -> Account:
    return accounts.at(GATE_SEAL_COMMITTEE, force=True)


@pytest.fixture(scope="module")
def csm_committee_account() -> Account:
    return accounts.at(CSM_COMMITTEE_MS, force=True)


def _submit_dg_proposal_via_voting(calls, description, voting_acct):
    """Submit a DG proposal directly via the Voting account (impersonated), bypassing the Aragon vote."""
    proposal_calldata = [(addr, 0, data) for addr, data in calls]
    tx = contracts.dual_governance.submitProposal(
        proposal_calldata, description, {"from": voting_acct}
    )
    return tx.events["ProposalSubmitted"][0]["proposalId"]


def _execute_admin_via_dg(circuit_breaker, encoded_call, voting_acct):
    """Wrap an encoded CircuitBreaker call in agent_forward + DG submit + execute."""
    proposal_id = _submit_dg_proposal_via_voting(
        [agent_forward([(circuit_breaker.address, encoded_call)])],
        "test admin call",
        voting_acct,
    )
    process_proposals([proposal_id])
    return proposal_id


# ============================================================================
# Per-pausable pause flow — event order, state transitions, auto-resume
# ============================================================================
def test_pause_flow_emits_events_and_clears_pauser(
    circuit_breaker, gate_seal_committee_account
):
    wq = contracts.withdrawal_queue
    assert not wq.isPaused()
    assert circuit_breaker.getPauser(WQ_PAUSABLE).lower() == GATE_SEAL_COMMITTEE.lower()

    pre_count = circuit_breaker.getPausableCount(GATE_SEAL_COMMITTEE)
    tx = circuit_breaker.pause(WQ_PAUSABLE, {"from": gate_seal_committee_account})

    # Registry-side: slot cleared, count decremented
    assert circuit_breaker.getPauser(WQ_PAUSABLE) == ZERO_ADDRESS
    assert circuit_breaker.getPausableCount(GATE_SEAL_COMMITTEE) == pre_count - 1
    assert WQ_PAUSABLE.lower() not in [addr.lower() for addr in circuit_breaker.getPausables()]

    # Events
    assert tx.events["PauserSet"]["pausable"].lower() == WQ_PAUSABLE.lower()
    assert tx.events["PauserSet"]["previousPauser"].lower() == GATE_SEAL_COMMITTEE.lower()
    assert tx.events["PauserSet"]["newPauser"] == ZERO_ADDRESS
    assert tx.events["PauseTriggered"]["pausable"].lower() == WQ_PAUSABLE.lower()
    assert tx.events["PauseTriggered"]["pauser"].lower() == GATE_SEAL_COMMITTEE.lower()
    assert tx.events["PauseTriggered"]["pauseDuration"] == CIRCUIT_BREAKER_PAUSE_DURATION

    # Pausable-side: paused, with the correct resume timestamp
    assert wq.isPaused()
    assert wq.getResumeSinceTimestamp() == tx.timestamp + CIRCUIT_BREAKER_PAUSE_DURATION


def test_pause_auto_resumes_after_pause_duration(
    circuit_breaker, gate_seal_committee_account
):
    wq = contracts.withdrawal_queue
    circuit_breaker.pause(WQ_PAUSABLE, {"from": gate_seal_committee_account})
    assert wq.isPaused()

    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert not wq.isPaused()


# ============================================================================
# Heartbeat side-effects from pause()
# ============================================================================
def test_pause_refreshes_heartbeat_when_pauser_has_more_coverage(
    circuit_breaker, csm_committee_account
):
    # CSM_COMMITTEE_MS covers six pausables; pausing one leaves it registered for the rest.
    assert circuit_breaker.getPausableCount(CSM_COMMITTEE_MS) >= 2

    tx = circuit_breaker.pause(CSM_PAUSABLE, {"from": csm_committee_account})
    expected_expiry = tx.timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL

    assert circuit_breaker.heartbeatExpiry(CSM_COMMITTEE_MS) == expected_expiry
    assert circuit_breaker.isPauserLive(CSM_COMMITTEE_MS)
    assert tx.events["HeartbeatUpdated"]["pauser"].lower() == CSM_COMMITTEE_MS.lower()
    assert tx.events["HeartbeatUpdated"]["newHeartbeatExpiry"] == expected_expiry


def test_pause_zeroes_heartbeat_when_pausing_last_pausable(
    circuit_breaker, agent_account, stranger
):
    # Use a fresh pauser registered for exactly one pausable so we hit the
    # "last pausable" branch cleanly, without disturbing other registrations.
    fresh_pauser = stranger.address
    circuit_breaker.registerPauser(WITHDRAWAL_QUEUE, fresh_pauser, {"from": agent_account})
    assert circuit_breaker.getPausableCount(fresh_pauser) == 1
    assert circuit_breaker.isPauserLive(fresh_pauser)

    tx = circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": stranger})

    assert circuit_breaker.heartbeatExpiry(fresh_pauser) == 0
    assert not circuit_breaker.isPauserLive(fresh_pauser)
    assert tx.events["HeartbeatUpdated"]["newHeartbeatExpiry"] == 0

    # Self-revive blocked
    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.heartbeat({"from": stranger})


# ============================================================================
# Negative cases
# ============================================================================
def test_pause_reverts_when_circuit_breaker_lacks_pause_role(
    circuit_breaker, agent_account, gate_seal_committee_account
):
    pausable = interface.IPausableUntilWithRoles(WITHDRAWAL_QUEUE)
    pausable.revokeRole(PAUSE_ROLE, CIRCUIT_BREAKER, {"from": agent_account})
    assert not pausable.hasRole(PAUSE_ROLE, CIRCUIT_BREAKER)

    # WithdrawalQueue's pauseFor uses OZ AccessControl which reverts with AccessControlUnauthorizedAccount.
    # We don't pin the exact revert string here — just confirm the call reverts and registry slot is preserved.
    with reverts():
        circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})

    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()


def test_pause_reverts_when_pausable_already_paused(
    circuit_breaker, reseal_manager_account, gate_seal_committee_account
):
    wq = contracts.withdrawal_queue
    wq.pauseFor(PAUSE_INFINITELY, {"from": reseal_manager_account})
    assert wq.isPaused()

    with reverts(encode_error("ResumedExpected()")):
        circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})

    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()


def test_pause_reverts_when_sender_not_pauser(circuit_breaker, stranger):
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": stranger})

    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()


def test_pauser_isolation(
    circuit_breaker, gate_seal_committee_account, csm_committee_account
):
    # GATE_SEAL_COMMITTEE covers WithdrawalQueue, not CSModule.
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(CSM_ADDRESS, {"from": gate_seal_committee_account})

    # CSM_COMMITTEE_MS covers CSModule, not WithdrawalQueue.
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": csm_committee_account})


# ============================================================================
# ResealManager coexistence
# ============================================================================
def test_reseal_manager_indefinite_pause_survives_circuit_breaker_auto_resume(
    circuit_breaker, gate_seal_committee_account, reseal_manager_account
):
    wq = contracts.withdrawal_queue
    circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})
    assert wq.isPaused()
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE) == ZERO_ADDRESS

    # ResealCommittee would normally resume + reseal via ResealManager; we shortcut
    # by impersonating ResealManager (which holds RESUME_ROLE and PAUSE_ROLE).
    wq.resume({"from": reseal_manager_account})
    assert not wq.isPaused()
    wq.pauseFor(PAUSE_INFINITELY, {"from": reseal_manager_account})
    assert wq.isPaused()

    # Pass CircuitBreaker's pauseDuration — the ResealManager indefinite pause must hold.
    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert wq.isPaused()
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE) == ZERO_ADDRESS


# ============================================================================
# Heartbeat
# ============================================================================
def test_heartbeat_happy_path(circuit_breaker, gate_seal_committee_account):
    tx = circuit_breaker.heartbeat({"from": gate_seal_committee_account})
    expected_expiry = tx.timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    assert circuit_breaker.heartbeatExpiry(GATE_SEAL_COMMITTEE) == expected_expiry
    assert tx.events["HeartbeatUpdated"]["newHeartbeatExpiry"] == expected_expiry


def test_heartbeat_reverts_for_non_pauser(circuit_breaker, stranger):
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.heartbeat({"from": stranger})


def test_heartbeat_reverts_for_expired_pauser(
    circuit_breaker, gate_seal_committee_account
):
    chain.sleep(CIRCUIT_BREAKER_HEARTBEAT_INTERVAL + 1)
    chain.mine(1)
    assert not circuit_breaker.isPauserLive(GATE_SEAL_COMMITTEE)

    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.heartbeat({"from": gate_seal_committee_account})


def test_pause_reverts_for_expired_pauser(
    circuit_breaker, gate_seal_committee_account
):
    chain.sleep(CIRCUIT_BREAKER_HEARTBEAT_INTERVAL + 1)
    chain.mine(1)
    assert not circuit_breaker.isPauserLive(GATE_SEAL_COMMITTEE)

    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})


# ============================================================================
# Admin authorization
# ============================================================================
@pytest.mark.parametrize(
    "method, args",
    [
        ("registerPauser", (WITHDRAWAL_QUEUE, GATE_SEAL_COMMITTEE)),
        ("setPauseDuration", (CIRCUIT_BREAKER_PAUSE_DURATION,)),
        ("setHeartbeatInterval", (CIRCUIT_BREAKER_HEARTBEAT_INTERVAL,)),
    ],
)
def test_admin_methods_revert_for_non_admin(circuit_breaker, stranger, method, args):
    fn = getattr(circuit_breaker, method)
    with reverts(encode_error("SenderNotAdmin()")):
        fn(*args, {"from": stranger})


# ============================================================================
# Admin parameter bounds (driven directly from impersonated Agent — bounds
# checking is independent of how the call reaches the admin)
# ============================================================================
def test_set_pause_duration_below_min_reverts(circuit_breaker, agent_account):
    with reverts(encode_error("PauseDurationBelowMin()")):
        circuit_breaker.setPauseDuration(
            CIRCUIT_BREAKER_MIN_PAUSE_DURATION - 1, {"from": agent_account}
        )


def test_set_pause_duration_above_max_reverts(circuit_breaker, agent_account):
    with reverts(encode_error("PauseDurationAboveMax()")):
        circuit_breaker.setPauseDuration(
            CIRCUIT_BREAKER_MAX_PAUSE_DURATION + 1, {"from": agent_account}
        )


def test_set_pause_duration_within_bounds_succeeds(circuit_breaker, agent_account):
    new_value = CIRCUIT_BREAKER_MIN_PAUSE_DURATION + 1
    tx = circuit_breaker.setPauseDuration(new_value, {"from": agent_account})
    assert circuit_breaker.pauseDuration() == new_value
    assert tx.events["PauseDurationUpdated"]["newPauseDuration"] == new_value


def test_set_heartbeat_interval_below_min_reverts(circuit_breaker, agent_account):
    with reverts(encode_error("HeartbeatIntervalBelowMin()")):
        circuit_breaker.setHeartbeatInterval(
            CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL - 1, {"from": agent_account}
        )


def test_set_heartbeat_interval_above_max_reverts(circuit_breaker, agent_account):
    with reverts(encode_error("HeartbeatIntervalAboveMax()")):
        circuit_breaker.setHeartbeatInterval(
            CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL + 1, {"from": agent_account}
        )


def test_set_heartbeat_interval_within_bounds_succeeds(circuit_breaker, agent_account):
    new_value = CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL + 1
    tx = circuit_breaker.setHeartbeatInterval(new_value, {"from": agent_account})
    assert circuit_breaker.heartbeatInterval() == new_value
    assert tx.events["HeartbeatIntervalUpdated"]["newHeartbeatInterval"] == new_value


def test_set_heartbeat_interval_does_not_retroact(circuit_breaker, agent_account):
    # Capture an existing registered pauser's expiry, change the interval, confirm it didn't move.
    pre_expiry = circuit_breaker.heartbeatExpiry(GATE_SEAL_COMMITTEE)
    new_interval = CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL + 12345
    circuit_breaker.setHeartbeatInterval(new_interval, {"from": agent_account})

    assert circuit_breaker.heartbeatExpiry(GATE_SEAL_COMMITTEE) == pre_expiry


# ============================================================================
# Admin re-registration via the full DG timelock flow (one end-to-end test).
# ============================================================================
def test_register_pauser_via_dg_timelock(
    circuit_breaker, voting_account, stranger
):
    new_pauser = stranger.address
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()

    encoded = circuit_breaker.registerPauser.encode_input(WITHDRAWAL_QUEUE, new_pauser)
    proposal_id = _submit_dg_proposal_via_voting(
        [agent_forward([(circuit_breaker.address, encoded)])],
        "re-register WQ pauser",
        voting_account,
    )

    # Before timelocks elapse, the proposal is not executable.
    with reverts():
        contracts.emergency_protected_timelock.execute(proposal_id, {"from": stranger})

    process_proposals([proposal_id])
    exec_block_timestamp = web3.eth.get_block("latest")["timestamp"]

    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == new_pauser.lower()
    assert circuit_breaker.heartbeatExpiry(new_pauser) == \
        exec_block_timestamp + circuit_breaker.heartbeatInterval()
    assert circuit_breaker.isPauserLive(new_pauser)


def test_deregister_pauser_via_admin(
    circuit_breaker, agent_account
):
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()
    pre_expiry = circuit_breaker.heartbeatExpiry(GATE_SEAL_COMMITTEE)
    assert pre_expiry > 0

    tx = circuit_breaker.registerPauser(WITHDRAWAL_QUEUE, ZERO_ADDRESS, {"from": agent_account})

    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE) == ZERO_ADDRESS
    assert WITHDRAWAL_QUEUE.lower() not in [a.lower() for a in circuit_breaker.getPausables()]
    assert tx.events["PauserSet"]["previousPauser"].lower() == GATE_SEAL_COMMITTEE.lower()
    assert tx.events["PauserSet"]["newPauser"] == ZERO_ADDRESS


# ============================================================================
# Emergency pause bypasses DG timelock
# ============================================================================
def test_emergency_pause_bypasses_dg_timelock(
    circuit_breaker, voting_account, gate_seal_committee_account
):
    # Submit a slow admin proposal that will sit in the DG timelock.
    encoded = circuit_breaker.setPauseDuration.encode_input(
        CIRCUIT_BREAKER_MIN_PAUSE_DURATION + 99
    )
    proposal_id = _submit_dg_proposal_via_voting(
        [agent_forward([(circuit_breaker.address, encoded)])],
        "admin proposal mid-timelock",
        voting_account,
    )

    pre_duration = circuit_breaker.pauseDuration()

    # Immediately trigger the emergency pause path — it must succeed in this block.
    wq = contracts.withdrawal_queue
    tx = circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})
    assert wq.isPaused()
    assert tx.events["PauseTriggered"]["pausable"].lower() == WITHDRAWAL_QUEUE.lower()

    # Admin proposal is unaffected — pauseDuration didn't change yet.
    assert circuit_breaker.pauseDuration() == pre_duration

    # Walking the timelock forward, the admin proposal eventually executes.
    process_proposals([proposal_id])
    assert circuit_breaker.pauseDuration() == CIRCUIT_BREAKER_MIN_PAUSE_DURATION + 99


# ============================================================================
# Recovery after auto-resume
# ============================================================================
def test_recovery_after_auto_resume(
    circuit_breaker, agent_account, gate_seal_committee_account
):
    wq = contracts.withdrawal_queue

    circuit_breaker.pause(WITHDRAWAL_QUEUE, {"from": gate_seal_committee_account})
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE) == ZERO_ADDRESS

    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert not wq.isPaused()

    # Admin re-registers the pauser, restoring coverage and refreshing heartbeat.
    tx = circuit_breaker.registerPauser(
        WITHDRAWAL_QUEUE, GATE_SEAL_COMMITTEE, {"from": agent_account}
    )
    assert circuit_breaker.getPauser(WITHDRAWAL_QUEUE).lower() == GATE_SEAL_COMMITTEE.lower()
    assert circuit_breaker.isPauserLive(GATE_SEAL_COMMITTEE)
    assert circuit_breaker.heartbeatExpiry(GATE_SEAL_COMMITTEE) == \
        tx.timestamp + circuit_breaker.heartbeatInterval()
