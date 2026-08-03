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
from utils.allowed_recipients_registry import create_top_up_allowed_recipient_permission
from utils.easy_track import create_permissions

from utils.config import contracts, DAI_TOKEN
from utils.test.helpers import ETH
from utils.test.deposits_helpers import WEI_TOLERANCE
from utils.test.governance_helpers import execute_vote_and_process_dg_proposals
from utils.test.oracle_report_helpers import oracle_report
from utils.test.easy_track_helpers import (
    _encode_calldata,
    assert_create_evm_script_reverts,
    create_and_enact_payment_motion,
    create_and_enact_add_recipient_motion,
    create_and_enact_remove_recipient_motion,
)

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
OP_STACK_TOKEN_RATE_PUSHER = "0xd54c1c6413caac3477AC14b2a80D5398E3c32FfE"
STONKS_STETH_TOPUP_REGISTRY = "0x1a7cFA9EFB4D5BfFDE87B0FaEb1fC65d653868C0"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"
OLD_TOKEN_RATE_NOTIFIER = "0x25e35855783bec3E49355a29e110f02Ed8b05ba9"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
FINANCE = "0xB9E5CBB9CA5b0d659238807E84D0176930753d86"
ALLOWED_TOKENS_REGISTRY = "0x4AC40c34f8992bb1e5E856A448792158022551ca"

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

# --- LOL (Liquidity Observation Lab) stablecoins Easy Track setup ---
LOL_STABLES_REGISTRY = "0x8d8b35cA51e7808098afF4918C21Ce428c943F89"
LOL_STABLES_TOP_UP_FACTORY = "0xc72d4C3e86b681D7c9EE306D41193C64D709C303"
LOL_STABLES_ADD_RECIPIENT_FACTORY = "0xe24230619e9218C1eed3de3489a22f6BC3ce18FF"
LOL_STABLES_REMOVE_RECIPIENT_FACTORY = "0xF4d5D97C85eD18f77F99B57f55E9E11d52992632"
LOL_STABLES_FACTORIES = [
    LOL_STABLES_TOP_UP_FACTORY,
    LOL_STABLES_ADD_RECIPIENT_FACTORY,
    LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
]
LOL_TRUSTED_CALLER = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"  # LOL multisig, also the only allowed recipient
LOL_STABLES_LIMIT = 8_000_000 * 10**18
LOL_STABLES_PERIOD_DURATION_MONTHS = 6
LOL_STABLES_PERIOD_START = 1782864000  # 2026-07-01 00:00:00 UTC
LOL_STABLES_PERIOD_END = 1798761600  # 2027-01-01 00:00:00 UTC

# --- Roles ---
MANAGER_ROLE = "0x24bec1f1283f989ed510b4d89bc7ef5002f20db1b60c1b3192336791c868543e"  # keccak256("Buybacks.MANAGER_ROLE")
ALLOCATOR_ROLE = "0x87905334ad07701d0cd9b21ea0599de1a0cab067e0ab49596d423d87159ac7f2"  # keccak256("Buybacks.BuybackExecutor.ALLOCATOR_ROLE")
EMERGENCY_ROLE = "0xc748c205190870b4e890036f373e30556929f7fbf3db8644c998a652c1996dbd"  # keccak256("Buybacks.BuybackExecutor.EMERGENCY_ROLE")
# AllowedRecipientsRegistry roles — each hash is keccak256 of the constant's own name
ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
UPDATE_SPENT_AMOUNT_ROLE = "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
SET_PARAMETERS_ROLE = "0x260b83d52a26066d8e9db550fa70395df5f3f064b50ff9d8a94267d9f1fe1967"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"

# TokenRateNotifier.ObserverKind
OBSERVER_KIND_NO_ARGS = 0
OBSERVER_KIND_WITH_ARGS = 1

ONE_DAY = 86400

# --- NEST buyback scenario params ---
QUOTE_DENOMINATION_ETH = 1
TOTAL_BASIS_POINTS = 10_000
SECONDS_PER_YEAR = 365 * ONE_DAY
NORMAL_CL_APR_BP = 300  # 3%, well under the oracle's ~10% annual CL-increase sanity limit

