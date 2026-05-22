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
    GATE_SEAL_COMMITTEE as CIRCUIT_BREAKER_COMMITTEE,
    PREDEPOSIT_GUARANTEE,
    RESEAL_MANAGER,
    TRIGGERABLE_WITHDRAWALS_GATEWAY,
    VALIDATORS_EXIT_BUS_ORACLE,
    VAULT_HUB,
    VOTING,
    contracts,
)
from utils.agent import agent_forward
from utils.dual_governance import process_proposals
from utils.evm_script import encode_error

PAUSE_INFINITELY = 2**256 - 1


@pytest.fixture(scope="module")
def circuit_breaker():
    return interface.CircuitBreaker(CIRCUIT_BREAKER)


@pytest.fixture(scope="module")
def agent() -> Account:
    return accounts.at(AGENT, force=True)


@pytest.fixture(scope="module")
def voting() -> Account:
    return accounts.at(VOTING, force=True)


@pytest.fixture(scope="module")
def reseal_manager() -> Account:
    return accounts.at(RESEAL_MANAGER, force=True)


@pytest.fixture(scope="module")
def circuit_breaker_committee() -> Account:
    return accounts.at(CIRCUIT_BREAKER_COMMITTEE, force=True)


@pytest.fixture(scope="module")
def csm_committee() -> Account:
    return accounts.at(CSM_COMMITTEE_MS, force=True)


@pytest.fixture(scope="module")
def withdrawal_queue():
    return contracts.withdrawal_queue


def _submit_dg_proposal_via_voting(calls, description, voting_acct):
    """Submit a DG proposal directly via the Voting account (impersonated), bypassing the Aragon vote."""
    return contracts.dual_governance.submitProposal(
        [(addr, 0, data) for addr, data in calls], description, {"from": voting_acct}
    ).events["ProposalSubmitted"][0]["proposalId"]


# ============================================================================
# Per-pausable pause flow — event order, state transitions, auto-resume
# ============================================================================
def test_pause_flow(
    circuit_breaker, circuit_breaker_committee, withdrawal_queue
):
    assert not withdrawal_queue.isPaused()
    assert circuit_breaker.getPauser(withdrawal_queue.address) == circuit_breaker_committee.address

    pre_count = circuit_breaker.getPausableCount(circuit_breaker_committee.address)
    tx = circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})

    assert circuit_breaker.getPauser(withdrawal_queue.address) == ZERO_ADDRESS
    assert circuit_breaker.getPausableCount(circuit_breaker_committee.address) == pre_count - 1
    assert withdrawal_queue.address not in circuit_breaker.getPausables()

    assert tx.events["PauserSet"]["pausable"] == withdrawal_queue.address
    assert tx.events["PauserSet"]["previousPauser"] == circuit_breaker_committee.address
    assert tx.events["PauserSet"]["newPauser"] == ZERO_ADDRESS
    assert tx.events["PauseTriggered"]["pausable"] == withdrawal_queue.address
    assert tx.events["PauseTriggered"]["pauser"] == circuit_breaker_committee.address
    assert tx.events["PauseTriggered"]["pauseDuration"] == CIRCUIT_BREAKER_PAUSE_DURATION

    assert withdrawal_queue.isPaused()
    assert withdrawal_queue.getResumeSinceTimestamp() == tx.timestamp + CIRCUIT_BREAKER_PAUSE_DURATION


def test_pause_auto_resumes_after_pause_duration(
    circuit_breaker, circuit_breaker_committee, withdrawal_queue
):
    circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})
    assert withdrawal_queue.isPaused()

    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert not withdrawal_queue.isPaused()


# ============================================================================
# Heartbeat side-effects from pause()
# ============================================================================
def test_pause_refreshes_heartbeat_when_pauser_has_more_pausables(
    circuit_breaker, csm_committee
):
    assert circuit_breaker.getPausableCount(csm_committee.address) >= 2

    tx = circuit_breaker.pause(CSM_ADDRESS, {"from": csm_committee})
    expected_expiry = tx.timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL

    assert circuit_breaker.heartbeatExpiry(csm_committee.address) == expected_expiry
    assert circuit_breaker.isPauserLive(csm_committee.address)
    assert tx.events["HeartbeatUpdated"]["pauser"] == csm_committee.address
    assert tx.events["HeartbeatUpdated"]["newHeartbeatExpiry"] == expected_expiry


def test_pause_zeroes_heartbeat_when_pausing_last_pausable(
    circuit_breaker, agent, stranger, withdrawal_queue
):
    circuit_breaker.registerPauser(withdrawal_queue.address, stranger.address, {"from": agent})
    assert circuit_breaker.getPausableCount(stranger.address) == 1
    assert circuit_breaker.isPauserLive(stranger.address)

    assert circuit_breaker.pause(
        withdrawal_queue.address, {"from": stranger}
    ).events["HeartbeatUpdated"]["newHeartbeatExpiry"] == 0
    assert circuit_breaker.heartbeatExpiry(stranger.address) == 0
    assert not circuit_breaker.isPauserLive(stranger.address)

    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.heartbeat({"from": stranger})


