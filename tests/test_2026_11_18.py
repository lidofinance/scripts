from brownie import interface, reverts
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
)
from utils.evm_script import encode_call_script
from utils.test.event_validators.easy_track import (
    validate_evmscript_factory_added_event,
    EVMScriptFactoryAdded,
)
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.balance import set_balance

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
from scripts.vote_2026_11_18 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"

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

LIDO_LEND_WETH_WSTETH_MARKET = {
    "id": "<MARKET_ID>",
    "loan_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    "collateral_token": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",  # wstETH
    "oracle": "<ORACLE>",
    "irm": "0x81B7cC9523B30429110282d90db2fa90ff443d91",
    "irm_config": "<IRM_CONFIG>",
    "lltv": 0,  # <LLTV>
    "supply_cap": 0,  # <SUPPLY_CAP>
    "guardian_signals": "<GUARDIAN_SIGNALS>",
    "controller": "<CONTROLLER>",
    "vault": "<VAULT>",
    "steward": "0x1011E8a0668da8bbED925cB5A6DA5aa128C2BB5E",
    "fee": 0,  # <FEE>
    "enable_settlement": True,
}

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
EXPECTED_VOTE_ID = 207
EXPECTED_VOTE_EVENTS_COUNT = 6
IPFS_DESCRIPTION_HASH = ""


# ============================================================================
# ================================ Helpers ===================================
# ============================================================================
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


