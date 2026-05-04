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
from utils.permission_parameters import Param, Op, ArgumentValue
from utils.test.event_validators.allowed_recipients_registry import validate_set_limit_parameter_event
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.permission import Permission, validate_permission_grantp_event
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.balance import set_balance

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


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
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

# 1.1. Emergency Protection end date
EMERGENCY_PROTECTION_END_DATE_BEFORE = 1781913600  # 2026-05-19 00:00:00 UTC
EMERGENCY_PROTECTION_END_DATE_AFTER = 1813449600  # 2027-05-19 00:00:00 UTC

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


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 201
EXPECTED_DG_PROPOSAL_ID = 10
EXPECTED_VOTE_EVENTS_COUNT = 1  # 1 DG submit
EXPECTED_DG_EVENTS_COUNT = 3  # 1.1 + 1.2 + 1.3
EXPECTED_DG_EVENTS_FROM_AGENT = 2  # 1.2 + 1.3 (1.1 is direct, no agent_forward)
IPFS_DESCRIPTION_HASH = "bafkreiabxjdrtsaln7urdmeru7afcjfwj3xm5fsobhafr34ptac5vssunm"
DG_PROPOSAL_METADATA = (
    "Extend DG Emergency Protection by one year, "
    "grant MANAGE_SIGNING_KEYS for Consensys (NO ID = 21), and "
    "raise Alliance Ops stablecoins Easy Track limit to 5M stETH / 6 months"
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
    agent = interface.Agent(AGENT)
    acl = interface.ACL(ACL)

    consensys_perm_param = Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID))
    consensys_perm_param_uint = consensys_perm_param.to_uint256()
    other_no_perm_param_uint = Param(0, Op.EQ, ArgumentValue(CONSENSYS_NO_ID + 1)).to_uint256()

    alliance_ops_spent_before = None  # captured in the DG-before block when first-running the test

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
            alliance_ops_spent_before, _, _, _ = alliance_ops_registry.getPeriodState()

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
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

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # 1.1. Emergency Protection end date extended by one year
        protection_details_after_dg = timelock.getEmergencyProtectionDetails()
        assert protection_details_after_dg["emergencyProtectionEndsAfter"] == EMERGENCY_PROTECTION_END_DATE_AFTER

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
        # The new 6-month window (Jan-Jul 2026) encompasses the old 3-month one (Apr-Jul 2026),
        # so `_currentPeriodAdvanced` does not trigger and the spent counter carries over.
        # The period boundaries snap to the new 6-month calendar window covering the current chain time.
        (
            alliance_ops_spent_after,
            alliance_ops_spendable_after,
            alliance_ops_period_start_after,
            alliance_ops_period_end_after,
        ) = alliance_ops_registry.getPeriodState()
        assert alliance_ops_period_start_after == ALLIANCE_OPS_PERIOD_START_AFTER
        assert alliance_ops_period_end_after == ALLIANCE_OPS_PERIOD_END_AFTER
        # Invariant: spent + spendable == limit. Holds even on re-runs where pre-state wasn't captured.
        assert alliance_ops_spent_after + alliance_ops_spendable_after == ALLIANCE_OPS_LIMIT_AFTER
        # On a first-run we additionally verify the spent counter was preserved through the change.
        if alliance_ops_spent_before is not None:
            assert alliance_ops_spent_after == alliance_ops_spent_before

        alliance_ops_payment_motion_test(stranger, accounts)


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


def alliance_ops_payment_motion_test(stranger, accounts):
    """Post-DG scenario: an Alliance Ops top-up motion enacts under the new limit and increments spent."""
    chain.snapshot()
    easy_track = interface.EasyTrack(EASYTRACK)
    alliance_ops_registry = interface.AllowedRecipientRegistry(ALLIANCE_OPS_STABLECOINS_REGISTRY)
    multisig = accounts.at(ALLIANCE_OPS_TRUSTED_CALLER, force=True)
    dai_token = interface.ERC20(DAI_TOKEN)
    transfer_amount = 1_000 * 10**18

    spent_before, _, _, _ = alliance_ops_registry.getPeriodState()

    create_and_enact_payment_motion(
        easy_track,
        ALLIANCE_OPS_TRUSTED_CALLER,
        ALLIANCE_OPS_TOP_UP_FACTORY,
        dai_token,
        [multisig],
        [transfer_amount],
        stranger,
    )

    spent_after, _, _, _ = alliance_ops_registry.getPeriodState()
    assert spent_after == spent_before + transfer_amount
    chain.revert()
