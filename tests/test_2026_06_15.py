from brownie import ZERO_ADDRESS, chain, interface, web3
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events,
)
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2026_06_15 import (
    DG_PROPOSAL_METADATA,
    MIGRATION_TARGETS,
    get_dg_items,
    get_vote_items,
    start_vote,
)
from utils.config import (
    CIRCUIT_BREAKER,
    CIRCUIT_BREAKER_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MAX_PAUSE_DURATION,
    CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL,
    CIRCUIT_BREAKER_MIN_PAUSE_DURATION,
    CIRCUIT_BREAKER_PAUSE_DURATION,
    RESEAL_MANAGER,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 1

# Per migration (one pausable each): revoke PAUSE_ROLE, grant PAUSE_ROLE, registerPauser.
EXPECTED_DG_EVENTS_FROM_AGENT = len(MIGRATION_TARGETS) * 3
EXPECTED_DG_EVENTS_COUNT = EXPECTED_DG_EVENTS_FROM_AGENT

IPFS_DESCRIPTION_HASH = ""


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):
    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)

    # V3 targets use namespaced role names whose hashes differ from the legacy
    # `keccak("PAUSE_ROLE")` / `keccak("RESUME_ROLE")` — resolve via the contract.
    pre_vote_resume_role_holders = {}
    pre_vote_cb_globals = {}

    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================
        for target in MIGRATION_TARGETS:
            pausable = interface.IPausableUntilWithRoles(target.pausable)
            pause_role_hash = str(pausable.PAUSE_ROLE())

            # Hard prerequisites: if CircuitBreaker already holds the role or already
            # has a pauser registered for this target, the migration was already
            # applied (or partially applied) and re-running this vote is unsafe.
            assert not pausable.hasRole(pause_role_hash, CIRCUIT_BREAKER), (
                f"CircuitBreaker should not have PAUSE_ROLE on {pausable.address} before vote"
            )
            assert circuit_breaker.getPauser(pausable.address) == ZERO_ADDRESS, (
                f"CircuitBreaker should not have a pauser for {pausable.address} before vote"
            )

            # Soft expectation: the legacy GateSeal currently holds PAUSE_ROLE. OZ
            # revokeRole is idempotent, so the DG proposal will succeed either way —
            # this is informational, not a precondition.
            if not pausable.hasRole(pause_role_hash, target.gate_seal):
                print(
                    f"  [warn] GateSeal {target.gate_seal} does not hold PAUSE_ROLE "
                    f"on {pausable.address} — revoke step will be a no-op"
                )

            resume_role_hash = str(pausable.RESUME_ROLE())
            count = pausable.getRoleMemberCount(resume_role_hash)
            pre_vote_resume_role_holders[pausable.address.lower()] = (
                count,
                tuple(
                    pausable.getRoleMember(resume_role_hash, i).lower()
                    for i in range(count)
                ),
            )

        # Snapshot CircuitBreaker globals that this vote MUST NOT change.
        pre_vote_cb_globals.update({
            "ADMIN": circuit_breaker.ADMIN(),
            "pauseDuration": circuit_breaker.pauseDuration(),
            "heartbeatInterval": circuit_breaker.heartbeatInterval(),
            "MIN_PAUSE_DURATION": circuit_breaker.MIN_PAUSE_DURATION(),
            "MAX_PAUSE_DURATION": circuit_breaker.MAX_PAUSE_DURATION(),
            "MIN_HEARTBEAT_INTERVAL": circuit_breaker.MIN_HEARTBEAT_INTERVAL(),
            "MAX_HEARTBEAT_INTERVAL": circuit_breaker.MAX_HEARTBEAT_INTERVAL(),
        })

        if IPFS_DESCRIPTION_HASH:
            assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=EXPECTED_DG_PROPOSAL_ID if EXPECTED_DG_PROPOSAL_ID is not None else timelock.getProposalsCount(),
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )


    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    dg_proposal_id = EXPECTED_DG_PROPOSAL_ID if EXPECTED_DG_PROPOSAL_ID is not None else timelock.getProposalsCount()
    details = timelock.getProposalDetails(dg_proposal_id)

    dg_execution_timestamp = None
    if details["status"] != PROPOSAL_STATUS["executed"]:
        if details["status"] == PROPOSAL_STATUS["submitted"]:
            chain.sleep(timelock.getAfterSubmitDelay() + 1)
            dual_governance.scheduleProposal(dg_proposal_id, {"from": stranger})

        if timelock.getProposalDetails(dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
            chain.sleep(timelock.getAfterScheduleDelay() + 1)

            dg_tx: TransactionReceipt = timelock.execute(dg_proposal_id, {"from": stranger})
            dg_execution_timestamp = dg_tx.timestamp
            display_dg_events(dg_tx)
            dg_events = group_dg_events_from_receipt(
                dg_tx,
                timelock=EMERGENCY_PROTECTED_TIMELOCK,
                admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            )
            assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
            assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT


            # =======================================================================
            # ============================ DG events checks =========================
            # =======================================================================
            event_index = 0
            for target in MIGRATION_TARGETS:
                pausable = interface.IPausableUntilWithRoles(target.pausable)
                pause_role_hash = str(pausable.PAUSE_ROLE())

                validate_revoke_role_event(
                    dg_events[event_index],
                    role=pause_role_hash,
                    revoke_from=target.gate_seal,
                    sender=AGENT,
                    emitted_by=pausable.address,
                )
                event_index += 1

                validate_grant_role_event(
                    dg_events[event_index],
                    role=pause_role_hash,
                    grant_to=CIRCUIT_BREAKER,
                    sender=AGENT,
                    emitted_by=pausable.address,
                )
                event_index += 1

                # registerPauser emits both PauserSet and HeartbeatUpdated
                register_group = dg_events[event_index]
                assert "PauserSet" in register_group, (
                    f"No PauserSet event for {pausable.address}"
                )
                pauser_set = register_group["PauserSet"]
                assert pauser_set["pausable"].lower() == pausable.address.lower(), (
                    f"Wrong pausable in PauserSet event for {pausable.address}"
                )
                assert pauser_set["previousPauser"] == ZERO_ADDRESS, (
                    f"PauserSet.previousPauser for {pausable.address} should be zero"
                )
                assert pauser_set["newPauser"].lower() == target.pauser.lower(), (
                    f"PauserSet.newPauser for {pausable.address} should be {target.pauser}"
                )
                assert pauser_set["_emitted_by"].lower() == CIRCUIT_BREAKER.lower(), (
                    f"PauserSet for {pausable.address} should be emitted by CircuitBreaker"
                )

                assert "HeartbeatUpdated" in register_group, (
                    f"No HeartbeatUpdated event for {pausable.address}"
                )
                heartbeat_updated = register_group["HeartbeatUpdated"]
                assert heartbeat_updated["pauser"].lower() == target.pauser.lower(), (
                    f"HeartbeatUpdated.pauser for {pausable.address} should be {target.pauser}"
                )
                assert heartbeat_updated["_emitted_by"].lower() == CIRCUIT_BREAKER.lower(), (
                    f"HeartbeatUpdated for {pausable.address} should be emitted by CircuitBreaker"
                )
                event_index += 1


    # =========================================================================
    # ==================== After DG proposal executed checks ==================
    # =========================================================================
    expected_pausables = {t.pausable.lower() for t in MIGRATION_TARGETS}
    on_chain_pausables = {addr.lower() for addr in circuit_breaker.getPausables()}
    assert on_chain_pausables == expected_pausables, (
        f"CircuitBreaker.getPausables() mismatch: expected {expected_pausables}, got {on_chain_pausables}"
    )

    expected_pausable_counts = {}
    for t in MIGRATION_TARGETS:
        expected_pausable_counts[t.pauser.lower()] = expected_pausable_counts.get(t.pauser.lower(), 0) + 1

    for target in MIGRATION_TARGETS:
        pausable = interface.IPausableUntilWithRoles(target.pausable)
        pause_role_hash = str(pausable.PAUSE_ROLE())

        # PAUSE_ROLE: GateSeal out, CircuitBreaker in, count exactly 2 with ResealManager.
        assert not pausable.hasRole(pause_role_hash, target.gate_seal), (
            f"GateSeal {target.gate_seal} should not have PAUSE_ROLE on {pausable.address} after vote"
        )
        assert pausable.hasRole(pause_role_hash, CIRCUIT_BREAKER), (
            f"CircuitBreaker should have PAUSE_ROLE on {pausable.address} after vote"
        )
        assert pausable.getRoleMemberCount(pause_role_hash) == 2, (
            f"{pausable.address} should have exactly 2 PAUSE_ROLE holders after vote"
        )
        post_vote_pause_holders = {
            pausable.getRoleMember(pause_role_hash, 0).lower(),
            pausable.getRoleMember(pause_role_hash, 1).lower(),
        }
        assert post_vote_pause_holders == {CIRCUIT_BREAKER.lower(), RESEAL_MANAGER.lower()}, (
            f"{pausable.address} PAUSE_ROLE holders {post_vote_pause_holders} != "
            f"{{CircuitBreaker, ResealManager}}"
        )

        # RESUME_ROLE: untouched by the vote.
        if pre_vote_resume_role_holders:
            resume_role_hash = str(pausable.RESUME_ROLE())
            count = pausable.getRoleMemberCount(resume_role_hash)
            pre_count, pre_holders = pre_vote_resume_role_holders[pausable.address.lower()]
            assert count == pre_count, (
                f"{pausable.address} RESUME_ROLE holder count changed from {pre_count} to {count}"
            )
            post_holders = tuple(
                pausable.getRoleMember(resume_role_hash, i).lower() for i in range(count)
            )
            assert post_holders == pre_holders, (
                f"{pausable.address} RESUME_ROLE holders changed from {pre_holders} to {post_holders}"
            )

        assert circuit_breaker.getPauser(pausable.address).lower() == target.pauser.lower(), (
            f"CircuitBreaker pauser for {pausable.address} should be {target.pauser} after vote"
        )

    # Per-pauser checks (deduped across migrations that share a pauser)
    for pauser, expected_count in expected_pausable_counts.items():
        assert circuit_breaker.getPausableCount(pauser) == expected_count, (
            f"getPausableCount mismatch for {pauser}"
        )
        assert circuit_breaker.isPauserLive(pauser), f"{pauser} should be live after vote"
        if dg_execution_timestamp is not None:
            # Exact equality is only meaningful when this test executed the DG proposal —
            # otherwise the execution block was mined before this test ran (e.g. by the
            # autoexecute_vote fixture) and we can't recover its timestamp.
            assert circuit_breaker.heartbeatExpiry(pauser) == (
                dg_execution_timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
            ), (
                f"heartbeatExpiry({pauser}) should equal DG execution timestamp + "
                f"heartbeat interval"
            )

    # CircuitBreaker globals — the vote must NOT touch these.
    assert circuit_breaker.ADMIN() == AGENT
    assert circuit_breaker.pauseDuration() == CIRCUIT_BREAKER_PAUSE_DURATION
    assert circuit_breaker.heartbeatInterval() == CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    assert circuit_breaker.MIN_PAUSE_DURATION() == CIRCUIT_BREAKER_MIN_PAUSE_DURATION
    assert circuit_breaker.MAX_PAUSE_DURATION() == CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    assert circuit_breaker.MIN_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
    assert circuit_breaker.MAX_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL

    if pre_vote_cb_globals:
        for key, value in pre_vote_cb_globals.items():
            current = getattr(circuit_breaker, key)()
            assert current == value, f"CircuitBreaker.{key} changed from {value} to {current}"