# Launch staleness (finance) is 1h ETH/USD bridge, 24h token feeds. Not usable on the fork: fast-forwarded
# DG timelock delays plus the oracle_report frame push the clock past the Chainlink feeds' frozen updatedAt,
# so 1h/24h trip OracleStale. We widen the bound to cover that gap for the fork run — quote (ETH), active
# flag and underlying feeds are identical to launch.
FORK_FEED_STALENESS_SECONDS = 30 * ONE_DAY

# --- LOL stablecoins scenario params ---
DAI_WARD = "0x9759A6Ac90977b93B58547b4A71c78317f391A28"  # authorized DAI minter, funds the Agent on a fork
# ACL cap on a single newImmediatePayment by the EVMScriptExecutor
FINANCE_DAI_MAX_PER_CALL = 2_000_000 * 10**18
PAYMENT_CALLDATA_SIGNATURE = ["address", "address[]", "uint256[]"]

# The Buybacks role grants (vote items 4-8) are executed directly by Aragon Voting,
# not forwarded through the Agent, so each grant emits a single LogScriptCall followed by RoleGranted.
DIRECT_GRANT_ROLE_EVENTS_CHAIN = ["LogScriptCall", "RoleGranted"]

# The LOL registry role grants (DG items 1.5-1.6) run inside the Agent-forwarded call script, and
# _group_agent_dg_events_from_receipt splits it per Agent LogScriptCall — one per group, like ObserverAdded.
AGENT_FORWARDED_GRANT_ROLE_EVENTS_CHAIN = ["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"]

# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = 204
EXPECTED_VOTE_ITEMS_COUNT = 14
EXPECTED_VOTE_EVENTS_COUNT = 14
EXPECTED_DG_PROPOSAL_ID = 13
EXPECTED_DG_EVENTS_FROM_AGENT = 6
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


