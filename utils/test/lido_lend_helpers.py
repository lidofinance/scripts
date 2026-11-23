"""Lido Lend Easy Track motion scenarios shared by the vote test and the regression suite."""

from brownie import InvalidAdaptiveCurveConfigStub, chain, convert, history, interface, reverts, web3
from eth_abi.abi import encode

from configs.config_mainnet import (
    AGENT,
    LIDO_LEND,
    LIDO_LEND_IRM_CONFIG_FACTORY,
    LIDO_LEND_CIRCUIT_BREAKER,
    LIDO_LEND_ADAPTIVE_CURVE_IRM,
    LIDO_LEND_IRM_ROUTER,
    LIDO_LEND_RISK_STEWARD_DASHBOARD,
    LIDO_LEND_PAUSER_COMMITTEE_MS,
    LIDO_LEND_WETH_WSTETH_MARKET,
    EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY,
    EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY,
)
from utils.balance import set_balance
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

    events = history[-1].events["IrmConfigApplied"]
    assert len(events) == 1
    assert convert.to_address(events[0].address) == adaptive_curve_irm.address
    assert events[0]["marketId"] == market_id(market)
    assert events[0]["config"] == irm_config
    assert adaptive_curve_irm.marketCurveConfig(market_id(market)) == irm_config


def apply_new_irm_config_with_accrual(easy_track, trusted_caller, borrower, market=LIDO_LEND_WETH_WSTETH_MARKET):
    core = interface.LidoLend(LIDO_LEND)
    irm = interface.AdaptiveCurveIrm(LIDO_LEND_ADAPTIVE_CURVE_IRM)
    mid = market_id(market)
    params = market_params(market)
    old_config = irm.marketCurveConfig(mid)
    old_curve = interface.AdaptiveCurveConfig(old_config).getCurveParams()
    new_curve = list(old_curve)
    new_curve[2] = 8 * 10**17  # Move target utilization from 90% to 80%.
    assert old_curve[2] == 9 * 10**17
    factory = interface.IrmConfigFactory(LIDO_LEND_IRM_CONFIG_FACTORY)
    factory.getOrDeployAdaptiveCurveConfig(new_curve, {"from": borrower})
    new_config = factory.getAdaptiveCurveConfig(new_curve)
    assert new_config != old_config
    assert list(interface.AdaptiveCurveConfig(new_config).getCurveParams()) == new_curve

    # At exactly the old target, adaptation is zero and the old rate stays constant.
    # This gives an independent interest expectation for the entire motion delay.
    assert core.market(mid)["totalBorrowAssets"] == 0
    assert interface.LidoLendMarketController(market["controller"]).hasInstantActivation(borrower)
    weth = interface.WethToken(market["loan_token"])
    collateral = interface.WstETH(market["collateral_token"])
    top_up = 100 * 10**18 - core.market(mid)["totalSupplyAssets"]
    weth.deposit({"from": borrower, "value": top_up})
    weth.approve(core, top_up, {"from": borrower})
    core.supply(params, top_up, 0, borrower, b"", {"from": borrower})
    collateral_before = collateral.balanceOf(borrower)
    borrower.transfer(collateral, 200 * 10**18)
    collateral_amount = collateral.balanceOf(borrower) - collateral_before
    collateral.approve(core, collateral_amount, {"from": borrower})
    core.supplyCollateral(params, collateral_amount, borrower, b"", {"from": borrower})
    core.borrow(params, 90 * 10**18, 0, borrower, borrower, {"from": borrower})
    before = core.market(mid)
    assert before["totalBorrowAssets"] * 10**18 // before["totalSupplyAssets"] == old_curve[2]
    expected_rate = irm.rateAtTarget(mid)
    if old_curve[6]:
        expected_rate = min(expected_rate, old_curve[6])
    assert expected_rate > 0
    assert irm.borrowRateView(params, before) == expected_rate

    apply_irm_config_via_motion(easy_track, trusted_caller, borrower, new_config, market)
    tx = history[-1]
    elapsed = tx.timestamp - before["lastUpdate"]
    assert elapsed > 0
    first = expected_rate * elapsed
    second = first * first // (2 * 10**18)
    third = second * first // (3 * 10**18)
    expected_interest = before["totalBorrowAssets"] * (first + second + third) // 10**18
    assert expected_interest > 0
    accruals = tx.events["AccrueInterest"]
    assert len(accruals) == 1
    accrual = accruals[0]
    assert convert.to_address(accrual.address) == core.address
    assert accrual["id"] == mid
    assert accrual["prevBorrowRate"] == expected_rate
    assert accrual["interest"] == expected_interest
    assert accrual.pos < tx.events["IrmConfigApplied"][0].pos
    after = core.market(mid)
    assert after["totalBorrowAssets"] == before["totalBorrowAssets"] + expected_interest
    assert after["totalSupplyAssets"] == before["totalSupplyAssets"] + expected_interest
    assert after["totalBorrowShares"] == before["totalBorrowShares"]
    assert after["lastUpdate"] == tx.timestamp
    assert list(interface.AdaptiveCurveConfig(irm.marketCurveConfig(mid)).getCurveParams()) == new_curve
    assert irm.borrowRateView(params, after) != expected_rate


