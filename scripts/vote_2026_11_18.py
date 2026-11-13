"""
Vote 2026_11_18

1. Add LidoLendActivateMarket EVM script factory 0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6 with applyIrmConfig permission on AdaptiveCurveIrm 0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f, setMarketIrm permission on IrmRouter 0x81B7cC9523B30429110282d90db2fa90ff443d91, createMarket and setFee permissions on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a, addMarketSteward permission on RiskStewardDashboard 0xC3C241bC213EF3ba16234A7c689999209cE515D7, registerPauser permission on CircuitBreaker 0xd0A81A130a303237d338A0b5835edcB011Ab3afd, and preseedMarket permission on LidoLendPreseeder 0x3F107d1fbCA49F425321Cb27f6Ef5CbB94a72c41 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.
2. Add LidoLendCircuitBreakerActions EVM script factory 0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8 with registerPauser, setPauseDuration and setHeartbeatInterval permissions on CircuitBreaker 0xd0A81A130a303237d338A0b5835edcB011Ab3afd to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.
3. Add LidoLendGuardianActions EVM script factory 0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779 with addGuardian, setGuardiansQuorum, removeGuardian, replaceGuardian, setGuardiansSuspectWindow and unbanGuardianSignals permissions on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.
4. Add LidoLendMarketManagerActions EVM script factory 0x9D75EaE321976e85e472847AFD21246F1f87dC43 with setInstantActivation, setMarketCollateralActivationConfig, setMarketSettlementConfig, setMarketSupplyCap, unfreezeMarket and setFee permissions on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.
5. Add LidoLendRiskStewardActions EVM script factory 0x7276CE5f92911216d41C7b0A9C3575DE873763E9 with addMarketSteward and removeMarketSteward permissions on RiskStewardDashboard 0xC3C241bC213EF3ba16234A7c689999209cE515D7 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.
6. Add LidoLendApplyIrmConfig EVM script factory 0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668 with accrueInterest permission on LidoLend 0x026a770badc7126c7252Ef8d407E5b9C56147491 and applyIrmConfig permission on AdaptiveCurveIrm 0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.

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
    LIDO_LEND,
    LIDO_LEND_OWNER,
    LIDO_LEND_ADAPTIVE_CURVE_IRM,
    LIDO_LEND_IRM_ROUTER,
    LIDO_LEND_RISK_STEWARD_DASHBOARD,
    LIDO_LEND_CIRCUIT_BREAKER,
    LIDO_LEND_PRESEEDER,
)
from utils.mainnet_fork import pass_and_exec_dao_vote
from utils.easy_track import add_evmscript_factory


# ============================== Constants ===================================
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


def permissions(*entries: Tuple[str, str]) -> str:
    """Easy Track permissions: concatenated (target address ++ function selector) entries."""
    return "0x" + "".join(target[2:] + selector[2:] for target, selector in entries)


ACTIVATE_MARKET_PERMISSIONS = permissions(
    (LIDO_LEND_ADAPTIVE_CURVE_IRM, IRM_APPLY_IRM_CONFIG),
    (LIDO_LEND_IRM_ROUTER, IRM_ROUTER_SET_MARKET_IRM),
    (LIDO_LEND_OWNER, OWNER_CREATE_MARKET),
    (LIDO_LEND_RISK_STEWARD_DASHBOARD, DASHBOARD_ADD_MARKET_STEWARD),
    (LIDO_LEND_CIRCUIT_BREAKER, CIRCUIT_BREAKER_REGISTER_PAUSER),
    (LIDO_LEND_PRESEEDER, PRESEEDER_PRESEED_MARKET),
    (LIDO_LEND_OWNER, OWNER_SET_FEE),
)
CIRCUIT_BREAKER_ACTIONS_PERMISSIONS = permissions(
    (LIDO_LEND_CIRCUIT_BREAKER, CIRCUIT_BREAKER_REGISTER_PAUSER),
    (LIDO_LEND_CIRCUIT_BREAKER, CIRCUIT_BREAKER_SET_PAUSE_DURATION),
    (LIDO_LEND_CIRCUIT_BREAKER, CIRCUIT_BREAKER_SET_HEARTBEAT_INTERVAL),
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
    (LIDO_LEND_RISK_STEWARD_DASHBOARD, DASHBOARD_ADD_MARKET_STEWARD),
    (LIDO_LEND_RISK_STEWARD_DASHBOARD, DASHBOARD_REMOVE_MARKET_STEWARD),
)
APPLY_IRM_CONFIG_PERMISSIONS = permissions(
    (LIDO_LEND, LIDO_LEND_ACCRUE_INTEREST),
    (LIDO_LEND_ADAPTIVE_CURVE_IRM, IRM_APPLY_IRM_CONFIG),
)
# ============================= IPFS Description ==================================
IPFS_DESCRIPTION = """
# Lido Lend Easy Track factories

