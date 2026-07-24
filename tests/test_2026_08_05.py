from brownie import chain, convert, interface, web3, ZERO_ADDRESS, reverts
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.tx_tracing import tx_events_from_receipt
from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    add_event_emitter,
    display_voting_events,
    display_dg_events
)
from utils.evm_script import encode_call_script
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.proxy import validate_proxy_upgrade_event
from utils.test.event_validators.permission import validate_grant_role_event
from utils.test.event_validators.allowed_recipients_registry import validate_recipient_added_event
from utils.test.event_validators.easy_track import (
    EVMScriptFactoryAdded,
    validate_evmscript_factory_added_event,
    validate_evmscript_factory_removed_event,
)
from utils.easy_track import create_permissions

from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.upgrade_2026_08_05 import (
    start_vote,
    get_vote_items,
    get_dg_items,
    DG_PROPOSAL_METADATA,
)


# ============================================================================
# ============================== Constants ===================================
# ===========================================================================
# --- Committees ---
TMC = "0xa02FC823cCE0D016bD7e17ac684c9abAb2d6D647"
EMERGENCY_COMMITTEE = "0x73b047fe6337183A454c5217241D780a932777bD"

# --- Lido contracts ---
LIDO_LOCATOR = "0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb"
OP_STACK_TOKEN_RATE_PUSHER = "0xd54c1c6413caac3477ac14b2a80d5398e3c32ffe"
STONKS_STETH_TOPUP_REGISTRY = "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OLD_TOKEN_RATE_NOTIFIER = "0x25e35855783bec3E49355a29e110f02Ed8b05ba9"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

# --- NEST contracts ---
ORACLE_ROUTER = "0x79ef3a538200Fe4981D67E7e886bfb36D4Cb5a31"
NEW_TOKEN_RATE_NOTIFIER = "0xbe05d12Fd10919F1881125006523452F6aFF791b"
NEW_LIDO_LOCATOR_IMPL = "0xF2Ffb952e129a63F0614Ff87126E1d4a494A2313"
STAKING_REVENUE_SOURCE = "0x6220212a33a87Ed7Cc386B67eB2c393974F28C38"
BUYBACK_EXECUTOR = "0x6c213ca5A10Cc26548C742229569B4AeD2A9C9B7"
BUYBACK_STONKS_TREASURY = "0xb368586CB980895E51e1D82102E63b3F69d3F151"
BUYBACK_ALLOCATOR = "0xAA568141c051f2D1132b110f8391F18D48E8D889"

# --- Easy Track factories ---
OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0x0C6703F1d8D9DdfB6c6e5F57b4f7432a6500D6D8"
NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY = "0xde3e46E3129fA4e4e3f66c9024B0A3Ad509b27a1"
CSM_TRUSTED_CALLER = "0xC52fC3081123073078698F1EAc2f1Dc7Bd71880f"
CSM_STAKING_MODULE_ID = 3

# --- Roles ---
MANAGER_ROLE = "0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e"  # keccak256("Buybacks.MANAGER_ROLE")
ALLOCATOR_ROLE = "0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2"  # keccak256("Buybacks.BuybackExecutor.ALLOCATOR_ROLE")
EMERGENCY_ROLE = "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd"  # keccak256("Buybacks.BuybackExecutor.EMERGENCY_ROLE")

# TokenRateNotifier.ObserverKind
OBSERVER_KIND_NO_ARGS = 0
OBSERVER_KIND_WITH_ARGS = 1

ONE_DAY = 86400

# The Buybacks role grants (vote items 4-8) are executed directly by Aragon Voting,
# not forwarded through the Agent, so each grant emits a single LogScriptCall followed by RoleGranted.
DIRECT_GRANT_ROLE_EVENTS_CHAIN = ["LogScriptCall", "RoleGranted"]

# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 204
EXPECTED_VOTE_ITEMS_COUNT = 11
EXPECTED_VOTE_EVENTS_COUNT = 11
EXPECTED_DG_PROPOSAL_ID = 13
EXPECTED_DG_EVENTS_FROM_AGENT = 4
EXPECTED_DG_EVENTS_COUNT = 1