# ============================================================================
# Negative cases
# ============================================================================
def test_pause_reverts_when_circuit_breaker_lacks_pause_role(
    circuit_breaker, agent, circuit_breaker_committee, withdrawal_queue
):
    pause_role = withdrawal_queue.PAUSE_ROLE()
    withdrawal_queue.revokeRole(pause_role, circuit_breaker.address, {"from": agent})
    assert not withdrawal_queue.hasRole(pause_role, circuit_breaker.address)

    with reverts():
        circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})


def test_pause_reverts_when_pausable_already_paused(
    circuit_breaker, reseal_manager, circuit_breaker_committee, withdrawal_queue
):
    withdrawal_queue.pauseFor(PAUSE_INFINITELY, {"from": reseal_manager})
    assert withdrawal_queue.isPaused()

    with reverts(encode_error("ResumedExpected()")):
        circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})


def test_pause_reverts_when_sender_not_pauser(circuit_breaker, stranger, withdrawal_queue):
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(withdrawal_queue.address, {"from": stranger})


def test_pauser_isolation(
    circuit_breaker, circuit_breaker_committee, csm_committee, withdrawal_queue
):
    # CIRCUIT_BREAKER_COMMITTEE covers WithdrawalQueue, not CSModule.
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(CSM_ADDRESS, {"from": circuit_breaker_committee})

    # CSM_COMMITTEE_MS covers CSModule, not WithdrawalQueue.
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.pause(withdrawal_queue.address, {"from": csm_committee})


# ============================================================================
# ResealManager coexistence
# ============================================================================
def test_reseal_manager_infinite_pause(
    circuit_breaker, circuit_breaker_committee, reseal_manager, withdrawal_queue
):
    circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})
    assert withdrawal_queue.isPaused()
    assert circuit_breaker.getPauser(withdrawal_queue.address) == ZERO_ADDRESS

    withdrawal_queue.resume({"from": reseal_manager})
    assert not withdrawal_queue.isPaused()
    withdrawal_queue.pauseFor(PAUSE_INFINITELY, {"from": reseal_manager})
    assert withdrawal_queue.isPaused()

    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert withdrawal_queue.isPaused()
    assert circuit_breaker.getPauser(withdrawal_queue.address) == ZERO_ADDRESS


# ============================================================================
# Heartbeat
# ============================================================================
def test_heartbeat(circuit_breaker, circuit_breaker_committee):
    tx = circuit_breaker.heartbeat({"from": circuit_breaker_committee})
    expected_expiry = tx.timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    assert circuit_breaker.heartbeatExpiry(circuit_breaker_committee.address) == expected_expiry
    assert tx.events["HeartbeatUpdated"]["newHeartbeatExpiry"] == expected_expiry


def test_heartbeat_reverts_for_non_pauser(circuit_breaker, stranger):
    with reverts(encode_error("SenderNotPauser()")):
        circuit_breaker.heartbeat({"from": stranger})


def test_heartbeat_reverts_for_expired_pauser(
    circuit_breaker, circuit_breaker_committee
):
    chain.sleep(CIRCUIT_BREAKER_HEARTBEAT_INTERVAL + 1)
    chain.mine(1)
    assert not circuit_breaker.isPauserLive(circuit_breaker_committee.address)

    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.heartbeat({"from": circuit_breaker_committee})


def test_pause_reverts_for_expired_pauser(
    circuit_breaker, circuit_breaker_committee, withdrawal_queue
):
    chain.sleep(CIRCUIT_BREAKER_HEARTBEAT_INTERVAL + 1)
    chain.mine(1)
    assert not circuit_breaker.isPauserLive(circuit_breaker_committee.address)

    with reverts(encode_error("HeartbeatExpired()")):
        circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})


# ============================================================================
# Admin authorization
# ============================================================================
def test_register_pauser_reverts_for_non_admin(
    circuit_breaker, stranger, withdrawal_queue, circuit_breaker_committee
):
    with reverts(encode_error("SenderNotAdmin()")):
        circuit_breaker.registerPauser(
            withdrawal_queue.address, circuit_breaker_committee.address, {"from": stranger}
        )


def test_set_pause_duration_reverts_for_non_admin(circuit_breaker, stranger):
    with reverts(encode_error("SenderNotAdmin()")):
        circuit_breaker.setPauseDuration(CIRCUIT_BREAKER_PAUSE_DURATION, {"from": stranger})


def test_set_heartbeat_interval_reverts_for_non_admin(circuit_breaker, stranger):
    with reverts(encode_error("SenderNotAdmin()")):
        circuit_breaker.setHeartbeatInterval(CIRCUIT_BREAKER_HEARTBEAT_INTERVAL, {"from": stranger})


# ============================================================================
# Config bounds
# ============================================================================
def test_set_pause_duration_below_min_reverts(circuit_breaker, agent):
    with reverts(encode_error("PauseDurationBelowMin()")):
        circuit_breaker.setPauseDuration(
            CIRCUIT_BREAKER_MIN_PAUSE_DURATION - 1, {"from": agent}
        )


