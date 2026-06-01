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
from utils.test.event_validators.circuit_breaker import validate_register_pauser_event
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2026_06_17 import (
    DG_PROPOSAL_METADATA,
    MIGRATION_TARGETS,
    get_dg_items,
    get_vote_items,
    start_vote,
)

# ============================================================================
# ============================== Constants ===================================
# ============================================================================
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"

CIRCUIT_BREAKER_MIN_PAUSE_DURATION = 432000        # 5 days
CIRCUIT_BREAKER_MAX_PAUSE_DURATION = 5184000       # 60 days
CIRCUIT_BREAKER_PAUSE_DURATION = 1814400           # 21 days
CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL = 2592000   # 30 days
CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL = 94608000  # 1095 days (~3 years)
CIRCUIT_BREAKER_HEARTBEAT_INTERVAL = 31536000      # 1 year (365 days)

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"

# Operational items
CURATED_MODULE = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"

LOL_ALLOWED_RECIPIENTS_REGISTRY = "0x48c4929630099b217136b64089E8543dB0E5163a"
LOL_OLD_LIMIT = 6000 * 10**18
LOL_NEW_LIMIT = 8000 * 10**18
LOL_PERIOD_DURATION_MONTHS = 6

PIER_TWO_NO_ID = 36
PIER_TWO_NAME_OLD = "Pier Two"
PIER_TWO_NAME_NEW = "MAVAN"

# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 1

