"""Lido Lend Easy Track motion scenarios shared by the vote test and the regression suite."""

from brownie import interface, web3
from eth_abi.abi import encode

from configs.config_mainnet import (
    LIDO_LEND,
    LIDO_LEND_CIRCUIT_BREAKER,
    LIDO_LEND_ADAPTIVE_CURVE_IRM,
    LIDO_LEND_IRM_ROUTER,
    LIDO_LEND_RISK_STEWARD_DASHBOARD,
    LIDO_LEND_ERC4626_EXIT_BOOK,
    LIDO_LEND_PAUSER_COMMITTEE_MS,
    LIDO_LEND_WETH_WSTETH_MARKET,
    EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY,
    EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY,
    EASYTRACK_LIDO_LEND_EXIT_BOOK_ACTIONS_FACTORY,
)
from utils.test.easy_track_helpers import create_and_enact_motion

MARKET_PARAMS_TYPE = "(address,address,address,address,uint256)"
ACTIVATION_PARAMS_TYPE = f"({MARKET_PARAMS_TYPE},address,address,bool,address,address,address,uint256)"

# Action enums of the factories, in declaration order
CIRCUIT_BREAKER_REGISTER_PAUSER, CIRCUIT_BREAKER_SET_PAUSE_DURATION, CIRCUIT_BREAKER_SET_HEARTBEAT_INTERVAL = range(3)
GUARDIAN_ADD, GUARDIAN_REMOVE, GUARDIAN_REPLACE, GUARDIAN_SET_QUORUM, GUARDIAN_SET_SUSPECT_WINDOW, GUARDIAN_UNBAN = (
    range(6)
)
(
    MARKET_SET_INSTANT_ACTIVATION,
    MARKET_SET_COLLATERAL_ACTIVATION_CONFIG,
    MARKET_SET_SETTLEMENT_CONFIG,
    MARKET_SET_SUPPLY_CAP,
    MARKET_UNFREEZE,
    MARKET_SET_FEE,
) = range(6)
RISK_STEWARD_ADD, RISK_STEWARD_REMOVE = range(2)
EXIT_BOOK_SET_MORPHO_ALLOWED, EXIT_BOOK_SET_ERC4626_ALLOWED = range(2)


def market_params(market=LIDO_LEND_WETH_WSTETH_MARKET):
    return (market["loan_token"], market["collateral_token"], market["oracle"], market["irm"], market["lltv"])


def market_id(market=LIDO_LEND_WETH_WSTETH_MARKET):
    return "0x" + bytes(web3.keccak(encode([MARKET_PARAMS_TYPE], [market_params(market)]))).hex()


def market_id_bytes(market=LIDO_LEND_WETH_WSTETH_MARKET):
    return bytes.fromhex(market_id(market)[2:])


def encode_action(action, payload_types, payload_values):
    payload = encode(payload_types, payload_values)
    return "0x" + encode(["uint8", "bytes"], [action, payload]).hex()


def encode_activate_market(market=LIDO_LEND_WETH_WSTETH_MARKET):
    params = (
        market_params(market),
        market["irm_config"],
        market["controller"],
        market["enable_settlement"],
        market["steward"],
        LIDO_LEND_PAUSER_COMMITTEE_MS,
        market["vault"],
        market["fee"],
    )
    return "0x" + encode([ACTIVATION_PARAMS_TYPE], [params]).hex()


