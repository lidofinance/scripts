import pytest

from brownie import chain, interface
from brownie.network.transaction import TransactionReceipt

from utils.easy_track import create_permissions
from utils.test.tx_tracing_helpers import (
    count_vote_items_by_events,
    display_dg_events,
    display_voting_events,
    group_dg_events_from_receipt,
    group_voting_events_from_receipt,
)
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import EVMScriptFactoryAdded, validate_evmscript_factory_added_event
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import calculate_vote_ipfs_description, get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_04_14_hoodi_protocol_upgrade import (
    start_vote,
    get_vote_items,
    get_dg_items,
    UPGRADE_VOTE_SCRIPT,
    DG_PROPOSAL_METADATA,
    IPFS_DESCRIPTION,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x49B3512c44891bef83F8967d075121Bd1b07a01B"
AGENT = "0x0534aA41907c9631fae990960bCC72d75fA7cfeD"
EMERGENCY_PROTECTED_TIMELOCK = "0x0A5E22782C0Bd4AddF10D771f0bF0406B038282d"
DUAL_GOVERNANCE = "0x9CAaCCc62c66d817CC59c44780D1b722359795bF"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x0eCc17597D292271836691358B22340b78F3035B"
EASYTRACK = "0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a"
STAKING_ROUTER = "0xCc820558B39ee15C7C45B59390B503b83fb499A8"

UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x0000000000000000000000000000000000000000"  # TODO
ALLOW_CONSOLIDATION_PAIR_FACTORY = "0x0000000000000000000000000000000000000000"  # TODO
CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY = "0x0000000000000000000000000000000000000000"  # TODO
CONSOLIDATION_MIGRATOR = "0x0000000000000000000000000000000000000000"  # TODO
META_REGISTRY = "0x0000000000000000000000000000000000000000"  # TODO


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = None
EXPECTED_DG_EVENTS_FROM_AGENT = None
EXPECTED_DG_EVENTS_COUNT = None
IPFS_DESCRIPTION_HASH = None


def _is_placeholder_address(value: str) -> bool:
    return value in ("", "0x0000000000000000000000000000000000000000")


def _is_placeholder_text(value: str) -> bool:
    return "TODO:" in value


pytestmark = pytest.mark.skipif(
    _is_placeholder_address(UPGRADE_VOTE_SCRIPT)
    or _is_placeholder_address(UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY)
    or _is_placeholder_address(ALLOW_CONSOLIDATION_PAIR_FACTORY)
    or _is_placeholder_address(CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY)
    or _is_placeholder_address(CONSOLIDATION_MIGRATOR)
    or _is_placeholder_address(META_REGISTRY)
    or _is_placeholder_text(DG_PROPOSAL_METADATA)
    or _is_placeholder_text(IPFS_DESCRIPTION),
    reason="Fill TODO values in the active Hoodi upgrade vote script before running the dedicated test.",
)


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items()

    proposal_calls = []
    for target, data in dg_items:
        proposal_calls.append(
            {
                "target": target,
                "value": 0,
                "data": data,
            }
        )

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)
    easy_track = interface.EasyTrack(EASYTRACK)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    consolidation_migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)
    meta_registry = interface.IMetaRegistry(META_REGISTRY)

    vote_desc_items, call_script_items = get_vote_items()
    dg_items = get_dg_items()

    expected_vote_events_count = EXPECTED_VOTE_EVENTS_COUNT or len(call_script_items)
    expected_dg_events_from_agent = EXPECTED_DG_EVENTS_FROM_AGENT or len(dg_items)
    expected_dg_events_count = EXPECTED_DG_EVENTS_COUNT or len(dg_items)
    expected_ipfs_description_hash = IPFS_DESCRIPTION_HASH or calculate_vote_ipfs_description(IPFS_DESCRIPTION)["cid"]

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

    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    expected_dg_proposal_id = EXPECTED_DG_PROPOSAL_ID
    dg_proposals_count_before_vote_execution = timelock.getProposalsCount()

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        initial_factories = easy_track.getEVMScriptFactories()
        assert UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY not in initial_factories
        assert ALLOW_CONSOLIDATION_PAIR_FACTORY not in initial_factories
        assert CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY not in initial_factories

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == expected_ipfs_description_hash

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================

        new_factories = easy_track.getEVMScriptFactories()
        assert UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY in new_factories
        assert ALLOW_CONSOLIDATION_PAIR_FACTORY in new_factories
        assert CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY in new_factories

        assert len(vote_events) == expected_vote_events_count
        assert count_vote_items_by_events(vote_tx, voting.address) == expected_vote_events_count

        if expected_dg_proposal_id is None:
            expected_dg_proposal_id = dg_proposals_count_before_vote_execution + 1

        assert expected_dg_proposal_id == timelock.getProposalsCount()

        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=expected_dg_proposal_id,
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

        validate_evmscript_factory_added_event(
            event=vote_events[1],
            p=EVMScriptFactoryAdded(
                factory_addr=UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                permissions=create_permissions(staking_router, "updateModuleShares"),
            ),
            emitted_by=easy_track,
        )

        validate_evmscript_factory_added_event(
            event=vote_events[2],
            p=EVMScriptFactoryAdded(
                factory_addr=ALLOW_CONSOLIDATION_PAIR_FACTORY,
                permissions=create_permissions(consolidation_migrator, "allowPair"),
            ),
            emitted_by=easy_track,
        )

        validate_evmscript_factory_added_event(
            event=vote_events[3],
            p=EVMScriptFactoryAdded(
                factory_addr=CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY,
                permissions=create_permissions(meta_registry, "createOrUpdateOperatorGroup"),
            ),
            emitted_by=easy_track,
        )
    elif expected_dg_proposal_id is None:
        pytest.skip("Fill EXPECTED_DG_PROPOSAL_ID to run the DG part against an already executed live Hoodi vote.")

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if expected_dg_proposal_id is not None:
        details = timelock.getProposalDetails(expected_dg_proposal_id)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================

            # TODO Acceptance tests (before DG state)

            # TODO Scenario tests (before DG state)

            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(expected_dg_proposal_id, {"from": stranger})

            if timelock.getProposalDetails(expected_dg_proposal_id)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(expected_dg_proposal_id, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == expected_dg_events_from_agent
                assert len(dg_events) == expected_dg_events_count

                # TODO validate all DG events

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================

        # TODO Acceptance tests (after DG state)

        # TODO Scenario tests (after DG state)
