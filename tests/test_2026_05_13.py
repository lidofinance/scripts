from brownie import chain, interface, reverts, web3
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
from utils.permission_parameters import (
    Param,
    Op,
    ArgumentValue,
    SpecialArgumentID,
    encode_argument_value_if,
    encode_permission_params,
)
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grantp_event,
    validate_grant_role_event,
    validate_revoke_role_event,
)
from utils.test.event_validators.time_constraints import (
    validate_dg_time_constraints_executed_within_day_time_event,
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.balance import set_balance

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.config import contracts
from utils.test.oracle_report_helpers import (
    wait_to_next_available_report_time,
    reach_consensus,
    prepare_exit_bus_report,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2026_05_13 import (
    start_vote,
    get_vote_items,
    get_dg_items,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

# Lido addresses
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
ACL = "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EASYTRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
NODE_OPERATORS_REGISTRY = "0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
EMERGENCY_ACTIVATION_COMMITTEE = "0x8B7854488Fde088d686Ea672B6ba1A5242515f45"  # configs/config_mainnet.py:429
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

# 1.1. Emergency Protection end date
EMERGENCY_PROTECTION_END_DATE_BEFORE = 1781913600  # 2026-05-19 00:00:00 UTC
EMERGENCY_PROTECTION_END_DATE_AFTER = 1813449600  # 2027-06-20 00:00:00 UTC

# 1.2. Grant MANAGE_SIGNING_KEYS for Consensys (NO ID = 21)
CONSENSYS_NO_ID = 21
CONSENSYS_NEW_MANAGER = "0xF45C77EadD434612fCD93db978B3E36B0D58eC99"
MANAGE_SIGNING_KEYS_HASH = web3.keccak(text="MANAGE_SIGNING_KEYS").hex()

# 1.3. Raise Alliance Ops stablecoins Easy Track limit
ALLIANCE_OPS_STABLECOINS_REGISTRY = "0x3B525F4c059F246Ca4aa995D21087204F30c9E2F"
ALLIANCE_OPS_TOP_UP_FACTORY = "0xe5656eEe7eeD02bdE009d77C88247BC8271e26Eb"
ALLIANCE_OPS_TRUSTED_CALLER = "0x606f77BF3dd6Ed9790D9771C7003f269a385D942"
ALLIANCE_OPS_LIMIT_BEFORE = 250_000 * 10**18
ALLIANCE_OPS_PERIOD_DURATION_MONTHS_BEFORE = 3
ALLIANCE_OPS_LIMIT_AFTER = 5_000_000 * 10**18
ALLIANCE_OPS_PERIOD_DURATION_MONTHS_AFTER = 6
ALLIANCE_OPS_PERIOD_START_AFTER = 1767225600  # Thu Jan 01 2026 00:00:00 GMT+0000
ALLIANCE_OPS_PERIOD_END_AFTER = 1782864000  # Wed Jul 01 2026 00:00:00 GMT+0000
DAI_TOKEN = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
DAI_WARD = "0x9759A6Ac90977b93B58547b4A71c78317f391A28"  # authorized DAI minter, used to fund the Agent on a fork
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

# 1.4 - 1.6. Change the number of epochs in the VEBO reporting frame
VEBO_HASH_CONSENSUS = "0x7FaDB6358950c5fAA66Cb5EB8eE5147De3df355a"
VEBO_NEW_EPOCHS_PER_FRAME = 45
MANAGE_FRAME_CONFIG_ROLE = "0x921f40f434e049d23969cbe68d9cf3ac1013fbe8945da07963af6f3142de6afe"

# 1.7. Set time window constraint
DUAL_GOVERNANCE_TIME_CONSTRAINTS = "0x2a30F5aC03187674553024296bed35Aa49749DDa"
TIME_WINDOW_FROM = 13 * 3600
TIME_WINDOW_TO = 16.5 * 3600


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 201
EXPECTED_DG_PROPOSAL_ID = 10
EXPECTED_VOTE_EVENTS_COUNT = 1  # 1 DG submit
EXPECTED_DG_EVENTS_COUNT = 7  # 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
EXPECTED_DG_EVENTS_FROM_AGENT = 5  # 1.2 + 1.3 + 1.4 + 1.5 + 1.6
IPFS_DESCRIPTION_HASH = "bafkreibs4p67ee62vmgrlks2qmkacyvg75mf2uaba2isjsnqhjzkivqkpy"
DG_PROPOSAL_METADATA = (
    "Extend Dual Governance Emergency Protection until June 20 2027, "
    "grant MANAGE_SIGNING_KEYS role to Node Operator Consensys, "
    "increase limit from $250K per 3 months to $5M per 6 months on Alliance Ops stablecoins Easy Track factory, "
    "reduce VEBO Reporting Frame from 75 to 45 epochs"
)


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items()

    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item
        proposal_calls.append({"target": target, "value": 0, "data": data})

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    nor = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    alliance_ops_registry = interface.AllowedRecipientRegistry(ALLIANCE_OPS_STABLECOINS_REGISTRY)
    vebo_hash_consensus = interface.HashConsensus(VEBO_HASH_CONSENSUS)
    agent = interface.Agent(AGENT)
    acl = interface.ACL(ACL)
    easy_track = interface.EasyTrack(EASYTRACK)

    consensys_perm_param = Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID))
    consensys_perm_param_uint = consensys_perm_param.to_uint256()
    other_no_perm_param_uint = Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID + 1)).to_uint256()

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

            # DG submit event
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata=DG_PROPOSAL_METADATA,
                proposal_calls=dual_governance_proposal_calls,
            )

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # 1.1. Emergency Protection end date — current value before DG execution
            protection_details_before_dg = timelock.getEmergencyProtectionDetails()
            assert protection_details_before_dg["emergencyProtectionEndsAfter"] == EMERGENCY_PROTECTION_END_DATE_BEFORE
            # Emergency Activation Committee can veto just before the old end date
            emergency_committee_can_veto_at(EMERGENCY_PROTECTION_END_DATE_BEFORE - 1, accounts)
            # Emergency Activation Committee cannot veto past the old end date
            emergency_committee_cannot_veto_at(EMERGENCY_PROTECTION_END_DATE_BEFORE + 1, accounts)

            # 1.2. Consensys cannot manage signing keys yet
            assert not acl.hasPermission["address,address,bytes32,uint[]"](
                CONSENSYS_NEW_MANAGER, NODE_OPERATORS_REGISTRY, MANAGE_SIGNING_KEYS_HASH, [consensys_perm_param_uint]
            )
            assert not nor.canPerform(CONSENSYS_NEW_MANAGER, MANAGE_SIGNING_KEYS_HASH, [consensys_perm_param_uint])
            add_signing_keys_fails_for_consensys_manager(accounts)

            # 1.3. Alliance Ops registry — current limit before DG execution
            assert alliance_ops_registry.getLimitParameters() == (
                ALLIANCE_OPS_LIMIT_BEFORE,
                ALLIANCE_OPS_PERIOD_DURATION_MONTHS_BEFORE,
            )
            spent_before_dg, spendable_before_dg, _, _ = alliance_ops_registry.getPeriodState()

            # 1.4 - 1.6. VEBO frame config before DG execution
            (_, epochs_per_frame_before, fast_lane_length_slots) = vebo_hash_consensus.getFrameConfig()
            assert epochs_per_frame_before != VEBO_NEW_EPOCHS_PER_FRAME
            assert epochs_per_frame_before == 75  # Current frame size
            assert not vebo_hash_consensus.hasRole(MANAGE_FRAME_CONFIG_ROLE, AGENT)

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)
                chain.mine()

                # 1.7. Time constraints window before DG execution
                # Check DG execution reverts with DayTimeOutOfRange outside [13:00, 16:30] window
                day_start = (chain.time() // 86400 + 1) * 86400
                out_of_range_time = 12 * 3600
                chain.mine(timestamp=day_start + out_of_range_time)  # 12:00 UTC

                with reverts(f"DayTimeOutOfRange: {out_of_range_time + 1}, {int(TIME_WINDOW_FROM)}, {int(TIME_WINDOW_TO)}"):
                    timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})

                # Move to 14:00 UTC to allow execution
                chain.mine(timestamp=day_start + 16 * 3600)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": DUAL_GOVERNANCE_ADMIN_EXECUTOR})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT

                # 1.1. EmergencyProtectionEndDateSet emitted by the EPT itself (direct call from admin executor)
                validate_events_chain(
                    [e.name for e in dg_events[0]],
                    ["EmergencyProtectionEndDateSet", "Executed"],
                )
                assert dg_events[0].count("EmergencyProtectionEndDateSet") == 1
                assert (
                    dg_events[0]["EmergencyProtectionEndDateSet"]["newEmergencyProtectionEndDate"]
                    == EMERGENCY_PROTECTION_END_DATE_AFTER
                )
                assert (
                    web3.to_checksum_address(dg_events[0]["EmergencyProtectionEndDateSet"]["_emitted_by"])
                    == web3.to_checksum_address(EMERGENCY_PROTECTED_TIMELOCK)
                )

                # 1.2. SetPermission + SetPermissionParams emitted by ACL via Agent.forward
                validate_permission_grantp_event(
                    dg_events[1],
                    Permission(
                        entity=CONSENSYS_NEW_MANAGER,
                        app=NODE_OPERATORS_REGISTRY,
                        role=MANAGE_SIGNING_KEYS_HASH,
                    ),
                    [consensys_perm_param],
                    emitted_by=ACL,
                )

                # 1.3. LimitsParametersChanged emitted by the Alliance Ops registry via Agent.forward
                _, _, alliance_ops_period_start_after, _ = alliance_ops_registry.getPeriodState()
                validate_set_limit_parameter_event(
                    dg_events[2],
                    limit=ALLIANCE_OPS_LIMIT_AFTER,
                    period_duration_month=ALLIANCE_OPS_PERIOD_DURATION_MONTHS_AFTER,
                    period_start_timestamp=alliance_ops_period_start_after,
                    emitted_by=ALLIANCE_OPS_STABLECOINS_REGISTRY,
                )

                # 1.4. GrantRole(MANAGE_FRAME_CONFIG_ROLE, ARAGON_AGENT)
                validate_grant_role_event(
                    dg_events[3],
                    role=MANAGE_FRAME_CONFIG_ROLE,
                    grant_to=AGENT,
                    sender=AGENT,
                    emitted_by=VEBO_HASH_CONSENSUS,
                )

                # 1.5. SetFrameConfig(45, fast_lane_length_slots)
                validate_events_chain(
                    [e.name for e in dg_events[4]],
                    ['LogScriptCall', 'FrameConfigSet', 'ScriptResult', 'Executed'],
                )
                assert dg_events[4]["FrameConfigSet"]["newInitialEpoch"] % 225 == 0
                assert dg_events[4]["FrameConfigSet"]["newEpochsPerFrame"] == VEBO_NEW_EPOCHS_PER_FRAME
                assert web3.to_checksum_address(dg_events[4]["FrameConfigSet"]["_emitted_by"]) == web3.to_checksum_address(
                    VEBO_HASH_CONSENSUS
                )

                # 1.6. RevokeRole(MANAGE_FRAME_CONFIG_ROLE, ARAGON_AGENT)
                validate_revoke_role_event(
                    dg_events[5],
                    role=MANAGE_FRAME_CONFIG_ROLE,
                    revoke_from=AGENT,
                    sender=AGENT,
                    emitted_by=VEBO_HASH_CONSENSUS,
                )

                # 1.7. TimeWithinDayTimeChecked
                validate_dg_time_constraints_executed_within_day_time_event(
                    dg_events[6],
                    start_day_time=TIME_WINDOW_FROM,
                    end_day_time=TIME_WINDOW_TO,
                    emitted_by=DUAL_GOVERNANCE_TIME_CONSTRAINTS,
                )

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # 1.1. Emergency Protection end date extended by one year
        protection_details_after_dg = timelock.getEmergencyProtectionDetails()
        assert protection_details_after_dg["emergencyProtectionEndsAfter"] == EMERGENCY_PROTECTION_END_DATE_AFTER
        # Emergency Activation Committee can veto just before the old end date (still inside the original window)
        emergency_committee_can_veto_at(EMERGENCY_PROTECTION_END_DATE_BEFORE - 1, accounts)
        # Emergency Activation Committee can veto in the gap between the old and new end dates —
        emergency_committee_can_veto_at(EMERGENCY_PROTECTION_END_DATE_BEFORE + 1, accounts)
        # Emergency Activation Committee cannot veto past the new end date
        emergency_committee_cannot_veto_at(EMERGENCY_PROTECTION_END_DATE_AFTER + 1, accounts)

        # 1.2. Consensys can manage signing keys for operator 21 only — param restriction holds
        assert acl.hasPermission["address,address,bytes32,uint[]"](
            CONSENSYS_NEW_MANAGER, NODE_OPERATORS_REGISTRY, MANAGE_SIGNING_KEYS_HASH, [consensys_perm_param_uint]
        )
        assert not acl.hasPermission["address,address,bytes32,uint[]"](
            CONSENSYS_NEW_MANAGER, NODE_OPERATORS_REGISTRY, MANAGE_SIGNING_KEYS_HASH, [other_no_perm_param_uint]
        )
        assert nor.canPerform(CONSENSYS_NEW_MANAGER, MANAGE_SIGNING_KEYS_HASH, [consensys_perm_param_uint])
        assert not nor.canPerform(CONSENSYS_NEW_MANAGER, MANAGE_SIGNING_KEYS_HASH, [other_no_perm_param_uint])
        consensys_manager_adds_signing_keys(accounts)
        add_signing_keys_to_other_no_fails(accounts)

        # 1.3. Alliance Ops limit raised to 5,000,000 stETH per 6 months
        assert alliance_ops_registry.getLimitParameters() == (
            ALLIANCE_OPS_LIMIT_AFTER,
            ALLIANCE_OPS_PERIOD_DURATION_MONTHS_AFTER,
        )
        spent_after_dg, spendable_after_dg, period_start_after_dg, period_end_after_dg = (
            alliance_ops_registry.getPeriodState()
        )
        assert spent_after_dg == spent_before_dg
        assert spendable_after_dg == spendable_before_dg + (ALLIANCE_OPS_LIMIT_AFTER - ALLIANCE_OPS_LIMIT_BEFORE)
        assert period_start_after_dg == ALLIANCE_OPS_PERIOD_START_AFTER
        assert period_end_after_dg == ALLIANCE_OPS_PERIOD_END_AFTER
        alliance_ops_limit_test(easy_track, alliance_ops_registry, stranger, accounts)

        # 1.4 - 1.6. VEBO frame config after DG execution
        (initial_epoch, epochs_per_frame_after, fast_lane_length_slots_after) = vebo_hash_consensus.getFrameConfig()
        assert initial_epoch % 225 == 0
        assert epochs_per_frame_after == VEBO_NEW_EPOCHS_PER_FRAME
        assert fast_lane_length_slots_after == fast_lane_length_slots
        assert not vebo_hash_consensus.hasRole(MANAGE_FRAME_CONFIG_ROLE, AGENT)

        send_vebo_report_in_45_epoches(helpers)