@pytest.fixture(scope="module")
def vote_applied(module_isolation, helpers, vote_ids_from_env, dg_proposal_ids_from_env):
    """Post-launch state for the scenario tests below: the omnibus and its DG proposal are applied.

    `test_vote` applies them itself, but function-level isolation rolls that back, so the scenarios
    take a module-scoped snapshot of their own.
    """
    execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env)


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

    lol_stables_registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    lol_stables_top_up_factory = interface.TopUpAllowedRecipients(LOL_STABLES_TOP_UP_FACTORY)
    lol_stables_add_recipient_factory = interface.AddAllowedRecipient(LOL_STABLES_ADD_RECIPIENT_FACTORY)
    lol_stables_remove_recipient_factory = interface.RemoveAllowedRecipient(LOL_STABLES_REMOVE_RECIPIENT_FACTORY)
    lol_stables_top_up_permissions = create_top_up_allowed_recipient_permission(registry_address=LOL_STABLES_REGISTRY)
    lol_stables_add_recipient_permissions = create_permissions(lol_stables_registry, "addRecipient")
    lol_stables_remove_recipient_permissions = create_permissions(lol_stables_registry, "removeRecipient")


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
        # vote items 12-14: none of the LOL stablecoins factories is registered yet
        for factory_address in LOL_STABLES_FACTORIES:
            assert factory_address not in initial_factories, f"{factory_address} already registered in Easy Track"
        # vote items 12-14: the pre-configured registry state the factories will operate on
        assert lol_stables_registry.getLimitParameters() == (LOL_STABLES_LIMIT, LOL_STABLES_PERIOD_DURATION_MONTHS)
        assert lol_stables_registry.getPeriodState() == (
            0,
            LOL_STABLES_LIMIT,
            LOL_STABLES_PERIOD_START,
            LOL_STABLES_PERIOD_END,
        )
        assert lol_stables_registry.getAllowedRecipients() == [LOL_TRUSTED_CALLER]
        # vote item 12: the top up factory is wired to the LOL registry and the canonical Lido contracts
        assert lol_stables_top_up_factory.trustedCaller() == LOL_TRUSTED_CALLER
        assert lol_stables_top_up_factory.allowedRecipientsRegistry() == LOL_STABLES_REGISTRY
        assert lol_stables_top_up_factory.allowedTokensRegistry() == ALLOWED_TOKENS_REGISTRY
        assert lol_stables_top_up_factory.finance() == FINANCE
        assert lol_stables_top_up_factory.easyTrack() == EASY_TRACK
        # vote item 13
        assert lol_stables_add_recipient_factory.trustedCaller() == LOL_TRUSTED_CALLER
        assert lol_stables_add_recipient_factory.allowedRecipientsRegistry() == LOL_STABLES_REGISTRY
        # vote item 14
        assert lol_stables_remove_recipient_factory.trustedCaller() == LOL_TRUSTED_CALLER
        assert lol_stables_remove_recipient_factory.allowedRecipientsRegistry() == LOL_STABLES_REGISTRY
        # DG items 1.5-1.6: the EVMScriptExecutor can already update the spent amount, but not the recipients list
        assert lol_stables_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, EVM_SCRIPT_EXECUTOR)
        assert not lol_stables_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR)
        assert not lol_stables_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR)

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
        # vote item 12
        assert LOL_STABLES_TOP_UP_FACTORY in updated_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(LOL_STABLES_TOP_UP_FACTORY)) == bytes.fromhex(
            lol_stables_top_up_permissions.removeprefix("0x")
        )
        # vote item 13
        assert LOL_STABLES_ADD_RECIPIENT_FACTORY in updated_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(LOL_STABLES_ADD_RECIPIENT_FACTORY)) == bytes.fromhex(
            lol_stables_add_recipient_permissions.removeprefix("0x")
        )
        # vote item 14
        assert LOL_STABLES_REMOVE_RECIPIENT_FACTORY in updated_factories
        assert bytes(easy_track.evmScriptFactoryPermissions(LOL_STABLES_REMOVE_RECIPIENT_FACTORY)) == bytes.fromhex(
            lol_stables_remove_recipient_permissions.removeprefix("0x")
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

        # vote item 1
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
        # vote item 12
        validate_evmscript_factory_added_event(
            event=vote_events[11],
            p=EVMScriptFactoryAdded(
                factory_addr=LOL_STABLES_TOP_UP_FACTORY,
                permissions=lol_stables_top_up_permissions,
            ),
            emitted_by=easy_track,
        )
        # vote item 13
        validate_evmscript_factory_added_event(
            event=vote_events[12],
            p=EVMScriptFactoryAdded(
                factory_addr=LOL_STABLES_ADD_RECIPIENT_FACTORY,
                permissions=lol_stables_add_recipient_permissions,
            ),
            emitted_by=easy_track,
        )
        # vote item 14
        validate_evmscript_factory_added_event(
            event=vote_events[13],
            p=EVMScriptFactoryAdded(
                factory_addr=LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
                permissions=lol_stables_remove_recipient_permissions,
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
            # DG items 1.1-1.2: neither observer is on the new TokenRateNotifier yet
            new_notifier_observers_before = [
                str(new_token_rate_notifier.observers(i)[0]).lower()
                for i in range(new_token_rate_notifier.observersLength())
            ]
            # DG item 1.1
            assert str(OP_STACK_TOKEN_RATE_PUSHER).lower() not in new_notifier_observers_before, "OpStack rate pusher already registered"
            # DG item 1.2
            assert str(STAKING_REVENUE_SOURCE).lower() not in new_notifier_observers_before, "Revenue source already registered"

            # DG item 1.3: LidoLocator still uses the old implementation and still resolves to the old postTokenRebaseReceiver
            assert lido_locator_proxy.proxy__getImplementation() != NEW_LIDO_LOCATOR_IMPL, "LidoLocator already upgraded"
            assert (
                interface.LidoLocator(LIDO_LOCATOR).postTokenRebaseReceiver() != NEW_TOKEN_RATE_NOTIFIER
            ), "postTokenRebaseReceiver already repointed to the new notifier"

            # DG item 1.4
            assert not stonks_topup_registry.isRecipientAllowed(BUYBACK_ALLOCATOR), "Allocator already an allowed recipient"

            # DG items 1.5-1.6
            assert not lol_stables_registry.hasRole(
                ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR
            ), "Add recipient role already granted"
            assert not lol_stables_registry.hasRole(
                REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR
            ), "Remove recipient role already granted"


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
                # DG item 1.5: ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE granted to the EVMScriptExecutor
                validate_grant_role_event(
                    agent_dg_events[4],
                    role=ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
                    grant_to=EVM_SCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=LOL_STABLES_REGISTRY,
                    event_chain=AGENT_FORWARDED_GRANT_ROLE_EVENTS_CHAIN,
                )
                # DG item 1.6: REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE granted to the EVMScriptExecutor
                validate_grant_role_event(
                    agent_dg_events[5],
                    role=REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
                    grant_to=EVM_SCRIPT_EXECUTOR,
                    sender=AGENT,
                    emitted_by=LOL_STABLES_REGISTRY,
                    event_chain=AGENT_FORWARDED_GRANT_ROLE_EVENTS_CHAIN,
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

        # DG items 1.5-1.6: without these roles the Add/Remove factories would revert on enactment
        assert lol_stables_registry.hasRole(
            ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR
        ), "Add recipient role not granted to the EVMScriptExecutor"
        assert lol_stables_registry.hasRole(
            REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR
        ), "Remove recipient role not granted to the EVMScriptExecutor"
        # the grants must not widen anything else on the registry
        assert not lol_stables_registry.hasRole(SET_PARAMETERS_ROLE, EVM_SCRIPT_EXECUTOR)
        assert not lol_stables_registry.hasRole(DEFAULT_ADMIN_ROLE, EVM_SCRIPT_EXECUTOR)


# ============================================================================
# ======================= NEST buyback happy path ============================
# ============================================================================
def _configure_oracle_router_feeds(oracle_router, tmc):
    """Set the OracleRouter feeds as TMC — the operational step the vote leaves to TMC post-launch."""
    steth = contracts.lido.address
    ldo = contracts.ldo_token.address
    if oracle_router.ethUsdBridge()["aggregator"] == ZERO_ADDRESS:
        oracle_router.setEthUsdBridge(FORK_FEED_STALENESS_SECONDS, {"from": tmc})
    if not oracle_router.tokenConfig(steth)["isActive"]:
        oracle_router.setTokenFeed(steth, QUOTE_DENOMINATION_ETH, FORK_FEED_STALENESS_SECONDS, True, {"from": tmc})
    if not oracle_router.tokenConfig(ldo)["isActive"]:
        oracle_router.setTokenFeed(ldo, QUOTE_DENOMINATION_ETH, FORK_FEED_STALENESS_SECONDS, True, {"from": tmc})


def _production_rebase_cl_diff():
    """CL rewards a normal report carries: current CL balance at ~3% APR over the report's period."""
    consensus = contracts.hash_consensus_for_accounting_oracle
    slots_per_epoch, seconds_per_slot, _ = consensus.getChainConfig()
    _, epochs_per_frame, _ = consensus.getFrameConfig()
    current_ref_slot, _ = consensus.getCurrentFrame()
    last_processing_ref_slot = contracts.accounting_oracle.getLastProcessingRefSlot()

    next_ref_slot = current_ref_slot + epochs_per_frame * slots_per_epoch
    elapsed_seconds = (next_ref_slot - last_processing_ref_slot) * seconds_per_slot

    cl_validators_balance, cl_pending_balance, *_ = contracts.lido.getBalanceStats()
    cl_balance = cl_validators_balance + cl_pending_balance
    return cl_balance * NORMAL_CL_APR_BP * elapsed_seconds // (TOTAL_BASIS_POINTS * SECONDS_PER_YEAR)


def test_nest_buyback_happy_path(vote_applied, accounts, stranger):
    """Drive the launched NEST buyback end to end: rebase -> revenue -> allocate -> CoW order."""
    steth = contracts.lido
    tmc = accounts.at(TMC, force=True)

    oracle_router = interface.OracleRouter(ORACLE_ROUTER)
    buyback_executor = interface.BuybackExecutor(BUYBACK_EXECUTOR)
    buyback_allocator = interface.BuybackAllocator(BUYBACK_ALLOCATOR)
    staking_revenue_source = interface.StakingRevenueSource(STAKING_REVENUE_SOURCE)
    notifier = interface.TokenRateNotifierV2(NEW_TOKEN_RATE_NOTIFIER)
    observer_addresses = [notifier.observers(index)["observer"] for index in range(notifier.observersLength())]

    # Preconditions: the launch is in place
    assert interface.LidoLocator(LIDO_LOCATOR).postTokenRebaseReceiver() == NEW_TOKEN_RATE_NOTIFIER
    assert buyback_allocator.activationTS() > 0, "BuybackAllocator not activated"
    assert buyback_executor.stonks() == BUYBACK_STONKS_TREASURY, "BuybackExecutor stonks not set"
    assert buyback_allocator.STETH() == steth.address, "Allocator stETH handle mismatch"

    # Wiring the launch established: revenue source registered on the notifier and the allocator granted its role
    assert STAKING_REVENUE_SOURCE in observer_addresses, "StakingRevenueSource not registered as a TokenRateNotifier observer"
    assert STAKING_REVENUE_SOURCE in buyback_allocator.revenueSources(), "StakingRevenueSource not a revenue source on the allocator"
    assert buyback_executor.hasRole(buyback_executor.ALLOCATOR_ROLE(), BUYBACK_ALLOCATOR), "allocator lacks ALLOCATOR_ROLE on the executor"

    _configure_oracle_router_feeds(oracle_router, tmc)
    assert oracle_router.tokenConfig(steth.address)["isActive"], "stETH feed not configured on OracleRouter"

    # Rebase -> revenue accrues in the StakingRevenueSource, then convert it to USD
    cumulative_revenue_before = staking_revenue_source.getCumulativeRevenueUSD()
    oracle_report(cl_diff=_production_rebase_cl_diff(), silent=True)
    assert staking_revenue_source.pendingRevenueStEth() > 0, "no fee shares reached the StakingRevenueSource"

    staking_revenue_source.convertPendingRevenueToUSD({"from": stranger})
    assert staking_revenue_source.getCumulativeRevenueUSD() > cumulative_revenue_before, "cumulative revenue did not grow"
    assert staking_revenue_source.pendingRevenueStEth() == 0, "pending revenue not fully converted"

    # Fund the allocator with fresh stETH
    steth_to_fund = ETH(1000)
    # submit rounds minted shares down; mint a few extra wei so the exact transfer below can't revert
    steth.submit(ZERO_ADDRESS, {"from": stranger, "value": steth_to_fund + WEI_TOLERANCE})
    steth.transfer(BUYBACK_ALLOCATOR, steth_to_fund, {"from": stranger})
    assert steth.balanceOf(BUYBACK_ALLOCATOR) >= steth_to_fund - WEI_TOLERANCE, "allocator not funded with stETH"

    spendable_status, _spendable_usd, spendable_steth = buyback_allocator.spendable()
    assert spendable_steth > 0, f"allocator reports nothing spendable (status={spendable_status})"

    # allocate() spends and forwards stETH to Stonks
    stonks_steth_before = steth.balanceOf(BUYBACK_STONKS_TREASURY)
    allocate_tx = buyback_allocator.allocate({"from": stranger})
    assert "AllocationSkipped" not in allocate_tx.events, "allocate() skipped instead of spending"
    allocated = allocate_tx.events["Allocated"]
    assert allocated["spendStEth"] > 0 and allocated["spendUSD"] > 0, "allocate() spent nothing"
    assert convert.to_address(allocated["executor"]) == convert.to_address(BUYBACK_EXECUTOR), "wrong executor"
    processed = allocate_tx.events["AllocationProcessed"]
    assert convert.to_address(processed["stonks"]) == convert.to_address(BUYBACK_STONKS_TREASURY), "wrong stonks"
    assert processed["forwardedToStonks"] > 0, "nothing forwarded to Stonks"
    assert steth.balanceOf(BUYBACK_STONKS_TREASURY) > stonks_steth_before, "Stonks stETH balance did not grow"

    # placeOrder() creates the Stonks/CoW order (stop before off-chain settlement)
    min_order_steth = buyback_executor.minAllowedOrderAmount()
    placement = buyback_executor.getPlacementStatus()
    assert placement["canPlace"], "executor cannot place an order"
    assert not placement["isStonksCreationPaused"] and not placement["isStonksKilled"], "Stonks creation blocked"
    assert placement["sellAmount"] >= min_order_steth, "sell amount below the minimum order amount"

    place_order_tx = buyback_executor.placeOrder({"from": stranger})
    order = place_order_tx.return_value
    assert order is not None, "placeOrder returned no order"
    assert order != ZERO_ADDRESS, "placeOrder returned the zero address"
    order_placed = place_order_tx.events["OrderPlaced"]
    assert convert.to_address(order_placed["order"]) == convert.to_address(order), "OrderPlaced order mismatch"
    assert order_placed["sellAmount"] > 0 and order_placed["minBuyAmount"] > 0, "order has zero sell/buy amount"
    assert buyback_executor.lastOrderAddress() == order, "lastOrderAddress not updated"
    expected_valid_to = place_order_tx.timestamp + buyback_executor.stonksOrderDurationSeconds()
    assert buyback_executor.lastOrderValidTo() == expected_valid_to, "lastOrderValidTo not placement time + order duration"
    assert steth.balanceOf(order) >= order_placed["sellAmount"] - WEI_TOLERANCE, "order does not hold the sold stETH"


# ============================================================================
# ==================== LOL stablecoins Easy Track motions ====================
# ============================================================================
def _assert_setup_is_live(registry):
    """What the omnibus set up: the factories are registered and the executor holds the registry roles."""
    factories = contracts.easy_track.getEVMScriptFactories()
    for factory_address in LOL_STABLES_FACTORIES:
        assert factory_address in factories, f"{factory_address} not registered in Easy Track"
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, EVM_SCRIPT_EXECUTOR)
    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, EVM_SCRIPT_EXECUTOR)


def _start_fresh_spending_period(registry):
    """Move past the stored period so the next payment opens a fresh one with spent == 0.

    getPeriodState reports stored values, and every enacted motion advances the chain by the motion
    duration — without this a run near a period boundary would measure a rollover as an under-spend.
    """
    _, _, _, period_end = registry.getPeriodState()
    chain.mine(1, max(chain.time(), period_end) + 1)
    return period_end


def _fund_agent_with_dai(amount, accounts):
    """Top the Agent up to `amount` DAI through a DAI ward."""
    if contracts.dai_token.balanceOf(contracts.agent) < amount:
        interface.Dai(DAI_TOKEN).mint(contracts.agent, amount, {"from": accounts.at(DAI_WARD, force=True)})
    assert contracts.dai_token.balanceOf(contracts.agent) >= amount, "Insufficient DAI balance on Agent"


def test_lol_stables_motion_guards(vote_applied, stranger):
    """The factories reject unauthorized and out-of-bounds motions at creation."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    top_up_factory = interface.TopUpAllowedRecipients(LOL_STABLES_TOP_UP_FACTORY)
    add_recipient_factory = interface.AddAllowedRecipient(LOL_STABLES_ADD_RECIPIENT_FACTORY)
    remove_recipient_factory = interface.RemoveAllowedRecipient(LOL_STABLES_REMOVE_RECIPIENT_FACTORY)
    _assert_setup_is_live(registry)

    # only the LOL multisig can create motions
    assert_create_evm_script_reverts(
        top_up_factory,
        stranger,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [LOL_TRUSTED_CALLER], [1]]),
        "CALLER_IS_FORBIDDEN",
    )
    assert_create_evm_script_reverts(
        add_recipient_factory,
        stranger,
        _encode_calldata(["address", "string"], [stranger.address, "Stranger"]),
        "CALLER_IS_FORBIDDEN",
    )
    assert_create_evm_script_reverts(
        remove_recipient_factory,
        stranger,
        _encode_calldata(["address"], [LOL_TRUSTED_CALLER]),
        "CALLER_IS_FORBIDDEN",
    )

    # only tokens listed in the AllowedTokensRegistry
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [contracts.lido.address, [LOL_TRUSTED_CALLER], [1]]),
        "TOKEN_NOT_ALLOWED",
    )
    # only recipients the registry allows
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [stranger.address], [1]]),
        "RECIPIENT_NOT_ALLOWED",
    )
    # never more than the period limit
    limit, _ = registry.getLimitParameters()
    assert_create_evm_script_reverts(
        top_up_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(PAYMENT_CALLDATA_SIGNATURE, [DAI_TOKEN, [LOL_TRUSTED_CALLER], [limit + 1]]),
        "SUM_EXCEEDS_SPENDABLE_BALANCE",
    )

    # no duplicates in the recipients list, and nothing to remove that is not there
    assert_create_evm_script_reverts(
        add_recipient_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(["address", "string"], [LOL_TRUSTED_CALLER, "LOL multisig once more"]),
        "ALLOWED_RECIPIENT_ALREADY_ADDED",
    )
    assert_create_evm_script_reverts(
        remove_recipient_factory,
        LOL_TRUSTED_CALLER,
        _encode_calldata(["address"], [stranger.address]),
        "ALLOWED_RECIPIENT_NOT_FOUND",
    )


def test_lol_stables_add_and_remove_recipient(vote_applied, accounts, stranger):
    """Whitelist a recipient, pay it, drop it — all three factories in one flow."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    payment_amount = 1_000 * 10**18
    _fund_agent_with_dai(payment_amount, accounts)
    recipients_before = registry.getAllowedRecipients()
    _start_fresh_spending_period(registry)

    create_and_enact_add_recipient_motion(
        contracts.easy_track,
        multisig,
        registry,
        LOL_STABLES_ADD_RECIPIENT_FACTORY,
        stranger,
        "Stranger",
        stranger,
    )
    create_and_enact_payment_motion(
        contracts.easy_track,
        multisig,
        LOL_STABLES_TOP_UP_FACTORY,
        contracts.dai_token,
        [stranger],
        [payment_amount],
        stranger,
    )
    create_and_enact_remove_recipient_motion(
        contracts.easy_track,
        multisig,
        registry,
        LOL_STABLES_REMOVE_RECIPIENT_FACTORY,
        stranger,
        stranger,
    )

    spent_after, _, _, _ = registry.getPeriodState()
    assert spent_after == payment_amount, "the payment was not counted against the period limit"
    assert registry.getAllowedRecipients() == recipients_before, "the allowed recipients list was not restored"


def test_lol_stables_every_allowed_token_counts_against_the_limit(vote_applied, accounts, stranger):
    """Each token the shared registry allows can be paid out, and counts normalized to 18 decimals.

    USDC and USDT hold 6 decimals, so a factory that skipped normalizeAmount would let them spend
    orders of magnitude past the budget while the registry barely noticed.
    """
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    tokens_registry = interface.AllowedTokensRegistry(ALLOWED_TOKENS_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    allowed_tokens = tokens_registry.getAllowedTokens()
    assert len(allowed_tokens) > 0, "the shared tokens registry allows no tokens"
    _start_fresh_spending_period(registry)

    expected_spent = 0
    for token_address in allowed_tokens:
        token = interface.ERC20(token_address)
        payment_amount = 1_000 * 10 ** token.decimals()
        assert token.balanceOf(contracts.agent) >= payment_amount, f"Agent holds too little {token.symbol()}"

        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            token,
            [multisig],
            [payment_amount],
            stranger,
        )

        expected_spent += tokens_registry.normalizeAmount(payment_amount, token_address)
        spent, _, _, _ = registry.getPeriodState()
        assert spent == expected_spent, f"{token.symbol()} was not counted normalized to 18 decimals"


def test_lol_stables_single_payment_capped_by_acl(vote_applied, accounts, stranger):
    """A single newImmediatePayment cannot exceed the executor's ACL cap, even well under the limit."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    over_the_cap = FINANCE_DAI_MAX_PER_CALL + 1
    limit, _ = registry.getLimitParameters()
    assert over_the_cap < limit, "the ACL cap must bite before the period limit does"
    _fund_agent_with_dai(over_the_cap, accounts)
    _start_fresh_spending_period(registry)

    with reverts("APP_AUTH_FAILED"):
        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            contracts.dai_token,
            [multisig],
            [over_the_cap],
            stranger,
        )


def test_lol_stables_period_limit(vote_applied, accounts, stranger):
    """A whole period's limit can be spent — and not a wei more."""
    registry = interface.AllowedRecipientRegistry(LOL_STABLES_REGISTRY)
    multisig = accounts.at(LOL_TRUSTED_CALLER, force=True)
    _assert_setup_is_live(registry)

    limit, _ = registry.getLimitParameters()
    _fund_agent_with_dai(limit, accounts)
    period_end_before = _start_fresh_spending_period(registry)

    # the whole budget, as several payments batched into one motion, each within the ACL cap
    recipients = []
    amounts = []
    to_spend = limit
    while to_spend > 0:
        chunk_amount = min(FINANCE_DAI_MAX_PER_CALL, to_spend)
        recipients.append(multisig)
        amounts.append(chunk_amount)
        to_spend -= chunk_amount

    create_and_enact_payment_motion(
        contracts.easy_track,
        multisig,
        LOL_STABLES_TOP_UP_FACTORY,
        contracts.dai_token,
        recipients,
        amounts,
        stranger,
    )

    spent_after, spendable_after, _, period_end_after = registry.getPeriodState()
    assert period_end_after > period_end_before, "the spending period should have rolled over to a fresh one"
    assert spent_after == limit
    assert spendable_after == 0

    # not a single wei beyond the limit
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            contracts.easy_track,
            multisig,
            LOL_STABLES_TOP_UP_FACTORY,
            contracts.dai_token,
            [multisig],
            [1],
            stranger,
        )
