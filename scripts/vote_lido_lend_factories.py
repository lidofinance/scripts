"""
Vote 2026_MM_DD

1. Add Lido Lend ActivateMarket EVM script factory <ACTIVATE_MARKET_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: AdaptiveCurveIrm.applyIrmConfig, IrmRouter.setMarketIrm, LidoLendOwner.createMarket, RiskStewardDashboard.addMarketSteward, CircuitBreaker.registerPauser, LidoLendPreseeder.preseedMarket, LidoLendOwner.setFee)
2. Add Lido Lend CircuitBreakerActions EVM script factory <CIRCUIT_BREAKER_ACTIONS_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: CircuitBreaker.registerPauser, CircuitBreaker.setPauseDuration, CircuitBreaker.setHeartbeatInterval)
3. Add Lido Lend GuardianActions EVM script factory <GUARDIAN_ACTIONS_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLendOwner.addGuardian, LidoLendOwner.setGuardiansQuorum, LidoLendOwner.removeGuardian, LidoLendOwner.replaceGuardian, LidoLendOwner.setGuardiansSuspectWindow, LidoLendOwner.unbanGuardianSignals)
4. Add Lido Lend MarketManagerActions EVM script factory <MARKET_MANAGER_ACTIONS_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLendOwner.setInstantActivation, LidoLendOwner.setMarketCollateralActivationConfig, LidoLendOwner.setMarketSettlementConfig, LidoLendOwner.setMarketSupplyCap, LidoLendOwner.unfreezeMarket, LidoLendOwner.setFee)
5. Add Lido Lend RiskStewardActions EVM script factory <RISK_STEWARD_ACTIONS_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: RiskStewardDashboard.addMarketSteward, RiskStewardDashboard.removeMarketSteward)
6. Add Lido Lend ApplyIrmConfig EVM script factory <APPLY_IRM_CONFIG_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLend.accrueInterest, AdaptiveCurveIrm.applyIrmConfig)
7. Add Lido Lend ExitBookActions EVM script factory <EXIT_BOOK_ACTIONS_FACTORY> to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: MorphoExitBook.setMarketAllowed, Erc4626ExitBook.setVaultAllowed)

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from typing import Dict, List, Tuple

from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY,
    EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY,
    EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY,
    EASYTRACK_LIDO_LEND_EXIT_BOOK_ACTIONS_FACTORY,
    LIDO_LEND,
    LIDO_LEND_OWNER,
    LIDO_LEND_ADAPTIVE_CURVE_IRM,
    LIDO_LEND_IRM_ROUTER,
    LIDO_LEND_RISK_STEWARD_DASHBOARD,
    LIDO_LEND_CIRCUIT_BREAKER,
    LIDO_LEND_MORPHO_EXIT_BOOK,
    LIDO_LEND_ERC4626_EXIT_BOOK,
    LIDO_LEND_PRESEEDER,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.easy_track import add_evmscript_factory


# ============================== Constants ===================================
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"

# Lido Lend EVM script factories (easy-track `et-lido-lend-deployed-mainnet-1-<block>.json`)
ACTIVATE_MARKET_FACTORY = EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY
CIRCUIT_BREAKER_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY
GUARDIAN_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY
MARKET_MANAGER_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY
RISK_STEWARD_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY
APPLY_IRM_CONFIG_FACTORY = EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY
EXIT_BOOK_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_EXIT_BOOK_ACTIONS_FACTORY

# Lido Lend permission targets (lend-markets `deployed/mainnet/`)
ADAPTIVE_CURVE_IRM = LIDO_LEND_ADAPTIVE_CURVE_IRM
IRM_ROUTER = LIDO_LEND_IRM_ROUTER
RISK_STEWARD_DASHBOARD = LIDO_LEND_RISK_STEWARD_DASHBOARD
CIRCUIT_BREAKER = LIDO_LEND_CIRCUIT_BREAKER
MORPHO_EXIT_BOOK = LIDO_LEND_MORPHO_EXIT_BOOK
ERC4626_EXIT_BOOK = LIDO_LEND_ERC4626_EXIT_BOOK

# Function selectors for permissions
LIDO_LEND_ACCRUE_INTEREST = "0x151c1ade"  # accrueInterest((address,address,address,address,uint256))
OWNER_CREATE_MARKET = "0xbee60e2e"  # createMarket((address,address,address,address,uint256),address,bool)
OWNER_SET_FEE = "0x2b4f013c"  # setFee((address,address,address,address,uint256),uint256)
OWNER_ADD_GUARDIAN = "0x85431596"  # addGuardian(bytes32,address)
OWNER_SET_GUARDIANS_QUORUM = "0xf3ad2cac"  # setGuardiansQuorum(bytes32,uint256)
OWNER_REMOVE_GUARDIAN = "0x3cab947d"  # removeGuardian(bytes32,address)
OWNER_REPLACE_GUARDIAN = "0xd9101d17"  # replaceGuardian(bytes32,address,address)
OWNER_SET_GUARDIANS_SUSPECT_WINDOW = "0xdf03d75d"  # setGuardiansSuspectWindow(bytes32,uint256)
OWNER_UNBAN_GUARDIAN_SIGNALS = "0x42abe0fd"  # unbanGuardianSignals(bytes32[],address)
OWNER_SET_INSTANT_ACTIVATION = "0x6835da96"  # setInstantActivation(bytes32,address,bool)
OWNER_SET_MARKET_COLLATERAL_ACTIVATION_CONFIG = "0x084f4e3f"  # setMarketCollateralActivationConfig(bytes32,(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40))
OWNER_SET_MARKET_SETTLEMENT_CONFIG = "0x3d15094a"  # setMarketSettlementConfig(bytes32,(uint16,uint96,uint96,uint16))
OWNER_SET_MARKET_SUPPLY_CAP = "0xbf96eb01"  # setMarketSupplyCap(bytes32,uint256)
OWNER_UNFREEZE_MARKET = "0xc49495df"  # unfreezeMarket(bytes32)
IRM_APPLY_IRM_CONFIG = "0x2078614b"  # applyIrmConfig((address,address,address,address,uint256),address)
IRM_ROUTER_SET_MARKET_IRM = "0x4451cfc5"  # setMarketIrm((address,address,address,address,uint256),address)
DASHBOARD_ADD_MARKET_STEWARD = "0x182d4cbb"  # addMarketSteward(bytes32,address)
DASHBOARD_REMOVE_MARKET_STEWARD = "0x9fdcc880"  # removeMarketSteward(bytes32,address)
CIRCUIT_BREAKER_REGISTER_PAUSER = "0x338d93fc"  # registerPauser(address,address)
CIRCUIT_BREAKER_SET_PAUSE_DURATION = "0xc9387332"  # setPauseDuration(uint256)
CIRCUIT_BREAKER_SET_HEARTBEAT_INTERVAL = "0x71a99c22"  # setHeartbeatInterval(uint256)
PRESEEDER_PRESEED_MARKET = "0x9e90390c"  # preseedMarket((address,address,address,address,uint256),address)
MORPHO_EXIT_BOOK_SET_MARKET_ALLOWED = "0xaf2a4133"  # setMarketAllowed((address,address,address,address,uint256),bool)
ERC4626_EXIT_BOOK_SET_VAULT_ALLOWED = "0xab05a1e3"  # setVaultAllowed(address,bool)


def permissions(*entries: Tuple[str, str]) -> str:
    """Easy Track permissions: concatenated (target address ++ function selector) entries."""
    return "0x" + "".join(target[2:] + selector[2:] for target, selector in entries)


ACTIVATE_MARKET_PERMISSIONS = permissions(
    (ADAPTIVE_CURVE_IRM, IRM_APPLY_IRM_CONFIG),
    (IRM_ROUTER, IRM_ROUTER_SET_MARKET_IRM),
    (LIDO_LEND_OWNER, OWNER_CREATE_MARKET),
    (RISK_STEWARD_DASHBOARD, DASHBOARD_ADD_MARKET_STEWARD),
    (CIRCUIT_BREAKER, CIRCUIT_BREAKER_REGISTER_PAUSER),
    (LIDO_LEND_PRESEEDER, PRESEEDER_PRESEED_MARKET),
    (LIDO_LEND_OWNER, OWNER_SET_FEE),
)
CIRCUIT_BREAKER_ACTIONS_PERMISSIONS = permissions(
    (CIRCUIT_BREAKER, CIRCUIT_BREAKER_REGISTER_PAUSER),
    (CIRCUIT_BREAKER, CIRCUIT_BREAKER_SET_PAUSE_DURATION),
    (CIRCUIT_BREAKER, CIRCUIT_BREAKER_SET_HEARTBEAT_INTERVAL),
)
GUARDIAN_ACTIONS_PERMISSIONS = permissions(
    (LIDO_LEND_OWNER, OWNER_ADD_GUARDIAN),
    (LIDO_LEND_OWNER, OWNER_SET_GUARDIANS_QUORUM),
    (LIDO_LEND_OWNER, OWNER_REMOVE_GUARDIAN),
    (LIDO_LEND_OWNER, OWNER_REPLACE_GUARDIAN),
    (LIDO_LEND_OWNER, OWNER_SET_GUARDIANS_SUSPECT_WINDOW),
    (LIDO_LEND_OWNER, OWNER_UNBAN_GUARDIAN_SIGNALS),
)
MARKET_MANAGER_ACTIONS_PERMISSIONS = permissions(
    (LIDO_LEND_OWNER, OWNER_SET_INSTANT_ACTIVATION),
    (LIDO_LEND_OWNER, OWNER_SET_MARKET_COLLATERAL_ACTIVATION_CONFIG),
    (LIDO_LEND_OWNER, OWNER_SET_MARKET_SETTLEMENT_CONFIG),
    (LIDO_LEND_OWNER, OWNER_SET_MARKET_SUPPLY_CAP),
    (LIDO_LEND_OWNER, OWNER_UNFREEZE_MARKET),
    (LIDO_LEND_OWNER, OWNER_SET_FEE),
)
RISK_STEWARD_ACTIONS_PERMISSIONS = permissions(
    (RISK_STEWARD_DASHBOARD, DASHBOARD_ADD_MARKET_STEWARD),
    (RISK_STEWARD_DASHBOARD, DASHBOARD_REMOVE_MARKET_STEWARD),
)
APPLY_IRM_CONFIG_PERMISSIONS = permissions(
    (LIDO_LEND, LIDO_LEND_ACCRUE_INTEREST),
    (ADAPTIVE_CURVE_IRM, IRM_APPLY_IRM_CONFIG),
)
EXIT_BOOK_ACTIONS_PERMISSIONS = permissions(
    (MORPHO_EXIT_BOOK, MORPHO_EXIT_BOOK_SET_MARKET_ALLOWED),
    (ERC4626_EXIT_BOOK, ERC4626_EXIT_BOOK_SET_VAULT_ALLOWED),
)

# (vote item name, factory, permissions) in vote order
FACTORIES: List[Tuple[str, str, str]] = [
    ("ActivateMarket", ACTIVATE_MARKET_FACTORY, ACTIVATE_MARKET_PERMISSIONS),
    ("CircuitBreakerActions", CIRCUIT_BREAKER_ACTIONS_FACTORY, CIRCUIT_BREAKER_ACTIONS_PERMISSIONS),
    ("GuardianActions", GUARDIAN_ACTIONS_FACTORY, GUARDIAN_ACTIONS_PERMISSIONS),
    ("MarketManagerActions", MARKET_MANAGER_ACTIONS_FACTORY, MARKET_MANAGER_ACTIONS_PERMISSIONS),
    ("RiskStewardActions", RISK_STEWARD_ACTIONS_FACTORY, RISK_STEWARD_ACTIONS_PERMISSIONS),
    ("ApplyIrmConfig", APPLY_IRM_CONFIG_FACTORY, APPLY_IRM_CONFIG_PERMISSIONS),
    ("ExitBookActions", EXIT_BOOK_ACTIONS_FACTORY, EXIT_BOOK_ACTIONS_PERMISSIONS),
]


# ============================= IPFS Description ==================================
# TODO forum link
IPFS_DESCRIPTION = """
1. **Add Lido Lend Easy Track factories**, [as proposed on the forum](<FORUM_LINK>). Audit & deployment verification: TODO. Items 1-7.
"""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items = []
    call_script_items = []

    for index, (name, factory, factory_permissions) in enumerate(FACTORIES, start=1):
        vote_desc_items.append(
            f"{index}. Add Lido Lend {name} EVM script factory {factory} to Easy Track {EASY_TRACK} "
            f"(permissions: {factory_permissions})"
        )
        call_script_items.append(add_evmscript_factory(factory, factory_permissions))

    return vote_desc_items, call_script_items


def start_vote(tx_params: Dict[str, str], silent: bool = False):
    vote_desc_items, call_script_items = get_vote_items()
    vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))

    desc_ipfs = (
        calculate_vote_ipfs_description(IPFS_DESCRIPTION) if silent else upload_vote_ipfs_description(IPFS_DESCRIPTION)
    )

    vote_id, tx = confirm_vote_script(vote_items, silent, desc_ipfs) and list(
        create_vote(vote_items, tx_params, desc_ipfs=desc_ipfs)
    )

    return vote_id, tx


def main():
    tx_params: Dict[str, str] = {"from": get_deployer_account().address}
    if get_is_live():
        tx_params["priority_fee"] = get_priority_fee()

    vote_id, _ = start_vote(tx_params=tx_params, silent=False)
    vote_id >= 0 and print(f"Vote created: {vote_id}.")


def start_and_execute_vote_on_fork_manual():
    if get_is_live():
        raise Exception("This script is for local testing only.")

    tx_params = {"from": get_deployer_account()}
    vote_id, _ = start_vote(tx_params=tx_params, silent=True)
    print(f"Vote created: {vote_id}.")
    pass_and_exec_dao_vote(int(vote_id), step_by_step=True)