# ============================================================================
# ============================ Scenario tests ================================
# ============================================================================


def add_signing_keys_fails_for_consensys_manager(accounts):
    """Pre-vote scenario: Consensys's new manager cannot add signing keys before the role is granted."""
    nor = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    manager = accounts.at(CONSENSYS_NEW_MANAGER, force=True)
    set_balance(manager, 10)
    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)
    with reverts():
        nor.addSigningKeys(CONSENSYS_NO_ID, 1, pubkeys, signatures, {"from": manager})


def consensys_manager_adds_signing_keys(accounts):
    """Post-DG scenario: Consensys's new manager adds a signing key for NO 21."""
    nor = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    manager = accounts.at(CONSENSYS_NEW_MANAGER, force=True)
    set_balance(manager, 10)
    total_keys_before = nor.getTotalSigningKeyCount(CONSENSYS_NO_ID)
    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)
    nor.addSigningKeys(CONSENSYS_NO_ID, 1, pubkeys, signatures, {"from": manager})
    assert nor.getTotalSigningKeyCount(CONSENSYS_NO_ID) == total_keys_before + 1


def add_signing_keys_to_other_no_fails(accounts):
    """Post-DG scenario: param restriction holds — Consensys's manager cannot manage other NOs."""
    nor = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    manager = accounts.at(CONSENSYS_NEW_MANAGER, force=True)
    set_balance(manager, 10)
    pubkeys = random_pubkeys_batch(1)
    signatures = random_signatures_batch(1)
    other_no_id = CONSENSYS_NO_ID + 1
    with reverts():
        nor.addSigningKeys(other_no_id, 1, pubkeys, signatures, {"from": manager})


