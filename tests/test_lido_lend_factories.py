import pytest
from brownie import chain, convert, history, interface, reverts
from brownie.network.event import EventDict
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import (
    add_event_emitter,
    tx_events_from_receipt,
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events,
)
from utils.dual_governance import PROPOSAL_STATUS, process_proposals
from utils.evm_script import encode_call_script, encode_error
from utils.test.event_validators.common import validate_events_chain
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.test.event_validators.permission import validate_grant_role_event
from utils.test.helpers import access_control_unauthorized
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.balance import set_balance
from utils.config import LIDO_LEND_WETH_WSTETH_MARKET

from utils.test.lido_lend_helpers import (
    activate_market_via_motion,
    set_supply_cap_via_motion,
    add_guardian_via_motion,
    add_risk_steward_via_motion,
    set_pause_duration_via_motion,
    apply_irm_config_via_motion,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_lido_lend_factories import start_vote, get_vote_items, get_dg_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"

# https://github.com/lidofinance/staking-modules/pull/918
CURATED_V2 = "0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1"
CURATED_V2_OLD_IMPL = "0x959fC67FE53c8A6C7a1AEd73430Aa07a36eD9337"
CURATED_V2_NEW_IMPL = "0x02bEFd784c6C382a021774472563671Ae23980C0"
CURATED_V2_PRE_UPGRADE_VERSION = 1
CURATED_V2_VERSION = 2
# https://docs.lido.fi/multisigs/committees#220-curated-module-committee-cmc
CURATED_MODULE_COMMITTEE = "0x2570e0b22AD904501dfB0d49575991ACB801dD91"
ENABLE_TOP_UP_ALLOCATION_ROLE_NAME = "ENABLE_TOP_UP_ALLOCATION_ROLE"
ENABLE_TOP_UP_ALLOCATION_ROLE = "0xf541c17eb0542b50d1f6df03622f7d9ab80d01dffb50bbd033a4dd4c57f09889"

EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
EASYTRACK_LIDO_LEND_TRUSTED_CALLER = "0x4f29aA4c299e17176b48c41D67ee97aE673d29bC"
LIDO_LEND = "0x026a770badc7126c7252Ef8d407E5b9C56147491"
LIDO_LEND_OWNER = "0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a"
LIDO_LEND_IRM_ROUTER = "0x81B7cC9523B30429110282d90db2fa90ff443d91"
LIDO_LEND_ADAPTIVE_CURVE_IRM = "0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f"
LIDO_LEND_MARKET_FACTORY = "0xBe1C1eaBda3eD8a93D3CE3246cf4EeF8111c76C7"
LIDO_LEND_RISK_STEWARD_DASHBOARD = "0xC3C241bC213EF3ba16234A7c689999209cE515D7"
LIDO_LEND_CIRCUIT_BREAKER = "0xd0A81A130a303237d338A0b5835edcB011Ab3afd"
LIDO_LEND_PRESEEDER = "0x3F107d1fbCA49F425321Cb27f6Ef5CbB94a72c41"
ACTIVATE_MARKET_FACTORY = "0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6"
CIRCUIT_BREAKER_ACTIONS_FACTORY = "0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8"
GUARDIAN_ACTIONS_FACTORY = "0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779"
MARKET_MANAGER_ACTIONS_FACTORY = "0x9D75EaE321976e85e472847AFD21246F1f87dC43"
RISK_STEWARD_ACTIONS_FACTORY = "0x7276CE5f92911216d41C7b0A9C3575DE873763E9"
APPLY_IRM_CONFIG_FACTORY = "0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668"
EXIT_BOOK_ACTIONS_FACTORY = "0xA30b212c3657fa745feaE4b48B7Eb0A8F429C604"

ACTIVATE_MARKET_PERMISSIONS = (
    "0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f2078614b"
    "81B7cC9523B30429110282d90db2fa90ff443d914451cfc5"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5abee60e2e"
    "C3C241bC213EF3ba16234A7c689999209cE515D7182d4cbb"
    "d0A81A130a303237d338A0b5835edcB011Ab3afd338d93fc"
    "3F107d1fbCA49F425321Cb27f6Ef5CbB94a72c419e90390c"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a2b4f013c"
)

CIRCUIT_BREAKER_ACTIONS_PERMISSIONS = (
    "0xd0A81A130a303237d338A0b5835edcB011Ab3afd338d93fc"
    "d0A81A130a303237d338A0b5835edcB011Ab3afdc9387332"
    "d0A81A130a303237d338A0b5835edcB011Ab3afd71a99c22"
)

GUARDIAN_ACTIONS_PERMISSIONS = (
    "0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a85431596"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5af3ad2cac"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a3cab947d"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5ad9101d17"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5adf03d75d"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a42abe0fd"
)

MARKET_MANAGER_ACTIONS_PERMISSIONS = (
    "0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a6835da96"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a084f4e3f"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a3d15094a"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5abf96eb01"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5ac49495df"
    "85378a1073E8f338e11A97E090E47e2F0FdD3D5a2b4f013c"
)

RISK_STEWARD_ACTIONS_PERMISSIONS = (
    "0xC3C241bC213EF3ba16234A7c689999209cE515D7182d4cbb" "C3C241bC213EF3ba16234A7c689999209cE515D79fdcc880"
)

APPLY_IRM_CONFIG_PERMISSIONS = (
    "0x026a770badc7126c7252Ef8d407E5b9C56147491151c1ade" "f6f1565F4fD3d29E6bDAb86764A50BCde381422f2078614b"
)


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_DG_PROPOSAL_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 7
EXPECTED_DG_EVENTS_FROM_AGENT = 2
EXPECTED_DG_EVENTS_COUNT = 2
IPFS_DESCRIPTION_HASH = "bafkreidd6tbexskyovsvkjiqtybyqkrqp6dogyvshe23yjeqomhkafobqm"
DG_PROPOSAL_METADATA = "Upgrade CMv2 to the implementation with top-up allocation controls"


def _event(events, name: str, emitted_by: str):
    assert events.count(name) == 1
    event = events[name]
    assert convert.to_address(event["_emitted_by"]) == convert.to_address(emitted_by)
    return event


def _top_up_allocation_eligible(operators) -> list:
    # CuratedModule.finalizeUpgradeV2 enables top-up allocation only for operators with non-withdrawn deposits.
    return [
        operator_id
        for operator_id, operator in enumerate(operators)
        if operator["totalDepositedKeys"] > operator["totalWithdrawnKeys"]
    ]


def curated_v2_top_up_allocation_smoke_test(curated_v2, stranger):
    committee = set_balance(CURATED_MODULE_COMMITTEE, 1000)
    operators_count = curated_v2.getNodeOperatorsCount()
    disabled = [
        operator_id for operator_id in range(operators_count) if not curated_v2.isTopUpAllocationEnabled(operator_id)
    ]
    assert disabled, "Expected at least one CMv2 operator with top-up allocation disabled"
    operator_id = disabled[0]

    with reverts(access_control_unauthorized(stranger, ENABLE_TOP_UP_ALLOCATION_ROLE_NAME)):
        curated_v2.enableTopUpAllocation(operator_id, {"from": stranger})

    tx = curated_v2.enableTopUpAllocation(operator_id, {"from": committee})
    # Brownie's tx.events leaves the proxied CMv2 event undecoded, so decode the receipt with the project ABIs.
    tx_events = EventDict([add_event_emitter(event) for event in tx_events_from_receipt(tx)])
    assert _event(tx_events, "TopUpAllocationEnabled", CURATED_V2)["nodeOperatorId"] == operator_id
    assert curated_v2.isTopUpAllocationEnabled(operator_id)

    with reverts(encode_error("TopUpAllocationStateUnchanged()")):
        curated_v2.enableTopUpAllocation(operator_id, {"from": committee})
    with reverts(encode_error("NodeOperatorDoesNotExist()")):
        curated_v2.enableTopUpAllocation(operators_count, {"from": committee})


def check_factory_bindings():
    activate_market = interface.LidoLendActivateMarket(ACTIVATE_MARKET_FACTORY)
    assert activate_market.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert activate_market.lidoLend() == LIDO_LEND
    assert activate_market.lidoLendOwner() == LIDO_LEND_OWNER
    assert activate_market.irmRouter() == LIDO_LEND_IRM_ROUTER
    assert activate_market.configurableIrm() == LIDO_LEND_ADAPTIVE_CURVE_IRM
    assert activate_market.lidoLendMarketFactory() == LIDO_LEND_MARKET_FACTORY
    assert activate_market.circuitBreaker() == LIDO_LEND_CIRCUIT_BREAKER
    assert activate_market.riskStewardDashboard() == LIDO_LEND_RISK_STEWARD_DASHBOARD
    assert activate_market.lidoLendPreseeder() == LIDO_LEND_PRESEEDER

    circuit_breaker_actions = interface.LidoLendCircuitBreakerActions(CIRCUIT_BREAKER_ACTIONS_FACTORY)
    assert circuit_breaker_actions.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert circuit_breaker_actions.lidoLend() == LIDO_LEND
    assert circuit_breaker_actions.circuitBreaker() == LIDO_LEND_CIRCUIT_BREAKER

    guardian_actions = interface.LidoLendGuardianActions(GUARDIAN_ACTIONS_FACTORY)
    assert guardian_actions.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert guardian_actions.lidoLend() == LIDO_LEND
    assert guardian_actions.lidoLendOwner() == LIDO_LEND_OWNER

    market_manager_actions = interface.LidoLendMarketManagerActions(MARKET_MANAGER_ACTIONS_FACTORY)
    assert market_manager_actions.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert market_manager_actions.lidoLend() == LIDO_LEND
    assert market_manager_actions.lidoLendOwner() == LIDO_LEND_OWNER

    risk_steward_actions = interface.LidoLendRiskStewardActions(RISK_STEWARD_ACTIONS_FACTORY)
    assert risk_steward_actions.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert risk_steward_actions.riskStewardDashboard() == LIDO_LEND_RISK_STEWARD_DASHBOARD

    apply_irm_config = interface.LidoLendApplyIrmConfig(APPLY_IRM_CONFIG_FACTORY)
    assert apply_irm_config.trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER
    assert apply_irm_config.lidoLend() == LIDO_LEND
    assert apply_irm_config.irmRouter() == LIDO_LEND_IRM_ROUTER
    assert apply_irm_config.configurableIrm() == LIDO_LEND_ADAPTIVE_CURVE_IRM


def lido_lend_factories_smoke_test(easy_track, stranger):
    trusted_caller = set_balance(EASYTRACK_LIDO_LEND_TRUSTED_CALLER, 1000)
    market = LIDO_LEND_WETH_WSTETH_MARKET

    assert not str(market["id"]).startswith(
        "<"
    ), "Fill LIDO_LEND_WETH_WSTETH_MARKET from the market deployment artifact"
    activate_market_via_motion(easy_track, trusted_caller, stranger, market)
    set_supply_cap_via_motion(easy_track, trusted_caller, stranger, market)
    add_guardian_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)
    add_risk_steward_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)
    set_pause_duration_via_motion(easy_track, trusted_caller, stranger)
    apply_irm_config_via_motion(easy_track, trusted_caller, stranger, market["irm_config"], market)


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():
    return [{"target": target, "value": 0, "data": data} for target, data in get_dg_items()]