1. **Add Lido Lend Easy Track factories for market activation and management, Guardian and Risk Steward management, Circuit Breaker configuration, and IRM updates**, [as proposed on the forum](<FORUM_URL>). Audits: [report](<AUDIT_URL>). Deployment verification: [report](<DEPLOYMENT_VERIFICATION_URL>). Items 1–6.
"""


# ================================ Main ======================================
def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    vote_desc_items, call_script_items = zip(
        (
            "1. Add LidoLendActivateMarket EVM script factory 0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6 with "
            "applyIrmConfig permission on AdaptiveCurveIrm 0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f, setMarketIrm "
            "permission on IrmRouter 0x81B7cC9523B30429110282d90db2fa90ff443d91, createMarket and setFee permissions "
            "on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a, addMarketSteward permission on "
            "RiskStewardDashboard 0xC3C241bC213EF3ba16234A7c689999209cE515D7, registerPauser permission on "
            "CircuitBreaker 0xd0A81A130a303237d338A0b5835edcB011Ab3afd, and preseedMarket permission on "
            "LidoLendPreseeder 0x3F107d1fbCA49F425321Cb27f6Ef5CbB94a72c41 to Easy Track "
            "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY, ACTIVATE_MARKET_PERMISSIONS),
        ),
        (
            "2. Add LidoLendCircuitBreakerActions EVM script factory 0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8 with "
            "registerPauser, setPauseDuration and setHeartbeatInterval permissions on CircuitBreaker "
            "0xd0A81A130a303237d338A0b5835edcB011Ab3afd to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(
                EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY, CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
            ),
        ),
        (
            "3. Add LidoLendGuardianActions EVM script factory 0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779 with "
            "addGuardian, setGuardiansQuorum, removeGuardian, replaceGuardian, setGuardiansSuspectWindow and "
            "unbanGuardianSignals permissions on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a to Easy "
            "Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY, GUARDIAN_ACTIONS_PERMISSIONS),
        ),
        (
            "4. Add LidoLendMarketManagerActions EVM script factory 0x9D75EaE321976e85e472847AFD21246F1f87dC43 with "
            "setInstantActivation, setMarketCollateralActivationConfig, setMarketSettlementConfig, setMarketSupplyCap, "
            "unfreezeMarket and setFee permissions on LidoLendOwner 0x85378a1073E8f338e11A97E090E47e2F0FdD3D5a to Easy "
            "Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(
                EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY, MARKET_MANAGER_ACTIONS_PERMISSIONS
            ),
        ),
        (
            "5. Add LidoLendRiskStewardActions EVM script factory 0x7276CE5f92911216d41C7b0A9C3575DE873763E9 with "
            "addMarketSteward and removeMarketSteward permissions on RiskStewardDashboard "
            "0xC3C241bC213EF3ba16234A7c689999209cE515D7 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY, RISK_STEWARD_ACTIONS_PERMISSIONS),
        ),
        (
            "6. Add LidoLendApplyIrmConfig EVM script factory 0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668 with "
            "accrueInterest permission on LidoLend 0x026a770badc7126c7252Ef8d407E5b9C56147491 and applyIrmConfig "
            "permission on AdaptiveCurveIrm 0xf6f1565F4fD3d29E6bDAb86764A50BCde381422f to Easy Track "
            "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea.",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY, APPLY_IRM_CONFIG_PERMISSIONS),
        ),
    )

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