# Per migration (one pausable each): revoke PAUSE_ROLE, grant PAUSE_ROLE, registerPauser.
# Plus 2 operational items: 1.34 LOL Easy Track limit increase, 1.35 Node Operator rename.
EXPECTED_DG_EVENTS_FROM_AGENT = len(MIGRATION_TARGETS) * 3 + 2
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
    lol_registry = interface.AllowedRecipientRegistry(LOL_ALLOWED_RECIPIENTS_REGISTRY)
    curated_module = interface.NodeOperatorsRegistry(CURATED_MODULE)

    pre_dg_resume_role_holders = {}
    pre_dg_cb_globals = {}

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
        # =======================================================================
        # ======================= Before DG enactment checks ====================
        # =======================================================================
        for target in MIGRATION_TARGETS:
            pausable = interface.IPausableUntilWithRoles(target.pausable)
            pause_role_hash = str(pausable.PAUSE_ROLE())

            assert not pausable.hasRole(pause_role_hash, CIRCUIT_BREAKER), (
                f"CircuitBreaker should not have PAUSE_ROLE on {pausable.address} before DG enactment"
            )
            assert circuit_breaker.getPauser(pausable.address) == ZERO_ADDRESS, (
                f"CircuitBreaker should not have a pauser for {pausable.address} before DG enactment"
            )

            assert pausable.hasRole(pause_role_hash, target.gate_seal), (
                f"GateSeal {target.gate_seal} should hold PAUSE_ROLE on {pausable.address} before DG enactment"
            )

            resume_role_hash = str(pausable.RESUME_ROLE())
            # not all pausables have `getRoleMembers`, so we have to use `getRoleMember` in a loop
            resume_role_holders = sorted(
                pausable.getRoleMember(resume_role_hash, i).lower()
                for i in range(pausable.getRoleMemberCount(resume_role_hash))
            )
            pre_dg_resume_role_holders[pausable.address.lower()] = resume_role_holders

        # Snapshot CircuitBreaker config that the DG proposal MUST NOT change.
        pre_dg_cb_globals.update({
            "ADMIN": circuit_breaker.ADMIN(),
            "pauseDuration": circuit_breaker.pauseDuration(),
            "heartbeatInterval": circuit_breaker.heartbeatInterval(),
            "MIN_PAUSE_DURATION": circuit_breaker.MIN_PAUSE_DURATION(),
            "MAX_PAUSE_DURATION": circuit_breaker.MAX_PAUSE_DURATION(),
            "MIN_HEARTBEAT_INTERVAL": circuit_breaker.MIN_HEARTBEAT_INTERVAL(),
            "MAX_HEARTBEAT_INTERVAL": circuit_breaker.MAX_HEARTBEAT_INTERVAL(),
        })

        # Operational items pre-state (items 1.34, 1.35).
        lol_limit_before, lol_period_before = lol_registry.getLimitParameters()
        assert lol_limit_before == LOL_OLD_LIMIT, (
            f"LOL limit before DG enactment should be {LOL_OLD_LIMIT}, got {lol_limit_before}"
        )
        assert lol_period_before == LOL_PERIOD_DURATION_MONTHS, (
            f"LOL period before DG enactment should be {LOL_PERIOD_DURATION_MONTHS}, got {lol_period_before}"
        )
        assert curated_module.getNodeOperator(PIER_TWO_NO_ID, True)["name"] == PIER_TWO_NAME_OLD, (
            f"Node Operator {PIER_TWO_NO_ID} name before DG enactment should be {PIER_TWO_NAME_OLD}"
        )

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
                validate_register_pauser_event(
                    dg_events[event_index],
                    pausable_address=pausable.address,
                    expected_pauser=target.pauser,
                    emitted_by=CIRCUIT_BREAKER,
                )
                event_index += 1

            # 1.34. LOL Easy Track limit increase
            _, _, lol_period_start_after, _ = lol_registry.getPeriodState()
            validate_set_limit_parameter_event(
                dg_events[event_index],
                limit=LOL_NEW_LIMIT,
                period_duration_month=LOL_PERIOD_DURATION_MONTHS,
                period_start_timestamp=lol_period_start_after,
                emitted_by=LOL_ALLOWED_RECIPIENTS_REGISTRY,
            )
            event_index += 1

            # 1.35. Change Node Operator Pier Two name to MAVAN
            validate_node_operator_name_set_event(
                dg_events[event_index],
                NodeOperatorNameSetItem(nodeOperatorId=PIER_TWO_NO_ID, name=PIER_TWO_NAME_NEW),
                emitted_by=CURATED_MODULE,
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

        assert not pausable.hasRole(pause_role_hash, target.gate_seal), (
            f"GateSeal {target.gate_seal} should not have PAUSE_ROLE on {pausable.address} after vote"
        )
        assert pausable.hasRole(pause_role_hash, CIRCUIT_BREAKER), (
            f"CircuitBreaker should have PAUSE_ROLE on {pausable.address} after vote"
        )
        assert pausable.getRoleMemberCount(pause_role_hash) == 2, (
            f"{pausable.address} should have exactly 2 PAUSE_ROLE holders after vote"
        )
        assert {
            pausable.getRoleMember(pause_role_hash, 0).lower(),
            pausable.getRoleMember(pause_role_hash, 1).lower(),
        } == {CIRCUIT_BREAKER.lower(), RESEAL_MANAGER.lower()}, (
            f"{pausable.address} PAUSE_ROLE holders do not match {{CircuitBreaker, ResealManager}}"
        )

        # RESUME_ROLE: untouched by the DG proposal.
        if pre_dg_resume_role_holders:
            resume_role_hash = str(pausable.RESUME_ROLE())
            post_dg_resume_role_holders = sorted(
                pausable.getRoleMember(resume_role_hash, i).lower()
                for i in range(pausable.getRoleMemberCount(resume_role_hash))
            )
            pre_holders = pre_dg_resume_role_holders[pausable.address.lower()]
            assert post_dg_resume_role_holders == pre_holders, (
                f"{pausable.address} RESUME_ROLE holders changed from {pre_holders} to {post_dg_resume_role_holders}"
            )

        assert circuit_breaker.getPauser(pausable.address).lower() == target.pauser.lower(), (
            f"CircuitBreaker pauser for {pausable.address} should be {target.pauser} after vote"
        )

    # Per-pauser checks (deduped)
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

    # CircuitBreaker globals — the DG proposal must NOT touch these.
    assert circuit_breaker.ADMIN() == AGENT
    assert circuit_breaker.pauseDuration() == CIRCUIT_BREAKER_PAUSE_DURATION
    assert circuit_breaker.heartbeatInterval() == CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    assert circuit_breaker.MIN_PAUSE_DURATION() == CIRCUIT_BREAKER_MIN_PAUSE_DURATION
    assert circuit_breaker.MAX_PAUSE_DURATION() == CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    assert circuit_breaker.MIN_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
    assert circuit_breaker.MAX_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL

    if pre_dg_cb_globals:
        for key, value in pre_dg_cb_globals.items():
            current = getattr(circuit_breaker, key)()
            assert current == value, f"CircuitBreaker.{key} changed from {value} to {current}"


    # =========================================================================
    # ============= After DG: operational items (1.34, 1.35) ==================
    # =========================================================================
    lol_limit_after, lol_period_after = lol_registry.getLimitParameters()
    assert lol_limit_after == LOL_NEW_LIMIT, (
        f"LOL limit after vote should be {LOL_NEW_LIMIT}, got {lol_limit_after}"
    )
    assert lol_period_after == LOL_PERIOD_DURATION_MONTHS, (
        f"LOL period after vote should be {LOL_PERIOD_DURATION_MONTHS}, got {lol_period_after}"
    )

    assert curated_module.getNodeOperator(PIER_TWO_NO_ID, True)["name"] == PIER_TWO_NAME_NEW, (
        f"Node Operator {PIER_TWO_NO_ID} name after vote should be {PIER_TWO_NAME_NEW}"
    )


    # =========================================================================
    # ============== Happy path: each pauser can pause its pausable ===========
    # =========================================================================
    for target in MIGRATION_TARGETS:
        pausable = interface.IPausableUntilWithRoles(target.pausable)
        assert not pausable.isPaused(), f"{pausable.address} should not be paused before happy-path pause"

        pauser = accounts.at(target.pauser, force=True)
        tx = circuit_breaker.pause(target.pausable, {"from": pauser})

        assert pausable.isPaused(), f"{pausable.address} should be paused after CircuitBreaker.pause"
        assert pausable.getResumeSinceTimestamp() == tx.timestamp + CIRCUIT_BREAKER_PAUSE_DURATION, (
            f"{pausable.address} resume-since timestamp should be tx.timestamp + pauseDuration"
        )