def test_vote(
    helpers, accounts, ldo_holder, vote_ids_from_env, dg_proposal_ids_from_env, stranger, dual_governance_proposal_calls
):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    easy_track = interface.EasyTrack(EASY_TRACK)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    curated_v2 = interface.CuratedModule(CURATED_V2)
    curated_v2_proxy = interface.StakingModulesOssifiableProxy(CURATED_V2)

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
    assert len(call_script_items) == EXPECTED_VOTE_EVENTS_COUNT
    assert len(dual_governance_proposal_calls) == EXPECTED_DG_EVENTS_COUNT
    onchain_script = voting.getVote(vote_id)["script"]
    assert str(onchain_script).lower() == encode_call_script(call_script_items).lower()

    proposal_id = EXPECTED_DG_PROPOSAL_ID
    if dg_proposal_ids_from_env:
        assert len(dg_proposal_ids_from_env) == 1
        if proposal_id is not None:
            assert dg_proposal_ids_from_env[0] == proposal_id
        proposal_id = dg_proposal_ids_from_env[0]

    assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH
    check_factory_bindings()
    assert easy_track.evmScriptExecutor() == EVM_SCRIPT_EXECUTOR

    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================
        initial_factories = list(easy_track.getEVMScriptFactories())
        initial_permissions = [easy_track.evmScriptFactoryPermissions(factory) for factory in initial_factories]
        assert EXIT_BOOK_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(EXIT_BOOK_ACTIONS_FACTORY) == "0x"

        # 2. ActivateMarket
        assert ACTIVATE_MARKET_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(ACTIVATE_MARKET_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendActivateMarket(ACTIVATE_MARKET_FACTORY).createEVMScript(stranger, "0x")

        # 3. CircuitBreakerActions
        assert CIRCUIT_BREAKER_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(CIRCUIT_BREAKER_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendCircuitBreakerActions(CIRCUIT_BREAKER_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 4. GuardianActions
        assert GUARDIAN_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(GUARDIAN_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendGuardianActions(GUARDIAN_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 5. MarketManagerActions
        assert MARKET_MANAGER_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(MARKET_MANAGER_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendMarketManagerActions(MARKET_MANAGER_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 6. RiskStewardActions
        assert RISK_STEWARD_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(RISK_STEWARD_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendRiskStewardActions(RISK_STEWARD_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 7. ApplyIrmConfig
        assert APPLY_IRM_CONFIG_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(APPLY_IRM_CONFIG_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendApplyIrmConfig(APPLY_IRM_CONFIG_FACTORY).createEVMScript(stranger, "0x")

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        assert list(easy_track.getEVMScriptFactories()) == initial_factories + [
            ACTIVATE_MARKET_FACTORY,
            CIRCUIT_BREAKER_ACTIONS_FACTORY,
            GUARDIAN_ACTIONS_FACTORY,
            MARKET_MANAGER_ACTIONS_FACTORY,
            RISK_STEWARD_ACTIONS_FACTORY,
            APPLY_IRM_CONFIG_FACTORY,
        ]
        assert [easy_track.evmScriptFactoryPermissions(factory) for factory in initial_factories] == initial_permissions
        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        # 1. Submit the CMv2 upgrade Dual Governance proposal
        submitted_id = vote_events[0]["ProposalSubmitted"][0]["id"]
        if proposal_id is not None:
            assert submitted_id == proposal_id
        proposal_id = submitted_id
        assert proposal_id == timelock.getProposalsCount()
        validate_dual_governance_submit_event(
            vote_events[0],
            proposal_id=proposal_id,
            proposer=VOTING,
            executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
            metadata=DG_PROPOSAL_METADATA,
            proposal_calls=dual_governance_proposal_calls,
        )

        # 2. ActivateMarket
        validate_evmscript_factory_added_event(
            vote_events[1],
            EVMScriptFactoryAdded(factory_addr=ACTIVATE_MARKET_FACTORY, permissions=ACTIVATE_MARKET_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

        # 3. CircuitBreakerActions
        validate_evmscript_factory_added_event(
            vote_events[2],
            EVMScriptFactoryAdded(
                factory_addr=CIRCUIT_BREAKER_ACTIONS_FACTORY, permissions=CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 4. GuardianActions
        validate_evmscript_factory_added_event(
            vote_events[3],
            EVMScriptFactoryAdded(factory_addr=GUARDIAN_ACTIONS_FACTORY, permissions=GUARDIAN_ACTIONS_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

        # 5. MarketManagerActions
        validate_evmscript_factory_added_event(
            vote_events[4],
            EVMScriptFactoryAdded(
                factory_addr=MARKET_MANAGER_ACTIONS_FACTORY, permissions=MARKET_MANAGER_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 6. RiskStewardActions
        validate_evmscript_factory_added_event(
            vote_events[5],
            EVMScriptFactoryAdded(
                factory_addr=RISK_STEWARD_ACTIONS_FACTORY, permissions=RISK_STEWARD_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 7. ApplyIrmConfig
        validate_evmscript_factory_added_event(
            vote_events[6],
            EVMScriptFactoryAdded(factory_addr=APPLY_IRM_CONFIG_FACTORY, permissions=APPLY_IRM_CONFIG_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

    assert proposal_id is not None, "Set EXPECTED_DG_PROPOSAL_ID or DG_PROPOSAL_IDS for the already-executed vote."

    # =========================================================================
    # ======================= Execute DG Proposal =============================
    # =========================================================================
    if timelock.getProposalDetails(proposal_id)["status"] != PROPOSAL_STATUS["executed"]:
        # =========================================================================
        # ================== DG before proposal executed checks ===================
        # =========================================================================
        assert curated_v2_proxy.proxy__getImplementation() == CURATED_V2_OLD_IMPL
        assert curated_v2_proxy.proxy__getAdmin() == AGENT
        assert curated_v2.getInitializedVersion() == CURATED_V2_PRE_UPGRADE_VERSION
        assert curated_v2.getRoleMemberCount(ENABLE_TOP_UP_ALLOCATION_ROLE) == 0
        nonce_before = curated_v2.getNonce()
        operators = [curated_v2.getNodeOperator(i) for i in range(curated_v2.getNodeOperatorsCount())]
        eligible_operators = _top_up_allocation_eligible(operators)
        assert eligible_operators, "Expected CMv2 operators with active validators"

        process_proposals([proposal_id])
        dg_tx: TransactionReceipt = history[-1]
        display_dg_events(dg_tx)
        dg_events = group_dg_events_from_receipt(
            dg_tx, timelock=EMERGENCY_PROTECTED_TIMELOCK, admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR
        )
        assert count_vote_items_by_events(dg_tx, AGENT) == EXPECTED_DG_EVENTS_FROM_AGENT
        assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

        # 1.1.1. Upgrade CMv2 and call finalizeUpgradeV2() atomically.
        validate_events_chain(
            [event.name for event in dg_events[0]],
            [
                "LogScriptCall",
                "Upgraded",
                *["TopUpAllocationEnabled"] * len(eligible_operators),
                "NonceChanged",
                "Initialized",
                "ScriptResult",
                "Executed",
            ],
        )
        assert _event(dg_events[0], "Upgraded", CURATED_V2)["implementation"] == CURATED_V2_NEW_IMPL
        top_up_enabled_events = dg_events[0]["TopUpAllocationEnabled"]
        assert [event["nodeOperatorId"] for event in top_up_enabled_events] == eligible_operators
        for event in top_up_enabled_events:
            assert convert.to_address(event["_emitted_by"]) == CURATED_V2
        assert _event(dg_events[0], "NonceChanged", CURATED_V2)["nonce"] == nonce_before + 1
        assert _event(dg_events[0], "Initialized", CURATED_V2)["version"] == CURATED_V2_VERSION

        # 1.2.1. Grant ENABLE_TOP_UP_ALLOCATION_ROLE to the Curated Module Committee.
        validate_grant_role_event(
            dg_events[1],
            ENABLE_TOP_UP_ALLOCATION_ROLE,
            CURATED_MODULE_COMMITTEE,
            sender=AGENT,
            emitted_by=CURATED_V2,
            event_chain=["LogScriptCall", "RoleGranted", "ScriptResult", "Executed"],
        )

        # =========================================================================
        # ================== DG after proposal executed checks ====================
        # =========================================================================
        assert curated_v2.getNonce() == nonce_before + 1
        for operator_id in range(len(operators)):
            assert curated_v2.isTopUpAllocationEnabled(operator_id) == (operator_id in eligible_operators)

    # =========================================================================
    # ======================= After vote executed checks ======================
    # =========================================================================
    assert voting.getVote(vote_id)["executed"]
    assert timelock.getProposalDetails(proposal_id)["status"] == PROPOSAL_STATUS["executed"]
    assert easy_track.evmScriptExecutor() == EVM_SCRIPT_EXECUTOR
    assert not easy_track.isEVMScriptFactory(EXIT_BOOK_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(EXIT_BOOK_ACTIONS_FACTORY) == "0x"

    # 1.1.1. CMv2 runs the new implementation under the same proxy admin.
    assert curated_v2_proxy.proxy__getImplementation() == CURATED_V2_NEW_IMPL
    assert curated_v2_proxy.proxy__getAdmin() == AGENT
    assert curated_v2.getInitializedVersion() == CURATED_V2_VERSION

    # 1.2.1. Only the Curated Module Committee holds ENABLE_TOP_UP_ALLOCATION_ROLE.
    assert curated_v2.getRoleMemberCount(ENABLE_TOP_UP_ALLOCATION_ROLE) == 1
    assert curated_v2.hasRole(ENABLE_TOP_UP_ALLOCATION_ROLE, CURATED_MODULE_COMMITTEE)

    # 2. ActivateMarket
    assert easy_track.isEVMScriptFactory(ACTIVATE_MARKET_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(ACTIVATE_MARKET_FACTORY) == ACTIVATE_MARKET_PERMISSIONS

    # 3. CircuitBreakerActions
    assert easy_track.isEVMScriptFactory(CIRCUIT_BREAKER_ACTIONS_FACTORY)
    assert (
        easy_track.evmScriptFactoryPermissions(CIRCUIT_BREAKER_ACTIONS_FACTORY) == CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
    )

    # 4. GuardianActions
    assert easy_track.isEVMScriptFactory(GUARDIAN_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(GUARDIAN_ACTIONS_FACTORY) == GUARDIAN_ACTIONS_PERMISSIONS

    # 5. MarketManagerActions
    assert easy_track.isEVMScriptFactory(MARKET_MANAGER_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(MARKET_MANAGER_ACTIONS_FACTORY) == MARKET_MANAGER_ACTIONS_PERMISSIONS

    # 6. RiskStewardActions
    assert easy_track.isEVMScriptFactory(RISK_STEWARD_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(RISK_STEWARD_ACTIONS_FACTORY) == RISK_STEWARD_ACTIONS_PERMISSIONS

    # 7. ApplyIrmConfig
    assert easy_track.isEVMScriptFactory(APPLY_IRM_CONFIG_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(APPLY_IRM_CONFIG_FACTORY) == APPLY_IRM_CONFIG_PERMISSIONS

    chain.snapshot()
    try:
        curated_v2_top_up_allocation_smoke_test(curated_v2, stranger)
    finally:
        chain.revert()

    chain.snapshot()
    try:
        lido_lend_factories_smoke_test(easy_track, stranger)
    finally:
        chain.revert()