def _assert_division_by_zero(contract, calldata, caller):
    # Brownie's Hardhat middleware drops panic return data; inspect the raw RPC response.
    response = web3.provider.make_request(
        "eth_call", [{"from": caller.address, "to": contract.address, "data": calldata}, "latest"]
    )
    assert "error" in response, response
    data = response["error"]["data"]
    if isinstance(data, dict):
        data = data.get("data", data.get("result"))
    assert data == "0x4e487b71" + encode(["uint256"], [0x12]).hex()


def invalid_irm_config_and_owner_recovery(easy_track, trusted_caller, stranger, market=LIDO_LEND_WETH_WSTETH_MARKET):
    core = interface.LidoLend(LIDO_LEND)
    irm = interface.AdaptiveCurveIrm(LIDO_LEND_ADAPTIVE_CURVE_IRM)
    mid = market_id(market)
    params = market_params(market)
    good_config = irm.marketCurveConfig(mid)
    assert core.market(mid)["totalBorrowAssets"] == 0
    invalid = InvalidAdaptiveCurveConfigStub.deploy({"from": stranger})
    assert list(interface.AdaptiveCurveConfig(invalid).getCurveParams()) == [0] * 7

    # Real factory motion accepts the ABI-compatible but invalid configuration.
    apply_irm_config_via_motion(easy_track, trusted_caller, stranger, invalid.address, market)
    chain.mine(1, chain.time() + 1)
    _assert_division_by_zero(core, core.accrueInterest.encode_input(params), stranger)
    _assert_division_by_zero(irm, irm.borrowRateView.encode_input(params, core.market(mid)), stranger)

    # The same factory cannot repair it: it accrues using the broken old config first.
    calldata = "0x" + encode(["bytes32", "address"], [market_id_bytes(market), good_config]).hex()
    created = easy_track.createMotion(EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY, calldata, {"from": trusted_caller})
    motion = easy_track.getMotions()[-1]
    chain.mine(1, motion[4] + motion[3] + 1)
    before = core.market(mid)
    _assert_division_by_zero(
        easy_track,
        easy_track.enactMotion.encode_input(motion[0], created.events["MotionCreated"]["_evmScriptCallData"]),
        stranger,
    )
    assert irm.marketCurveConfig(mid) == invalid.address
    assert core.market(mid) == before
    assert any(pending[0] == motion[0] for pending in easy_track.getMotions())

    # The DAO Agent can recover directly without reading the old configuration.
    with reverts("not authorized"):
        irm.applyIrmConfig(params, good_config, {"from": stranger})
    assert irm.owner() == AGENT
    irm.applyIrmConfig(params, good_config, {"from": set_balance(AGENT, 1000)})
    assert irm.marketCurveConfig(mid) == good_config
    assert irm.borrowRateView(params, core.market(mid)) > 0
    recovered = core.accrueInterest(params, {"from": stranger})
    assert core.market(mid)["lastUpdate"] == recovered.timestamp
    assert len(recovered.events["AccrueInterest"]) == 1
    easy_track.enactMotion(motion[0], created.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger})
    assert irm.marketCurveConfig(mid) == good_config
    assert not any(pending[0] == motion[0] for pending in easy_track.getMotions())


def circuit_breaker_actions_via_motions(easy_track, trusted_caller, stranger, market=LIDO_LEND_WETH_WSTETH_MARKET):
    circuit_breaker = interface.CircuitBreaker(LIDO_LEND_CIRCUIT_BREAKER)
    assert circuit_breaker.getPauser(market["controller"]) != stranger.address
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
        encode_action(
            CIRCUIT_BREAKER_REGISTER_PAUSER, ["bytes32", "address"], [market_id_bytes(market), stranger.address]
        ),
        stranger,
    )
    assert circuit_breaker.getPauser(market["controller"]) == stranger.address

    set_pause_duration_via_motion(easy_track, trusted_caller, stranger)

    current = circuit_breaker.heartbeatInterval()
    interval = current + 1 if current < circuit_breaker.MAX_HEARTBEAT_INTERVAL() else current - 1
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
        encode_action(CIRCUIT_BREAKER_SET_HEARTBEAT_INTERVAL, ["uint256"], [interval]),
        stranger,
    )
    assert circuit_breaker.heartbeatInterval() == interval