# TODO set once the IPFS description is uploaded.
IPFS_DESCRIPTION_HASH = ""


# ============================================================================
# ============================ Event validators ==============================
# ============================================================================
def _single_event(event: EventDict, name: str):
    assert event.count(name) == 1, f"Expected exactly one {name} event, got {event.count(name)}"
    return event[name][0]


def _assert_emitted_by(e, emitted_by: str) -> None:
    assert convert.to_address(e["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_manager_set_event(event: EventDict, manager: str, emitted_by: str) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "ManagerSet"])
    e = _single_event(event, "ManagerSet")
    assert convert.to_address(e["manager"]) == convert.to_address(manager), "Wrong OracleRouter manager"
    _assert_emitted_by(e, emitted_by)


def validate_stonks_set_event(event: EventDict, new_stonks: str, emitted_by: str) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "StonksAndOperatingModeSet"])
    e = _single_event(event, "StonksAndOperatingModeSet")
    assert convert.to_address(e["newStonks"]) == convert.to_address(new_stonks), "Wrong stonks set"
    _assert_emitted_by(e, emitted_by)


def validate_activated_event(event: EventDict, emitted_by: str) -> None:
    assert "LogScriptCall" in event, "No LogScriptCall event found"
    e = _single_event(event, "Activated")
    assert e["activationTS"] > 0, "activationTS not recorded"
    _assert_emitted_by(e, emitted_by)


def validate_observer_added_event(event: EventDict, observer: str, emitted_by: str) -> None:
    validate_events_chain([e.name for e in event], ["LogScriptCall", "ObserverAdded", "ScriptResult", "Executed"])
    e = _single_event(event, "ObserverAdded")
    assert convert.to_address(e["observer"]) == convert.to_address(observer), "Wrong observer added"
    _assert_emitted_by(e, emitted_by)


