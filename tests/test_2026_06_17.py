from typing import NamedTuple

from brownie import ZERO_ADDRESS, chain, interface, reverts, web3
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
from utils.permission_parameters import Param, Op, ArgumentValue, encode_permission_params
from utils.test.event_validators.circuit_breaker import validate_register_pauser_event
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import (
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    validate_node_operator_deactivated,
    NodeOperatorNameSetItem,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str

# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_06_17 import (
    DG_PROPOSAL_METADATA,
    get_dg_items,
    get_vote_items,
    start_vote,
)


# ============================================================================
# ===================== Migration targets (hardcoded) =======================
# ============================================================================
# Deliberately NOT imported from the vote script: the expected (pausable, pauser,
# gate_seal) triples are hardcoded here as an independent cross-check, so a wrong
# pairing or a missing/extra target in the vote is caught by the test.
class MigrationTarget(NamedTuple):
    pausable: str
    pauser: str
    gate_seal: str


MIGRATION_TARGETS = [
    # WithdrawalQueue
    MigrationTarget(
        "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1",
        "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C",
        "0x8A854C4E750CDf24f138f34A9061b2f556066912",
    ),
    # ValidatorsExitBusOracle
    MigrationTarget(
        "0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e",
        "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C",
        "0xA6BC802fAa064414AA62117B4a53D27fFfF741F1",
    ),
    # TriggerableWithdrawalsGateway
    MigrationTarget(
        "0xDC00116a0D3E064427dA2600449cfD2566B3037B",
        "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C",
        "0xA6BC802fAa064414AA62117B4a53D27fFfF741F1",
    ),
    # VaultHub
    MigrationTarget(
        "0x1d201BE093d847f6446530Efb0E8Fb426d176709",
        "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C",
        "0x881dAd714679A6FeaA636446A0499101375A365c",
    ),
    # PredepositGuarantee
    MigrationTarget(
        "0xF4bF42c6D6A0E38825785048124DBAD6c9eaaac3",
        "0x8772E3a2D86B9347A2688f9bc1808A6d8917760C",
        "0x881dAd714679A6FeaA636446A0499101375A365c",
    ),
    # CSModule
    MigrationTarget(
        "0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
    # CSAccounting
    MigrationTarget(
        "0x4d72BFF1BeaC69925F8Bd12526a39BAAb069e5Da",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
    # CSFeeOracle
    MigrationTarget(
        "0x4D4074628678Bd302921c20573EEa1ed38DdF7FB",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
    # CSVerifierV2
    MigrationTarget(
        "0xdC5FE1782B6943f318E05230d688713a560063DC",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
    # CSVettedGate
    MigrationTarget(
        "0xB314D4A76C457c93150d308787939063F4Cc67E0",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
    # CSEjector
    MigrationTarget(
        "0xc72b58aa02E0e98cF8A4a0E9Dce75e763800802C",
        "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f",
        "0xE1686C2E90eb41a48356c1cC7FaA17629af3ADB3",
    ),
]

# ============================================================================
# ============================== Constants ===================================
# ============================================================================
CIRCUIT_BREAKER = "0x6019CB557978296BA3C08a7B73225C0975DFB2F7"

CIRCUIT_BREAKER_MIN_PAUSE_DURATION = 432000  # 5 days
CIRCUIT_BREAKER_MAX_PAUSE_DURATION = 5184000  # 60 days
CIRCUIT_BREAKER_PAUSE_DURATION = 1814400  # 21 days
CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL = 2592000  # 30 days
CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL = 94608000  # 1095 days (~3 years)
CIRCUIT_BREAKER_HEARTBEAT_INTERVAL = 31536000  # 1 year (365 days)

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
RESEAL_MANAGER = "0x7914b5a1539b97Bd0bbd155757F25FD79A522d24"

# Operational items
CURATED_MODULE = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
STETH_TRANSFER_MAX_DELTA = 2
ETH_WHALE = "0x00000000219ab540356cBB839Cbe05303d7705Fa"

ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

LOL_ALLOWED_RECIPIENTS_REGISTRY = "0x48c4929630099b217136b64089E8543dB0E5163a"
LOL_OLD_LIMIT = 6000 * 10**18
LOL_NEW_LIMIT = 8000 * 10**18
LOL_PERIOD_DURATION_MONTHS = 6
LOL_PERIOD_START = 1767225600  # 2026-01-01 00:00:00 UTC
LOL_PERIOD_END = 1782864000  # 2026-07-01 00:00:00 UTC
LOL_TRUSTED_CALLER = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
LOL_TOP_UP_FACTORY = "0x1F2b79FE297B7098875930bBA6dd17068103897E"

PIER_TWO_NO_ID = 36
PIER_TWO_NAME_OLD = "Pier Two"
PIER_TWO_NAME_NEW = "MAVAN"

CHORUS_ONE_NO_ID = 3
CHORUS_ONE_NAME = "Chorus One"
CURATED_MODULE_ACTIVE_NO_COUNT_BEFORE = 36
CURATED_MODULE_TOTAL_NO_COUNT = 39

# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 202
EXPECTED_DG_PROPOSAL_ID = 11
EXPECTED_VOTE_EVENTS_COUNT = 1

# Per migration (one pausable each): revoke PAUSE_ROLE, grant PAUSE_ROLE, registerPauser.
# Plus 3 operational items: 1.34 LOL Easy Track limit increase, 1.35 Node Operator rename, 1.36 Node Operator deactivation.
# 11 migrations * 3 + 3 operational = 36.
EXPECTED_DG_EVENTS_FROM_AGENT = 36
EXPECTED_DG_EVENTS_COUNT = EXPECTED_DG_EVENTS_FROM_AGENT

IPFS_DESCRIPTION_HASH = "bafkreiailinuihhlknzfct7tjgrxg5bvoijsxyz3wcdvf66vabufovm4te"


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
    easy_track = interface.EasyTrack(EASYTRACK)

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
            proposal_id=(
                EXPECTED_DG_PROPOSAL_ID if EXPECTED_DG_PROPOSAL_ID is not None else timelock.getProposalsCount()
            ),
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

        # 1.1-1.33. CircuitBreaker migration
        for target in MIGRATION_TARGETS:
            pausable = interface.IPausableUntilWithRoles(target.pausable)
            pause_role_hash = str(pausable.PAUSE_ROLE())

            assert not pausable.hasRole(
                pause_role_hash, CIRCUIT_BREAKER
            ), f"CircuitBreaker should not have PAUSE_ROLE on {pausable.address} before DG enactment"
            assert (
                circuit_breaker.getPauser(pausable.address) == ZERO_ADDRESS
            ), f"CircuitBreaker should not have a pauser for {pausable.address} before DG enactment"

            assert pausable.hasRole(
                pause_role_hash, target.gate_seal
            ), f"GateSeal {target.gate_seal} should hold PAUSE_ROLE on {pausable.address} before DG enactment"

        validate_circuit_breaker_globals(circuit_breaker)

        # 1.34. LOL config before enactment
        # we can't predict the spendable before (state can change before the vote, so here we just pass the current value)
        _, lol_spendable_before, _, _ = lol_registry.getPeriodState()
        validate_lol_config(lol_registry, LOL_OLD_LIMIT, lol_spendable_before)

        # 1.35. Node Operator name before enactment.
        assert (
            curated_module.getNodeOperator(PIER_TWO_NO_ID, True)["name"] == PIER_TWO_NAME_OLD
        ), f"Node Operator {PIER_TWO_NO_ID} name before DG enactment should be {PIER_TWO_NAME_OLD}"

        # 1.36. Node Operator Chorus One active before enactment.
        chorus_one_before = curated_module.getNodeOperator(CHORUS_ONE_NO_ID, True)
        assert (
            chorus_one_before["name"] == CHORUS_ONE_NAME
        ), f"Node Operator {CHORUS_ONE_NO_ID} name before DG enactment should be {CHORUS_ONE_NAME}"
        assert chorus_one_before[
            "active"
        ], f"Node Operator {CHORUS_ONE_NO_ID} ({CHORUS_ONE_NAME}) should be active before DG enactment"
        assert (
            curated_module.getActiveNodeOperatorsCount() == CURATED_MODULE_ACTIVE_NO_COUNT_BEFORE
        ), f"Active node operators count before DG enactment should be {CURATED_MODULE_ACTIVE_NO_COUNT_BEFORE}"
        assert (
            curated_module.getNodeOperatorsCount() == CURATED_MODULE_TOTAL_NO_COUNT
        ), f"Total node operators count should be {CURATED_MODULE_TOTAL_NO_COUNT}"

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
            validate_set_limit_parameter_event(
                dg_events[event_index],
                limit=LOL_NEW_LIMIT,
                period_duration_month=LOL_PERIOD_DURATION_MONTHS,
                period_start_timestamp=LOL_PERIOD_START,
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

            # 1.36. Deactivate Node Operator Chorus One
            validate_node_operator_deactivated(
                dg_events[event_index],
                CHORUS_ONE_NO_ID,
                emitted_by=CURATED_MODULE,
            )
            event_index += 1

        # =====================================================================
        # ================ After DG proposal executed checks ==================
        # =====================================================================
        # This block is only reached when the proposal was executed.
        # This assert shouldn't fire; it's only here to narrow Optional[int] -> int for the type checker.
        assert dg_execution_timestamp is not None, "DG proposal was not executed in this run"

        # 1.1-1.33. CircuitBreaker migration
        expected_pausables = {t.pausable.lower() for t in MIGRATION_TARGETS}
        on_chain_pausables = {addr.lower() for addr in circuit_breaker.getPausables()}
        assert (
            on_chain_pausables == expected_pausables
        ), f"CircuitBreaker.getPausables() mismatch: expected {expected_pausables}, got {on_chain_pausables}"

        expected_pausable_counts = {}
        for t in MIGRATION_TARGETS:
            expected_pausable_counts[t.pauser.lower()] = expected_pausable_counts.get(t.pauser.lower(), 0) + 1

        for target in MIGRATION_TARGETS:
            pausable = interface.IPausableUntilWithRoles(target.pausable)
            pause_role_hash = str(pausable.PAUSE_ROLE())

            assert not pausable.hasRole(
                pause_role_hash, target.gate_seal
            ), f"GateSeal {target.gate_seal} should not have PAUSE_ROLE on {pausable.address} after vote"
            assert pausable.hasRole(
                pause_role_hash, CIRCUIT_BREAKER
            ), f"CircuitBreaker should have PAUSE_ROLE on {pausable.address} after vote"
            assert (
                pausable.getRoleMemberCount(pause_role_hash) == 2
            ), f"{pausable.address} should have exactly 2 PAUSE_ROLE holders after vote"
            assert {
                pausable.getRoleMember(pause_role_hash, 0).lower(),
                pausable.getRoleMember(pause_role_hash, 1).lower(),
            } == {
                CIRCUIT_BREAKER.lower(),
                RESEAL_MANAGER.lower(),
            }, f"{pausable.address} PAUSE_ROLE holders do not match {{CircuitBreaker, ResealManager}}"

            assert (
                circuit_breaker.getPauser(pausable.address).lower() == target.pauser.lower()
            ), f"CircuitBreaker pauser for {pausable.address} should be {target.pauser} after vote"

        # Per-pauser checks (deduped)
        for pauser, expected_count in expected_pausable_counts.items():
            assert circuit_breaker.getPausableCount(pauser) == expected_count, f"getPausableCount mismatch for {pauser}"
            assert circuit_breaker.isPauserLive(pauser), f"{pauser} should be live after vote"
            assert circuit_breaker.heartbeatExpiry(pauser) == (
                dg_execution_timestamp + CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
            ), f"heartbeatExpiry({pauser}) should equal DG execution timestamp + heartbeat interval"

        # CircuitBreaker config must NOT change
        validate_circuit_breaker_globals(circuit_breaker)

        # Happy path: each pauser can pause its pausable through the CircuitBreaker.
        circuit_breaker_pause_happy_path_test(circuit_breaker, accounts)

        # 1.34. LOL limit raised; spent untouched, spendable grew by exactly the limit delta.
        validate_lol_config(lol_registry, LOL_NEW_LIMIT, lol_spendable_before + (LOL_NEW_LIMIT - LOL_OLD_LIMIT))

        # Happy path: the new 8,000 stETH / 6-month budget is spendable and the limit is enforced.
        lol_limit_happy_path_test(easy_track, lol_registry, stranger, accounts)

        # 1.35. Node Operator name changed to MAVAN.
        assert (
            curated_module.getNodeOperator(PIER_TWO_NO_ID, True)["name"] == PIER_TWO_NAME_NEW
        ), f"Node Operator {PIER_TWO_NO_ID} name after vote should be {PIER_TWO_NAME_NEW}"

        # 1.36. Node Operator Chorus One deactivated.
        chorus_one_after = curated_module.getNodeOperator(CHORUS_ONE_NO_ID, True)
        assert not chorus_one_after[
            "active"
        ], f"Node Operator {CHORUS_ONE_NO_ID} ({CHORUS_ONE_NAME}) should be inactive after vote"
        assert (
            chorus_one_after["name"] == CHORUS_ONE_NAME
        ), f"Node Operator {CHORUS_ONE_NO_ID} name should be unchanged after deactivation"
        assert (
            curated_module.getActiveNodeOperatorsCount() == CURATED_MODULE_ACTIVE_NO_COUNT_BEFORE - 1
        ), "Active node operators count should decrease by exactly 1 after deactivation"
        assert (
            curated_module.getNodeOperatorsCount() == CURATED_MODULE_TOTAL_NO_COUNT
        ), "Total node operators count should be unchanged after deactivation"


# ============================================================================
# ============================ Happy path tests ================================
# ============================================================================


def validate_circuit_breaker_globals(circuit_breaker):
    assert circuit_breaker.ADMIN() == AGENT
    assert circuit_breaker.pauseDuration() == CIRCUIT_BREAKER_PAUSE_DURATION
    assert circuit_breaker.heartbeatInterval() == CIRCUIT_BREAKER_HEARTBEAT_INTERVAL
    assert circuit_breaker.MIN_PAUSE_DURATION() == CIRCUIT_BREAKER_MIN_PAUSE_DURATION
    assert circuit_breaker.MAX_PAUSE_DURATION() == CIRCUIT_BREAKER_MAX_PAUSE_DURATION
    assert circuit_breaker.MIN_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MIN_HEARTBEAT_INTERVAL
    assert circuit_breaker.MAX_HEARTBEAT_INTERVAL() == CIRCUIT_BREAKER_MAX_HEARTBEAT_INTERVAL


def validate_lol_config(lol_registry, expected_limit, expected_spendable):
    limit, period_duration = lol_registry.getLimitParameters()
    assert limit == expected_limit, f"LOL limit should be {expected_limit}, got {limit}"
    assert (
        period_duration == LOL_PERIOD_DURATION_MONTHS
    ), f"LOL period duration should be {LOL_PERIOD_DURATION_MONTHS}, got {period_duration}"

    spent, spendable, period_start, period_end = lol_registry.getPeriodState()
    assert spendable == expected_spendable, f"LOL spendable should be {expected_spendable}, got {spendable}"
    assert (
        spent == expected_limit - expected_spendable
    ), f"LOL already-spent should be {expected_limit - expected_spendable}, got {spent}"
    assert period_start == LOL_PERIOD_START, f"LOL period start should be {LOL_PERIOD_START}, got {period_start}"
    assert period_end == LOL_PERIOD_END, f"LOL period end should be {LOL_PERIOD_END}, got {period_end}"


def circuit_breaker_pause_happy_path_test(circuit_breaker, accounts):
    chain.snapshot()
    for target in MIGRATION_TARGETS:
        pausable = interface.IPausableUntilWithRoles(target.pausable)
        assert not pausable.isPaused(), f"{pausable.address} should not be paused before happy-path pause"

        pauser = accounts.at(target.pauser, force=True)
        tx = circuit_breaker.pause(target.pausable, {"from": pauser})

        assert pausable.isPaused(), f"{pausable.address} should be paused after CircuitBreaker.pause"
        assert (
            pausable.getResumeSinceTimestamp() == tx.timestamp + CIRCUIT_BREAKER_PAUSE_DURATION
        ), f"{pausable.address} resume-since timestamp should be tx.timestamp + pauseDuration"
    chain.revert()


def lol_limit_happy_path_test(easy_track, registry, stranger, accounts):
    chain.snapshot()
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    steth = interface.StETH(STETH)
    top_up_factory = interface.TopUpAllowedRecipients(LOL_TOP_UP_FACTORY)

    # Fast-forward to the start of a fresh spending period before exercising the budget.
    # Because enacting the motions moves the chain time and can roll over to the next period
    _, _, _, period_end = registry.getPeriodState()
    now_ts = web3.eth.get_block("latest")["timestamp"]
    chain.mine(1, max(now_ts, period_end) + 1)

    spendable_left = 10  # wei — leave a tiny remainder to verify the post-spend state
    to_spend = LOL_NEW_LIMIT - spendable_left

    prepare_agent_for_steth_payment(LOL_NEW_LIMIT, accounts)
    bump_create_payments_role_steth_cap(LOL_NEW_LIMIT, accounts)

    # 1) we can spend the entire budget for the fresh period (this also rolls the period over)
    create_and_enact_payment_motion(
        easy_track,
        multisig,
        top_up_factory,
        steth,
        [multisig],
        [to_spend],
        stranger,
    )

    spent_after, spendable_after, _, new_period_end = registry.getPeriodState()
    assert new_period_end > period_end, "spending period should have rolled over to a fresh one"
    assert spent_after == to_spend
    assert spendable_after == spendable_left

    # 2) we cannot spend more than what remains in the current period
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            multisig,
            top_up_factory,
            steth,
            [multisig],
            [spendable_left + 1],
            stranger,
        )

    chain.revert()


def bump_create_payments_role_steth_cap(max_per_call: int, accounts) -> None:
    """Re-grant CREATE_PAYMENTS_ROLE to the EVM_SCRIPT_EXECUTOR with a stETH per-call cap that fits
    the new period budget, so the whole budget can be spent in a single motion.
    """
    acl = interface.ACL(ACL)
    create_payments_role = web3.keccak(text="CREATE_PAYMENTS_ROLE")
    perm_manager = acl.getPermissionManager(FINANCE, create_payments_role)
    steth_only_amount_limits = [
        # token == stETH
        Param(0, Op.EQ, ArgumentValue(STETH)),
        # amount <= max_per_call
        Param(2, Op.LTE, ArgumentValue(max_per_call)),
    ]
    acl.grantPermissionP(
        EVM_SCRIPT_EXECUTOR,
        FINANCE,
        create_payments_role,
        encode_permission_params(steth_only_amount_limits),
        {"from": accounts.at(perm_manager, force=True)},
    )


def prepare_agent_for_steth_payment(amount: int, accounts) -> None:
    """Ensure the Agent holds at least `amount` stETH."""
    steth = interface.StETH(STETH)
    if steth.balanceOf(AGENT) < amount:
        eth_whale = accounts.at(ETH_WHALE, force=True)
        steth.submit(ZERO_ADDRESS, {"from": eth_whale, "value": amount + 2 * STETH_TRANSFER_MAX_DELTA})
        steth.transfer(AGENT, amount + STETH_TRANSFER_MAX_DELTA, {"from": eth_whale})
    assert steth.balanceOf(AGENT) >= amount, "Insufficient stETH balance on Agent"
