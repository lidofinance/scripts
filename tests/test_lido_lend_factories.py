from brownie import chain, interface
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
from utils.config import (
    EASYTRACK_LIDO_LEND_TRUSTED_CALLER,
    LIDO_LEND,
    LIDO_LEND_OWNER,
    LIDO_LEND_IRM_ROUTER,
    LIDO_LEND_ADAPTIVE_CURVE_IRM,
    LIDO_LEND_MARKET_FACTORY,
    LIDO_LEND_RISK_STEWARD_DASHBOARD,
    LIDO_LEND_CIRCUIT_BREAKER,
    LIDO_LEND_MORPHO_EXIT_BOOK,
    LIDO_LEND_ERC4626_EXIT_BOOK,
    LIDO_LEND_PRESEEDER,
    LIDO_LEND_WETH_WSTETH_MARKET,
)
from utils.test.lido_lend_helpers import (
    activate_market_via_motion,
    set_supply_cap_via_motion,
    add_guardian_via_motion,
    add_risk_steward_via_motion,
    set_pause_duration_via_motion,
    apply_irm_config_via_motion,
    allow_vault_in_erc4626_exit_book_via_motion,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_lido_lend_factories import (
    start_vote,
    get_vote_items,
    FACTORIES,
    EASY_TRACK,
    ACTIVATE_MARKET_FACTORY,
    CIRCUIT_BREAKER_ACTIONS_FACTORY,
    GUARDIAN_ACTIONS_FACTORY,
    MARKET_MANAGER_ACTIONS_FACTORY,
    RISK_STEWARD_ACTIONS_FACTORY,
    APPLY_IRM_CONFIG_FACTORY,
    EXIT_BOOK_ACTIONS_FACTORY,
)


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"


# ============================================================================
# ============================= Test params ==================================
# ============================================================================
EXPECTED_VOTE_ID = None
EXPECTED_VOTE_EVENTS_COUNT = 7
IPFS_DESCRIPTION_HASH = "bafkreib6qt5ccz43ohzpp3mc4wlaj327bmujnujgaje4qazdjtmyoartci"


def check_factory_bindings():
    activate_market = interface.LidoLendActivateMarket(ACTIVATE_MARKET_FACTORY)
    assert activate_market.lidoLend() == LIDO_LEND
    assert activate_market.lidoLendOwner() == LIDO_LEND_OWNER
    assert activate_market.irmRouter() == LIDO_LEND_IRM_ROUTER
    assert activate_market.configurableIrm() == LIDO_LEND_ADAPTIVE_CURVE_IRM
    assert activate_market.lidoLendMarketFactory() == LIDO_LEND_MARKET_FACTORY
    assert activate_market.circuitBreaker() == LIDO_LEND_CIRCUIT_BREAKER
    assert activate_market.riskStewardDashboard() == LIDO_LEND_RISK_STEWARD_DASHBOARD
    assert activate_market.lidoLendPreseeder() == LIDO_LEND_PRESEEDER

    circuit_breaker_actions = interface.LidoLendCircuitBreakerActions(CIRCUIT_BREAKER_ACTIONS_FACTORY)
    assert circuit_breaker_actions.lidoLend() == LIDO_LEND
    assert circuit_breaker_actions.circuitBreaker() == LIDO_LEND_CIRCUIT_BREAKER

    guardian_actions = interface.LidoLendGuardianActions(GUARDIAN_ACTIONS_FACTORY)
    assert guardian_actions.lidoLend() == LIDO_LEND
    assert guardian_actions.lidoLendOwner() == LIDO_LEND_OWNER

    market_manager_actions = interface.LidoLendMarketManagerActions(MARKET_MANAGER_ACTIONS_FACTORY)
    assert market_manager_actions.lidoLend() == LIDO_LEND
    assert market_manager_actions.lidoLendOwner() == LIDO_LEND_OWNER

    risk_steward_actions = interface.LidoLendRiskStewardActions(RISK_STEWARD_ACTIONS_FACTORY)
    assert risk_steward_actions.riskStewardDashboard() == LIDO_LEND_RISK_STEWARD_DASHBOARD

    apply_irm_config = interface.LidoLendApplyIrmConfig(APPLY_IRM_CONFIG_FACTORY)
    assert apply_irm_config.lidoLend() == LIDO_LEND
    assert apply_irm_config.irmRouter() == LIDO_LEND_IRM_ROUTER
    assert apply_irm_config.configurableIrm() == LIDO_LEND_ADAPTIVE_CURVE_IRM

    exit_book_actions = interface.LidoLendExitBookActions(EXIT_BOOK_ACTIONS_FACTORY)
    assert exit_book_actions.morphoExitBook() == LIDO_LEND_MORPHO_EXIT_BOOK
    assert exit_book_actions.erc4626ExitBook() == LIDO_LEND_ERC4626_EXIT_BOOK

    for _, factory, _ in FACTORIES:
        assert interface.LidoLendActivateMarket(factory).trustedCaller() == EASYTRACK_LIDO_LEND_TRUSTED_CALLER


def lido_lend_factories_smoke_test(easy_track, stranger):
    trusted_caller = set_balance(EASYTRACK_LIDO_LEND_TRUSTED_CALLER, 1000)
    market = LIDO_LEND_WETH_WSTETH_MARKET

    activate_market_via_motion(easy_track, trusted_caller, stranger, market)
    set_supply_cap_via_motion(easy_track, trusted_caller, stranger, market)
    add_guardian_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)
    add_risk_steward_via_motion(easy_track, trusted_caller, stranger, stranger.address, market)
    set_pause_duration_via_motion(easy_track, trusted_caller, stranger)
    apply_irm_config_via_motion(easy_track, trusted_caller, stranger, market["irm_config"], market)
    allow_vault_in_erc4626_exit_book_via_motion(easy_track, trusted_caller, stranger, market["vault"])


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    easy_track = interface.EasyTrack(EASY_TRACK)

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
        initial_factories = easy_track.getEVMScriptFactories()
        executor_before = easy_track.evmScriptExecutor()
        assert executor_before == EVM_SCRIPT_EXECUTOR

        for _, factory, _ in FACTORIES:
            assert factory not in initial_factories

        check_factory_bindings()

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)

        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        new_factories = easy_track.getEVMScriptFactories()
        assert len(new_factories) == len(initial_factories) + len(FACTORIES)
        assert new_factories[: len(initial_factories)] == initial_factories
        assert easy_track.evmScriptExecutor() == executor_before

        for _, factory, permissions in FACTORIES:
            assert factory in new_factories
            assert easy_track.isEVMScriptFactory(factory)
            assert str(easy_track.evmScriptFactoryPermissions(factory)).lower() == permissions.lower()

        # Happy path: every Lido Lend factory enacts a motion against the deployed protocol
        chain.snapshot()
        lido_lend_factories_smoke_test(easy_track, stranger)
        chain.revert()

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        for index, (_, factory, permissions) in enumerate(FACTORIES):
            validate_evmscript_factory_added_event(
                vote_events[index],
                EVMScriptFactoryAdded(factory_addr=factory, permissions=permissions),
                emitted_by=EASY_TRACK,
            )