def guardian_actions_via_motions(
    easy_track, trusted_caller, stranger, replacement, market=LIDO_LEND_WETH_WSTETH_MARKET
):
    signals = interface.GuardianSignals(market["guardian_signals"])
    initial_quorum = signals.getQuorum()
    initial_count = signals.getGuardianCount()
    add_guardian_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)

    # The launch quorum is one. Flag a fresh account so UnbanAccounts changes state.
    assert initial_quorum == 1
    assert not signals.isBanned(market_id(market), replacement)
    signals.flag(market_id(market), stranger.address, [replacement], {"from": stranger})
    assert signals.isBanned(market_id(market), replacement)
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(GUARDIAN_UNBAN, ["(address,bytes32[])[]"], [[(replacement, [market_id_bytes(market)])]]),
        stranger,
    )
    assert not signals.isBanned(market_id(market), replacement)

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(GUARDIAN_SET_QUORUM, ["bytes32", "uint256"], [market_id_bytes(market), initial_quorum + 1]),
        stranger,
    )
    assert signals.getQuorum() == initial_quorum + 1

    current = signals.getSuspectWindow()
    window = current + 1 if current < signals.MAX_SUSPECT_WINDOW() else current - 1
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(GUARDIAN_SET_SUSPECT_WINDOW, ["bytes32", "uint256"], [market_id_bytes(market), window]),
        stranger,
    )
    assert signals.getSuspectWindow() == window

    assert not signals.isGuardian(replacement)
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(
            GUARDIAN_REPLACE,
            ["bytes32", "address", "address"],
            [market_id_bytes(market), stranger.address, replacement],
        ),
        stranger,
    )
    assert not signals.isGuardian(stranger.address)
    assert signals.isGuardian(replacement)
    assert signals.getGuardianCount() == initial_count + 1
    assert signals.getQuorum() == initial_quorum + 1

    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
        encode_action(
            GUARDIAN_REMOVE, ["bytes32", "address", "uint256"], [market_id_bytes(market), replacement, initial_quorum]
        ),
        stranger,
    )
    assert not signals.isGuardian(replacement)
    assert signals.getGuardianCount() == initial_count
    assert signals.getQuorum() == initial_quorum


def market_manager_actions_via_motions(
    easy_track, trusted_caller, stranger, steward, market=LIDO_LEND_WETH_WSTETH_MARKET
):
    controller = interface.LidoLendMarketController(market["controller"])
    core = interface.LidoLend(LIDO_LEND)
    enabled = not controller.hasInstantActivation(stranger.address)
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(
            MARKET_SET_INSTANT_ACTIVATION,
            ["bytes32", "address", "bool"],
            [market_id_bytes(market), stranger.address, enabled],
        ),
        stranger,
    )
    assert controller.hasInstantActivation(stranger.address) == enabled

    activation_config = list(controller.collateralActivationConfig())
    activation_config[2] += 1  # maxDelayInflow; keep all delay and dust constraints unchanged.
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(
            MARKET_SET_COLLATERAL_ACTIVATION_CONFIG,
            ["bytes32", "(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40)"],
            [market_id_bytes(market), activation_config],
        ),
        stranger,
    )
    assert list(controller.collateralActivationConfig()) == activation_config

    settlement_config = list(controller.settlementConfig())
    settlement_config[1] += 1  # sliceFloorAssets
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(
            MARKET_SET_SETTLEMENT_CONFIG,
            ["bytes32", "(uint16,uint96,uint96,uint16)"],
            [market_id_bytes(market), settlement_config],
        ),
        stranger,
    )
    assert list(controller.settlementConfig()) == settlement_config

    set_supply_cap_via_motion(easy_track, trusted_caller, stranger, market)

    assert not controller.isFrozen()
    dashboard = interface.RiskStewardDashboard(LIDO_LEND_RISK_STEWARD_DASHBOARD)
    dashboard.freezeMarket(market_id(market), {"from": steward})
    assert controller.isFrozen()
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(MARKET_UNFREEZE, ["bytes32[]"], [[market_id_bytes(market)]]),
        stranger,
    )
    assert not controller.isFrozen()

    fee = 0 if core.market(market_id(market))["fee"] != 0 else 10**16
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
        encode_action(MARKET_SET_FEE, ["bytes32", "uint256"], [market_id_bytes(market), fee]),
        stranger,
    )
    assert core.market(market_id(market))["fee"] == fee


def risk_steward_actions_via_motions(easy_track, trusted_caller, stranger, market=LIDO_LEND_WETH_WSTETH_MARKET):
    dashboard = interface.RiskStewardDashboard(LIDO_LEND_RISK_STEWARD_DASHBOARD)
    add_risk_steward_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)
    create_and_enact_motion(
        easy_track,
        trusted_caller,
        EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY,
        encode_action(RISK_STEWARD_REMOVE, ["bytes32", "address"], [market_id_bytes(market), stranger.address]),
        stranger,
    )
    assert not dashboard.isMarketSteward(market_id(market), stranger.address)