# ============================================================================
# ================================= Test =====================================
# ============================================================================
def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    easy_track = interface.EasyTrack(EASY_TRACK)
    check_factory_bindings()
    assert easy_track.evmScriptExecutor() == EVM_SCRIPT_EXECUTOR

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
        initial_factories = list(easy_track.getEVMScriptFactories())
        initial_permissions = [easy_track.evmScriptFactoryPermissions(factory) for factory in initial_factories]
        assert EXIT_BOOK_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(EXIT_BOOK_ACTIONS_FACTORY) == "0x"

        # 1. LidoLendActivateMarket
        assert ACTIVATE_MARKET_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(ACTIVATE_MARKET_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendActivateMarket(ACTIVATE_MARKET_FACTORY).createEVMScript(stranger, "0x")

        # 2. LidoLendCircuitBreakerActions
        assert CIRCUIT_BREAKER_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(CIRCUIT_BREAKER_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendCircuitBreakerActions(CIRCUIT_BREAKER_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 3. LidoLendGuardianActions
        assert GUARDIAN_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(GUARDIAN_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendGuardianActions(GUARDIAN_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 4. LidoLendMarketManagerActions
        assert MARKET_MANAGER_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(MARKET_MANAGER_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendMarketManagerActions(MARKET_MANAGER_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 5. LidoLendRiskStewardActions
        assert RISK_STEWARD_ACTIONS_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(RISK_STEWARD_ACTIONS_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendRiskStewardActions(RISK_STEWARD_ACTIONS_FACTORY).createEVMScript(stranger, "0x")

        # 6. LidoLendApplyIrmConfig
        assert APPLY_IRM_CONFIG_FACTORY not in initial_factories
        assert easy_track.evmScriptFactoryPermissions(APPLY_IRM_CONFIG_FACTORY) == "0x"
        with reverts("CALLER_IS_FORBIDDEN"):
            interface.LidoLendApplyIrmConfig(APPLY_IRM_CONFIG_FACTORY).createEVMScript(stranger, "0x")

        if IPFS_DESCRIPTION_HASH:
            assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

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

        # 1. LidoLendActivateMarket
        validate_evmscript_factory_added_event(
            vote_events[0],
            EVMScriptFactoryAdded(factory_addr=ACTIVATE_MARKET_FACTORY, permissions=ACTIVATE_MARKET_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

        # 2. LidoLendCircuitBreakerActions
        validate_evmscript_factory_added_event(
            vote_events[1],
            EVMScriptFactoryAdded(
                factory_addr=CIRCUIT_BREAKER_ACTIONS_FACTORY, permissions=CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 3. LidoLendGuardianActions
        validate_evmscript_factory_added_event(
            vote_events[2],
            EVMScriptFactoryAdded(factory_addr=GUARDIAN_ACTIONS_FACTORY, permissions=GUARDIAN_ACTIONS_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

        # 4. LidoLendMarketManagerActions
        validate_evmscript_factory_added_event(
            vote_events[3],
            EVMScriptFactoryAdded(
                factory_addr=MARKET_MANAGER_ACTIONS_FACTORY, permissions=MARKET_MANAGER_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 5. LidoLendRiskStewardActions
        validate_evmscript_factory_added_event(
            vote_events[4],
            EVMScriptFactoryAdded(
                factory_addr=RISK_STEWARD_ACTIONS_FACTORY, permissions=RISK_STEWARD_ACTIONS_PERMISSIONS
            ),
            emitted_by=EASY_TRACK,
        )

        # 6. LidoLendApplyIrmConfig
        validate_evmscript_factory_added_event(
            vote_events[5],
            EVMScriptFactoryAdded(factory_addr=APPLY_IRM_CONFIG_FACTORY, permissions=APPLY_IRM_CONFIG_PERMISSIONS),
            emitted_by=EASY_TRACK,
        )

    # =========================================================================
    # ======================= After vote executed checks ======================
    # =========================================================================
    assert voting.getVote(vote_id)["executed"]
    assert easy_track.evmScriptExecutor() == EVM_SCRIPT_EXECUTOR
    assert not easy_track.isEVMScriptFactory(EXIT_BOOK_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(EXIT_BOOK_ACTIONS_FACTORY) == "0x"

    # 1. LidoLendActivateMarket
    assert easy_track.isEVMScriptFactory(ACTIVATE_MARKET_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(ACTIVATE_MARKET_FACTORY) == ACTIVATE_MARKET_PERMISSIONS

    # 2. LidoLendCircuitBreakerActions
    assert easy_track.isEVMScriptFactory(CIRCUIT_BREAKER_ACTIONS_FACTORY)
    assert (
        easy_track.evmScriptFactoryPermissions(CIRCUIT_BREAKER_ACTIONS_FACTORY) == CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
    )

    # 3. LidoLendGuardianActions
    assert easy_track.isEVMScriptFactory(GUARDIAN_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(GUARDIAN_ACTIONS_FACTORY) == GUARDIAN_ACTIONS_PERMISSIONS

    # 4. LidoLendMarketManagerActions
    assert easy_track.isEVMScriptFactory(MARKET_MANAGER_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(MARKET_MANAGER_ACTIONS_FACTORY) == MARKET_MANAGER_ACTIONS_PERMISSIONS

    # 5. LidoLendRiskStewardActions
    assert easy_track.isEVMScriptFactory(RISK_STEWARD_ACTIONS_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(RISK_STEWARD_ACTIONS_FACTORY) == RISK_STEWARD_ACTIONS_PERMISSIONS

    # 6. LidoLendApplyIrmConfig
    assert easy_track.isEVMScriptFactory(APPLY_IRM_CONFIG_FACTORY)
    assert easy_track.evmScriptFactoryPermissions(APPLY_IRM_CONFIG_FACTORY) == APPLY_IRM_CONFIG_PERMISSIONS

    # =========================================================================
    # ======================= Lido Lend Easy Track motions =====================
    # =========================================================================
    trusted_caller = set_balance(EASYTRACK_LIDO_LEND_TRUSTED_CALLER, 1000)
    market = LIDO_LEND_WETH_WSTETH_MARKET
    assert not str(market["id"]).startswith(
        "<"
    ), "Fill LIDO_LEND_WETH_WSTETH_MARKET from the market deployment artifact"

    # 1. LidoLendActivateMarket
    activate_market_via_motion(easy_track, trusted_caller, stranger, market)

    # 2. LidoLendCircuitBreakerActions
    set_pause_duration_via_motion(easy_track, trusted_caller, stranger)

    # 3. LidoLendGuardianActions
    add_guardian_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)

    # 4. LidoLendMarketManagerActions
    set_supply_cap_via_motion(easy_track, trusted_caller, stranger, market)

    # 5. LidoLendRiskStewardActions
    add_risk_steward_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)

    # 6. LidoLendApplyIrmConfig
    apply_irm_config_via_motion(easy_track, trusted_caller, stranger, market["irm_config"], market)