def alliance_ops_limit_test(easy_track, registry, stranger, accounts):
    """Post-DG scenario: spend down to a small remainder under the new 5M / 6-month limit and
    assert the next motion that would exceed the spendable balance reverts.
    """
    chain.snapshot()
    multisig = accounts.at(ALLIANCE_OPS_TRUSTED_CALLER, force=True)
    dai_token = interface.ERC20(DAI_TOKEN)

    spent_at_entry, spendable_at_entry, _, _ = registry.getPeriodState()
    spendable_left = 10  # wei — leave a tiny remainder to verify the post-spend state
    to_spend = spendable_at_entry - spendable_left

    prepare_agent_for_dai_payment(spendable_at_entry, accounts)
    bump_create_payments_role_dai_cap(spendable_at_entry, accounts)

    # 1) we can spend the entire remaining budget for the current period
    create_and_enact_payment_motion(
        easy_track,
        ALLIANCE_OPS_TRUSTED_CALLER,
        ALLIANCE_OPS_TOP_UP_FACTORY,
        dai_token,
        [multisig],
        [to_spend],
        stranger,
    )

    spent_after, spendable_after, _, _ = registry.getPeriodState()
    assert spent_after == spent_at_entry + to_spend
    assert spendable_after == spendable_left

    # 2) we cannot spend more than what remains in the current period
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            ALLIANCE_OPS_TRUSTED_CALLER,
            ALLIANCE_OPS_TOP_UP_FACTORY,
            dai_token,
            [multisig],
            [spendable_left + 1],
            stranger,
        )

    chain.revert()