def activate_market_via_motion(easy_track, trusted_caller, stranger, market=LIDO_LEND_WETH_WSTETH_MARKET):
    core = interface.LidoLend(LIDO_LEND)
    irm_router = interface.IrmRouter(LIDO_LEND_IRM_ROUTER)
    adaptive_curve_irm = interface.AdaptiveCurveIrm(LIDO_LEND_ADAPTIVE_CURVE_IRM)
    dashboard = interface.RiskStewardDashboard(LIDO_LEND_RISK_STEWARD_DASHBOARD)
    circuit_breaker = interface.CircuitBreaker(LIDO_LEND_CIRCUIT_BREAKER)
    vault = interface.LidoLendERC4626(market["vault"])
    current_market_id = market_id(market)
    assert current_market_id == market["id"].lower()

    assert core.market(current_market_id)["lastUpdate"] == 0

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY,
        encode_activate_market(market),
        stranger,
    )

    assert core.market(current_market_id)["lastUpdate"] != 0
    assert core.market(current_market_id)["fee"] == market["fee"]
    assert core.marketController(current_market_id) == market["controller"]
    assert core.isSettlementEnabled(current_market_id) == market["enable_settlement"]
    assert irm_router.marketIrm(current_market_id) == LIDO_LEND_ADAPTIVE_CURVE_IRM
    assert adaptive_curve_irm.marketCurveConfig(current_market_id) == market["irm_config"]
    assert dashboard.isMarketSteward(current_market_id, market["steward"])
    assert circuit_breaker.getPauser(market["controller"]) == LIDO_LEND_PAUSER_COMMITTEE_MS
    assert vault.totalSupply() > 0
    assert core.market(current_market_id)["totalSupplyAssets"] > 0


def set_supply_cap_via_motion(easy_track, trusted_caller, stranger, market=LIDO_LEND_WETH_WSTETH_MARKET):
    controller = interface.LidoLendMarketController(market["controller"])
    new_cap = controller.supplyCap() + 10**18

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(MARKET_SET_SUPPLY_CAP, ["bytes32", "uint256"], [market_id_bytes(market), new_cap]),
        stranger,
    )

    assert controller.supplyCap() == new_cap


def add_guardian_via_motion(easy_track, trusted_caller, stranger, guardian, market=LIDO_LEND_WETH_WSTETH_MARKET):
    guardian_signals = interface.GuardianSignals(market["guardian_signals"])
    quorum = guardian_signals.getQuorum()
    count = guardian_signals.getGuardianCount()
    assert not guardian_signals.isGuardian(guardian)

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(GUARDIAN_ADD, ["bytes32", "address", "uint256"], [market_id_bytes(market), guardian, quorum]),
        stranger,
    )

    assert guardian_signals.isGuardian(guardian)
    assert guardian_signals.getGuardianCount() == count + 1
    assert guardian_signals.getQuorum() == quorum


def add_risk_steward_via_motion(easy_track, trusted_caller, stranger, steward, market=LIDO_LEND_WETH_WSTETH_MARKET):
    dashboard = interface.RiskStewardDashboard(LIDO_LEND_RISK_STEWARD_DASHBOARD)
    assert not dashboard.isMarketSteward(market_id(market), steward)

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY,
        encode_action(RISK_STEWARD_ADD, ["bytes32", "address"], [market_id_bytes(market), steward]),
        stranger,
    )

    assert dashboard.isMarketSteward(market_id(market), steward)


def set_pause_duration_via_motion(easy_track, trusted_caller, stranger):
    circuit_breaker = interface.CircuitBreaker(LIDO_LEND_CIRCUIT_BREAKER)
    current = circuit_breaker.pauseDuration()
    new_duration = current + 1 if current < circuit_breaker.MAX_PAUSE_DURATION() else current - 1

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
        encode_action(CIRCUIT_BREAKER_SET_PAUSE_DURATION, ["uint256"], [new_duration]),
        stranger,
    )

    assert circuit_breaker.pauseDuration() == new_duration


def apply_irm_config_via_motion(easy_track, trusted_caller, stranger, irm_config, market=LIDO_LEND_WETH_WSTETH_MARKET):
    adaptive_curve_irm = interface.AdaptiveCurveIrm(LIDO_LEND_ADAPTIVE_CURVE_IRM)

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY,
        "0x" + encode(["bytes32", "address"], [market_id_bytes(market), irm_config]).hex(),
        stranger,
    )

    assert adaptive_curve_irm.marketCurveConfig(market_id(market)) == irm_config


def allow_vault_in_erc4626_exit_book_via_motion(easy_track, trusted_caller, stranger, vault):
    exit_book = interface.Erc4626ExitBook(LIDO_LEND_ERC4626_EXIT_BOOK)
    assert not exit_book.isVaultAllowed(vault)

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_EXIT_BOOK_ACTIONS_FACTORY,
        encode_action(EXIT_BOOK_SET_ERC4626_ALLOWED, ["address[]", "bool"], [[vault], True]),
        stranger,
    )

    assert exit_book.isVaultAllowed(vault)