def test_set_pause_duration_above_max_reverts(circuit_breaker, agent):
    with reverts(encode_error("PauseDurationAboveMax()")):
        circuit_breaker.setPauseDuration(
            CIRCUIT_BREAKER_MAX_PAUSE_DURATION + 1, {"from": agent}
        )


def test_set_pause_duration_within_bounds_succeeds(circuit_breaker, agent):
    new_value = CIRCUIT_BREAKER_MIN_PAUSE_DURATION + 1
    assert circuit_breaker.setPauseDuration(
        new_value, {"from": agent}
    ).events["PauseDurationUpdated"]["newPauseDuration"] == new_value
    assert circuit_breaker.pauseDuration() == new_value


def test_set_heartbeat_interval_below_min_reverts(circuit_breaker, agent):
    with reverts(encode_error("HeartbeatIntervalBelowMin()")):
        circuit_breaker.setHeartbeatInterval(
            CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL - 1, {"from": agent}
        )


def test_set_heartbeat_interval_above_max_reverts(circuit_breaker, agent):
    with reverts(encode_error("HeartbeatIntervalAboveMax()")):
        circuit_breaker.setHeartbeatInterval(
            CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL + 1, {"from": agent}
        )


def test_set_heartbeat_interval_within_bounds_succeeds(circuit_breaker, agent):
    new_value = CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL + 1
    assert circuit_breaker.setHeartbeatInterval(
        new_value, {"from": agent}
    ).events["HeartbeatIntervalUpdated"]["newHeartbeatInterval"] == new_value
    assert circuit_breaker.heartbeatInterval() == new_value


def test_set_heartbeat_interval_does_not_retroact(circuit_breaker, agent, circuit_breaker_committee):
    # Capture an existing registered pauser's expiry, change the interval, confirm it didn't move.
    pre_expiry = circuit_breaker.heartbeatExpiry(circuit_breaker_committee.address)
    circuit_breaker.setHeartbeatInterval(
        CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL + 12345, {"from": agent}
    )

    assert circuit_breaker.heartbeatExpiry(circuit_breaker_committee.address) == pre_expiry


# ============================================================================
# Admin re-registration via the full DG timelock flow
# ============================================================================
def test_register_pauser_via_dg(
    circuit_breaker, voting, stranger, withdrawal_queue, circuit_breaker_committee
):
    assert circuit_breaker.getPauser(withdrawal_queue.address) == circuit_breaker_committee.address

    proposal_id = _submit_dg_proposal_via_voting(
        [agent_forward([(
            circuit_breaker.address,
            circuit_breaker.registerPauser.encode_input(withdrawal_queue.address, stranger.address),
        )])],
        "re-register WQ pauser",
        voting,
    )

    # Before timelocks elapse, the proposal is not executable.
    with reverts():
        contracts.emergency_protected_timelock.execute(proposal_id, {"from": stranger})

    process_proposals([proposal_id])

    assert circuit_breaker.getPauser(withdrawal_queue.address) == stranger.address
    assert circuit_breaker.heartbeatExpiry(stranger.address) == \
        web3.eth.get_block("latest")["timestamp"] + circuit_breaker.heartbeatInterval()
    assert circuit_breaker.isPauserLive(stranger.address)


def test_deregister_pauser_via_admin(
    circuit_breaker, agent, withdrawal_queue, circuit_breaker_committee
):
    assert circuit_breaker.getPauser(withdrawal_queue.address) == circuit_breaker_committee.address
    pre_expiry = circuit_breaker.heartbeatExpiry(circuit_breaker_committee.address)
    assert pre_expiry > 0

    tx = circuit_breaker.registerPauser(withdrawal_queue.address, ZERO_ADDRESS, {"from": agent})

    assert circuit_breaker.getPauser(withdrawal_queue.address) == ZERO_ADDRESS
    assert withdrawal_queue.address not in circuit_breaker.getPausables()
    assert tx.events["PauserSet"]["previousPauser"] == circuit_breaker_committee.address
    assert tx.events["PauserSet"]["newPauser"] == ZERO_ADDRESS


# ============================================================================
# Recovery after auto-resume
# ============================================================================
def test_recovery_after_auto_resume(
    circuit_breaker, agent, circuit_breaker_committee, withdrawal_queue
):
    circuit_breaker.pause(withdrawal_queue.address, {"from": circuit_breaker_committee})
    assert circuit_breaker.getPauser(withdrawal_queue.address) == ZERO_ADDRESS

    chain.sleep(CIRCUIT_BREAKER_PAUSE_DURATION + 1)
    chain.mine(1)
    assert not withdrawal_queue.isPaused()

    # Admin re-registers the pauser, restoring coverage and refreshing heartbeat.
    circuit_breaker.registerPauser(
        withdrawal_queue.address, circuit_breaker_committee.address, {"from": agent}
    )
    assert circuit_breaker.getPauser(withdrawal_queue.address) == circuit_breaker_committee.address
    assert circuit_breaker.isPauserLive(circuit_breaker_committee.address)
    assert circuit_breaker.heartbeatExpiry(circuit_breaker_committee.address) == \
        web3.eth.get_block("latest")["timestamp"] + circuit_breaker.heartbeatInterval()