def prepare_agent_for_dai_payment(amount: int, accounts) -> None:
    dai = interface.Dai(DAI_TOKEN)
    if dai.balanceOf(AGENT) < amount:
        dai_ward = accounts.at(DAI_WARD, force=True)
        dai.mint(AGENT, amount, {"from": dai_ward})
    assert dai.balanceOf(AGENT) >= amount


def bump_create_payments_role_dai_cap(max_per_call: int, accounts) -> None:
    """Re-grant CREATE_PAYMENTS_ROLE to the EVM_SCRIPT_EXECUTOR with a DAI per-call cap that fits
    the new period budget.
    """
    acl = interface.ACL(ACL)
    create_payments_role = web3.keccak(text="CREATE_PAYMENTS_ROLE")
    perm_manager = acl.getPermissionManager(FINANCE, create_payments_role)
    dai_only_amount_limits = [
        # if (token == DAI) then (amount <= max_per_call) else (deny)
        Param(
            SpecialArgumentID.LOGIC_OP_PARAM_ID,
            Op.IF_ELSE,
            encode_argument_value_if(condition=1, success=2, failure=3),
        ),
        Param(0, Op.EQ, ArgumentValue(DAI_TOKEN)),
        Param(2, Op.LTE, ArgumentValue(max_per_call)),
        Param(SpecialArgumentID.PARAM_VALUE_PARAM_ID, Op.RET, ArgumentValue(0)),
    ]
    acl.grantPermissionP(
        EVM_SCRIPT_EXECUTOR,
        FINANCE,
        create_payments_role,
        encode_permission_params(dai_only_amount_limits),
        {"from": accounts.at(perm_manager, force=True)},
    )