def _group_agent_dg_events_from_receipt(receipt: TransactionReceipt, timelock: str, agent: str):
    """Re-group a single-agent-forward DG proposal into one group per forwarded sub-call.

    The default DG grouping yields one group. Here each sub-call is delimited by a LogScriptCall
    emitted by the Agent while it runs the forwarded call script.
    """
    events = tx_events_from_receipt(receipt)
    assert (
        web3.to_checksum_address(events[-1]["address"]) == web3.to_checksum_address(timelock)
        and events[-1]["name"] == "ProposalExecuted"
    ), "Unexpected Dual Governance service event"

    groups = []
    current_group = None
    for event in events[:-1]:
        is_start_of_new_group = event["name"] == "LogScriptCall" and web3.to_checksum_address(
            event["address"]
        ) == web3.to_checksum_address(agent)
        if is_start_of_new_group:
            current_group = []
            groups.append(current_group)
        if current_group is not None:
            current_group.append(add_event_emitter(event))

    return [EventDict(group) for group in groups]


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    dg_items = get_dg_items()

    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)

    oracle_router = interface.OracleRouter(ORACLE_ROUTER)
    buyback_executor = interface.BuybackExecutor(BUYBACK_EXECUTOR)
    buyback_allocator = interface.BuybackAllocator(BUYBACK_ALLOCATOR)
    new_token_rate_notifier = interface.TokenRateNotifierV2(NEW_TOKEN_RATE_NOTIFIER)
    old_token_rate_notifier = interface.TokenRateNotifier(OLD_TOKEN_RATE_NOTIFIER)
    lido_locator_proxy = interface.OssifiableProxy(LIDO_LOCATOR)
    stonks_topup_registry = interface.AllowedRecipientRegistry(STONKS_STETH_TOPUP_REGISTRY)
    easy_track = interface.EasyTrack(EASY_TRACK)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    old_update_staking_module_share_limits_factory = interface.UpdateStakingModuleShareLimits(
        OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    )
    new_update_staking_module_share_limits_factory = interface.UpdateStakingModuleShareLimits(
        NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY
    )
    new_factory_permissions = (
        create_permissions(new_update_staking_module_share_limits_factory, "validateParams")
        + create_permissions(staking_router, "updateModuleShares")[2:]
    )


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
        # vote item 2
        assert oracle_router.manager() != TMC, "OracleRouter manager already set to TMC"
        # vote item 3
        assert buyback_executor.stonks() == ZERO_ADDRESS, "BuybackExecutor stonks already set"
        # vote item 4
        assert not buyback_executor.hasRole(ALLOCATOR_ROLE, BUYBACK_ALLOCATOR)
        # vote item 5
        assert not buyback_executor.hasRole(MANAGER_ROLE, TMC)
        # vote item 6
        assert not buyback_executor.hasRole(EMERGENCY_ROLE, TMC)
        # vote item 7
        assert not buyback_executor.hasRole(EMERGENCY_ROLE, EMERGENCY_COMMITTEE)
        # vote item 8
        assert not buyback_allocator.hasRole(MANAGER_ROLE, TMC)
        # vote item 9
        assert buyback_allocator.activationTS() == 0, "BuybackAllocator already activated"
        # vote items 10-11
        initial_factories = easy_track.getEVMScriptFactories()
        assert OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY in initial_factories
        assert NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY not in initial_factories
        assert old_update_staking_module_share_limits_factory.maxStakeShareLimitIncrease() == 500
        assert old_update_staking_module_share_limits_factory.maxStakeShareLimitDecrease() == 500
        assert old_update_staking_module_share_limits_factory.maxPriorityExitShareThresholdIncrease() == 600
        assert old_update_staking_module_share_limits_factory.maxPriorityExitShareThresholdDecrease() == 600
        assert new_update_staking_module_share_limits_factory.name() == "CSM"
        assert new_update_staking_module_share_limits_factory.trustedCaller() == CSM_TRUSTED_CALLER
        assert new_update_staking_module_share_limits_factory.stakingRouter() == STAKING_ROUTER
        assert new_update_staking_module_share_limits_factory.stakingModuleId() == CSM_STAKING_MODULE_ID
        assert new_update_staking_module_share_limits_factory.maxStakeShareLimitIncrease() == 50
        assert new_update_staking_module_share_limits_factory.maxStakeShareLimitDecrease() == 50
        assert new_update_staking_module_share_limits_factory.maxPriorityExitShareThresholdIncrease() == 60
        assert new_update_staking_module_share_limits_factory.maxPriorityExitShareThresholdDecrease() == 60

        if IPFS_DESCRIPTION_HASH:
            assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # vote item 2
        assert oracle_router.manager() == TMC, "OracleRouter manager not set to TMC"
        # vote item 3
        assert buyback_executor.stonks() == BUYBACK_STONKS_TREASURY, "BuybackExecutor stonks not set"
        # vote item 4
        assert buyback_executor.hasRole(ALLOCATOR_ROLE, BUYBACK_ALLOCATOR), "ALLOCATOR_ROLE not granted to allocator"
        # vote item 5
        assert buyback_executor.hasRole(MANAGER_ROLE, TMC), "executor MANAGER_ROLE not granted to TMC"
        # vote item 6
        assert buyback_executor.hasRole(EMERGENCY_ROLE, TMC), "executor EMERGENCY_ROLE not granted to TMC"
        # vote item 7
        assert buyback_executor.hasRole(EMERGENCY_ROLE, EMERGENCY_COMMITTEE), "executor EMERGENCY_ROLE not granted to EC"
        # vote item 8
        assert buyback_allocator.hasRole(MANAGER_ROLE, TMC), "allocator MANAGER_ROLE not granted to TMC"
        # vote item 9: activate() records activationTS as midnight UTC of the execution day
        assert buyback_allocator.activationTS() == vote_tx.timestamp - (vote_tx.timestamp % ONE_DAY), \
            "BuybackAllocator not activated at the vote-execution day's midnight UTC"
        # vote items 10-11
        updated_factories = easy_track.getEVMScriptFactories()
        assert OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY not in updated_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY)) == b""
        assert NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY in updated_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY)) == bytes.fromhex(
            new_factory_permissions.removeprefix("0x")
        )

        # vote items 4-8: a non-admin (stranger) cannot grant the buyback roles
        with reverts():
            buyback_executor.grantRole(MANAGER_ROLE, stranger, {"from": stranger})
        with reverts():
            buyback_allocator.grantRole(MANAGER_ROLE, stranger, {"from": stranger})

        # buyback contracts point to the correct OracleRouter
        assert buyback_executor.ORACLE_ROUTER() == ORACLE_ROUTER, "BuybackExecutor points at wrong OracleRouter"
        assert buyback_allocator.ORACLE_ROUTER() == ORACLE_ROUTER, "BuybackAllocator points at wrong OracleRouter"


        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_ITEMS_COUNT

        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata=DG_PROPOSAL_METADATA,
                proposal_calls=dual_governance_proposal_calls,
            )

        # vote item 2
        validate_manager_set_event(vote_events[1], manager=TMC, emitted_by=ORACLE_ROUTER)
        # vote item 3
        validate_stonks_set_event(vote_events[2], new_stonks=BUYBACK_STONKS_TREASURY, emitted_by=BUYBACK_EXECUTOR)
        # vote item 4
        validate_grant_role_event(
            vote_events[3], role=ALLOCATOR_ROLE, grant_to=BUYBACK_ALLOCATOR, sender=VOTING,
            emitted_by=BUYBACK_EXECUTOR, event_chain=DIRECT_GRANT_ROLE_EVENTS_CHAIN,
        )
        # vote item 5
        validate_grant_role_event(
            vote_events[4], role=MANAGER_ROLE, grant_to=TMC, sender=VOTING,
            emitted_by=BUYBACK_EXECUTOR, event_chain=DIRECT_GRANT_ROLE_EVENTS_CHAIN,
        )
        # vote item 6
        validate_grant_role_event(
            vote_events[5], role=EMERGENCY_ROLE, grant_to=TMC, sender=VOTING,
            emitted_by=BUYBACK_EXECUTOR, event_chain=DIRECT_GRANT_ROLE_EVENTS_CHAIN,
        )
        # vote item 7
        validate_grant_role_event(
            vote_events[6], role=EMERGENCY_ROLE, grant_to=EMERGENCY_COMMITTEE, sender=VOTING,
            emitted_by=BUYBACK_EXECUTOR, event_chain=DIRECT_GRANT_ROLE_EVENTS_CHAIN,
        )
        # vote item 8
        validate_grant_role_event(
            vote_events[7], role=MANAGER_ROLE, grant_to=TMC, sender=VOTING,
            emitted_by=BUYBACK_ALLOCATOR, event_chain=DIRECT_GRANT_ROLE_EVENTS_CHAIN,
        )
        # vote item 9
        validate_activated_event(vote_events[8], emitted_by=BUYBACK_ALLOCATOR)
        # vote item 10
        validate_evmscript_factory_removed_event(
            vote_events[9],
            factory_addr=OLD_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
            emitted_by=easy_track,
        )
        # vote item 11
        validate_evmscript_factory_added_event(
            event=vote_events[10],
            p=EVMScriptFactoryAdded(
                factory_addr=NEW_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY,
                permissions=new_factory_permissions,
            ),
            emitted_by=easy_track,
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
            # DG item 1.2
            new_notifier_observers_before = [
                str(new_token_rate_notifier.observers(i)[0]).lower()
                for i in range(new_token_rate_notifier.observersLength())
            ]
            assert str(STAKING_REVENUE_SOURCE).lower() not in new_notifier_observers_before, "Revenue source already registered"

            # DG item 1.3: LidoLocator still uses the old implementation and still resolves to the old postTokenRebaseReceiver
            assert lido_locator_proxy.proxy__getImplementation() != NEW_LIDO_LOCATOR_IMPL, "LidoLocator already upgraded"
            assert (
                interface.LidoLocator(LIDO_LOCATOR).postTokenRebaseReceiver() != NEW_TOKEN_RATE_NOTIFIER
            ), "postTokenRebaseReceiver already repointed to the new notifier"

            # DG item 1.4
            assert not stonks_topup_registry.isRecipientAllowed(BUYBACK_ALLOCATOR), "Allocator already an allowed recipient"


            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)

                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                outer_dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                # Regroup by the Agent's sub-calls to validate each sub-calls events
                agent_dg_events = _group_agent_dg_events_from_receipt(
                    dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, agent=AGENT
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_FROM_AGENT
                assert len(outer_dg_events) == EXPECTED_DG_EVENTS_COUNT
                assert len(agent_dg_events) == EXPECTED_DG_EVENTS_FROM_AGENT

                # DG item 1.1: OpStack rate pusher observer added to the new TokenRateNotifier
                validate_observer_added_event(
                    agent_dg_events[0], observer=OP_STACK_TOKEN_RATE_PUSHER, emitted_by=NEW_TOKEN_RATE_NOTIFIER
                )
                # DG item 1.2: StakingRevenueSource observer added to the new TokenRateNotifier
                validate_observer_added_event(
                    agent_dg_events[1], observer=STAKING_REVENUE_SOURCE, emitted_by=NEW_TOKEN_RATE_NOTIFIER
                )
                # DG item 1.3: LidoLocator implementation upgrade
                validate_proxy_upgrade_event(agent_dg_events[2], NEW_LIDO_LOCATOR_IMPL, emitted_by=LIDO_LOCATOR)
                # DG item 1.4: BuybackAllocator added as an allowed recipient
                validate_recipient_added_event(
                    agent_dg_events[3],
                    recipient=BUYBACK_ALLOCATOR,
                    title="Buyback Allocator",
                    emitted_by=STONKS_STETH_TOPUP_REGISTRY,
                )


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================
        # DG items 1.1-1.2: new TokenRateNotifier observers — OpStack pusher (NoArgs) + StakingRevenueSource (WithArgs)
        new_observers = [
            tuple(new_token_rate_notifier.observers(i))
            for i in range(new_token_rate_notifier.observersLength())
        ]
        new_observers_normalized = [(str(addr).lower(), kind) for addr, kind in new_observers]
        new_observer_addrs = [addr for addr, _ in new_observers_normalized]

        # DG item 1.1
        assert (str(OP_STACK_TOKEN_RATE_PUSHER).lower(), OBSERVER_KIND_NO_ARGS) in new_observers_normalized, \
            "OpStack rate pusher not registered as NoArgs observer"
        # DG item 1.2
        assert (str(STAKING_REVENUE_SOURCE).lower(), OBSERVER_KIND_WITH_ARGS) in new_observers_normalized, \
            "Revenue source not registered as WithArgs observer"
        # DG item 1.2: the registered StakingRevenueSource observer is wired to the right OracleRouter and LidoLocator
        staking_revenue_source = interface.StakingRevenueSource(STAKING_REVENUE_SOURCE)
        assert staking_revenue_source.ORACLE_ROUTER() == ORACLE_ROUTER, "StakingRevenueSource points at wrong OracleRouter"
        assert staking_revenue_source.LIDO_LOCATOR() == LIDO_LOCATOR, "StakingRevenueSource points at wrong LidoLocator"

        # DG items 1.1-1.3: every old-notifier observer must be migrated to the new one before the repoint
        for i in range(old_token_rate_notifier.observersLength()):
            old_observer = str(old_token_rate_notifier.observers(i)).lower()
            assert old_observer in new_observer_addrs, \
                f"Observer {old_observer} on the old notifier was not migrated to the new notifier"

        # DG item 1.3: LidoLocator upgraded and postTokenRebaseReceiver repointed to the new notifier
        assert lido_locator_proxy.proxy__getImplementation() == NEW_LIDO_LOCATOR_IMPL, "LidoLocator impl not upgraded"
        assert (
            interface.LidoLocator(LIDO_LOCATOR).postTokenRebaseReceiver() == NEW_TOKEN_RATE_NOTIFIER
        ), "postTokenRebaseReceiver not repointed to the new notifier"

        # DG item 1.4
        assert stonks_topup_registry.isRecipientAllowed(BUYBACK_ALLOCATOR), "Allocator not an allowed recipient"