def emergency_committee_can_veto_at(timestamp: int, accounts) -> None:
    """Snapshot, fast-forward to `timestamp` (if in the future), then assert the Emergency Activation
    Committee can call activateEmergencyMode.
    """
    chain.snapshot()
    if timestamp > chain.time():
        chain.sleep(timestamp - chain.time())
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    committee = accounts.at(EMERGENCY_ACTIVATION_COMMITTEE, force=True)
    set_balance(committee, 10)
    assert not timelock.isEmergencyModeActive()
    timelock.activateEmergencyMode({"from": committee})
    assert timelock.isEmergencyModeActive()
    chain.revert()


def emergency_committee_cannot_veto_at(timestamp: int, accounts) -> None:
    """Snapshot, fast-forward to `timestamp`, then assert activateEmergencyMode reverts because the
    Emergency Protection has expired (timestamp >= emergencyProtectionEndsAfter).
    """
    chain.snapshot()
    if timestamp > chain.time():
        chain.sleep(timestamp - chain.time())
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    committee = accounts.at(EMERGENCY_ACTIVATION_COMMITTEE, force=True)
    set_balance(committee, 10)
    assert not timelock.isEmergencyModeActive()
    with reverts():  # EmergencyProtectionExpired(protectedTill)
        timelock.activateEmergencyMode({"from": committee})
    chain.revert()


def send_vebo_report_in_45_epoches(helpers):
    wait_to_next_available_report_time(contracts.hash_consensus_for_validators_exit_bus_oracle)
    ref_slot, _ = contracts.hash_consensus_for_validators_exit_bus_oracle.getCurrentFrame()
    report, report_hash = prepare_exit_bus_report([], ref_slot)

    consensus_version = contracts.validators_exit_bus_oracle.getConsensusVersion()
    contract_version = contracts.validators_exit_bus_oracle.getContractVersion()

    submitter = reach_consensus(
        ref_slot, report_hash, consensus_version, contracts.hash_consensus_for_validators_exit_bus_oracle
    )

    tx = contracts.validators_exit_bus_oracle.submitReportData(report, contract_version, {"from": submitter})

    helpers.assert_single_event_named("ProcessingStarted", tx, {"refSlot": ref_slot, "hash": report_hash.hex()})

    assert contracts.validators_exit_bus_oracle.getLastProcessingRefSlot() == ref_slot
    # Make sure this is first report after enactment in 45 epoches after prev slot
    assert (ref_slot + 1) // 32 % 225 == VEBO_NEW_EPOCHS_PER_FRAME
