"""
Vote 2026_MM_DD

1. Submit a Dual Governance proposal to upgrade CMv2 to the implementation with top-up allocation controls and connect the CMv2 internal ConsolidationMigrator to the ConsolidationBus
    1.1.1. Upgrade CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1 to implementation 0x02bEFd784c6C382a021774472563671Ae23980C0 and call finalizeUpgradeV2()
    1.2.1. Grant ENABLE_TOP_UP_ALLOCATION_ROLE 0xf541c17eb0542b50d1f6df03622f7d9ab80d01dffb50bbd033a4dd4c57f09889 to Curated Module Committee 0x2570e0b22AD904501dfB0d49575991ACB801dD91 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.3.1. Grant PUBLISH_ROLE 0xf3156f38966c62e303ac6c7519c63e00636409e3b3ca4abecd13cd0092fee53e to CMv2 internal ConsolidationMigrator 0xc8a7F4917cA03FDCD24a5E11A48Ab448318976e7 on ConsolidationBus 0xd907CE33B4Be423823d1CFFe80BD147E8b8554C8
2. Add Lido Lend ActivateMarket EVM script factory 0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: AdaptiveCurveIrm.applyIrmConfig, IrmRouter.setMarketIrm, LidoLendOwner.createMarket, RiskStewardDashboard.addMarketSteward, CircuitBreaker.registerPauser, LidoLendPreseeder.preseedMarket, LidoLendOwner.setFee)
3. Add Lido Lend CircuitBreakerActions EVM script factory 0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: CircuitBreaker.registerPauser, CircuitBreaker.setPauseDuration, CircuitBreaker.setHeartbeatInterval)
4. Add Lido Lend GuardianActions EVM script factory 0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLendOwner.addGuardian, LidoLendOwner.setGuardiansQuorum, LidoLendOwner.removeGuardian, LidoLendOwner.replaceGuardian, LidoLendOwner.setGuardiansSuspectWindow, LidoLendOwner.unbanGuardianSignals)
5. Add Lido Lend MarketManagerActions EVM script factory 0x9D75EaE321976e85e472847AFD21246F1f87dC43 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLendOwner.setInstantActivation, LidoLendOwner.setMarketCollateralActivationConfig, LidoLendOwner.setMarketSettlementConfig, LidoLendOwner.setMarketSupplyCap, LidoLendOwner.unfreezeMarket, LidoLendOwner.setFee)
6. Add Lido Lend RiskStewardActions EVM script factory 0x7276CE5f92911216d41C7b0A9C3575DE873763E9 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: RiskStewardDashboard.addMarketSteward, RiskStewardDashboard.removeMarketSteward)
7. Add Lido Lend ApplyIrmConfig EVM script factory 0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: LidoLend.accrueInterest, AdaptiveCurveIrm.applyIrmConfig)

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from typing import Dict, List, Tuple

from brownie import interface

from utils.agent import agent_forward
from utils.dual_governance import submit_proposals
from utils.permissions import encode_oz_grant_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    CURATED_V2_STAKING_MODULE_ADDRESS,
    CURATED_V2_COMMITTEE_MS,
    CONSOLIDATION_BUS,
    CONSOLIDATION_MIGRATOR_CMV2,
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
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"

# CMv2 implementation with top-up allocation controls
CURATED_V2 = CURATED_V2_STAKING_MODULE_ADDRESS
CURATED_V2_NEW_IMPL = "0x02bEFd784c6C382a021774472563671Ae23980C0"
CURATED_V2_TOP_UP_ALLOCATION_ENABLER = CURATED_V2_COMMITTEE_MS

# ConsolidationMigrator with CMv2 as both the source and the target module
CMV2_INTERNAL_MIGRATOR = CONSOLIDATION_MIGRATOR_CMV2

# Lido Lend EVM script factories (easy-track `lido-lend-factories-mainnet.json`)
ACTIVATE_MARKET_FACTORY = EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY
CIRCUIT_BREAKER_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY
GUARDIAN_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY
MARKET_MANAGER_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY
RISK_STEWARD_ACTIONS_FACTORY = EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY
APPLY_IRM_CONFIG_FACTORY = EASYTRACK_LIDO_LEND_APPLY_IRM_CONFIG_FACTORY

# Lido Lend permission targets (lend-markets `deployed/mainnet/`)
ADAPTIVE_CURVE_IRM = LIDO_LEND_ADAPTIVE_CURVE_IRM
IRM_ROUTER = LIDO_LEND_IRM_ROUTER
RISK_STEWARD_DASHBOARD = LIDO_LEND_RISK_STEWARD_DASHBOARD
CIRCUIT_BREAKER = LIDO_LEND_CIRCUIT_BREAKER

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
# ============================= IPFS Description ==================================
# TODO forum link
IPFS_DESCRIPTION = """
# CMv2 top-up allocation controls, CMv2 internal consolidation, Lido Lend Easy Track factories

1. **Upgrade CMv2 to the implementation with top-up allocation controls**, [as proposed on the forum](<FORUM_LINK>). Audit & deployment verification: TODO. Items 1.1.1, 1.2.1.
    - Upgrade CMv2 and enable top-up allocation for node operators with active validators. Item 1.1.1.
    - Allow the [Curated Module Committee](https://docs.lido.fi/multisigs/committees#220-curated-module-committee-cmc) to enable top-up allocation for node operators. Item 1.2.1.
2. **Connect the CMv2 internal ConsolidationMigrator to the ConsolidationBus**, so that Curated Module v2 node operators can consolidate validators inside CMv2, [as proposed on the forum](<FORUM_LINK>). Deployment verification: TODO. Item 1.3.1.
3. **Add Lido Lend Easy Track factories**, [as proposed on the forum](<FORUM_LINK>). Audit & deployment verification: TODO. Items 2-7.
"""

DG_PROPOSAL_METADATA = (
    "Upgrade CMv2 to the implementation with top-up allocation controls, "
    "connect the CMv2 internal ConsolidationMigrator to the ConsolidationBus"
)
DG_SUBMISSION_DESCRIPTION = (
    "1. Submit a Dual Governance proposal to upgrade CMv2 to the implementation with top-up allocation controls "
    "and connect the CMv2 internal ConsolidationMigrator to the ConsolidationBus"
)


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    # staking-modules OssifiableProxy (OZ v5): proxy__upgradeToAndCall(address,bytes), without forceCall_.
    curated_v2_proxy = interface.StakingModulesOssifiableProxy(CURATED_V2)
    curated_v2 = interface.CuratedModule(CURATED_V2)
    consolidation_bus = interface.ConsolidationBus(CONSOLIDATION_BUS)

    return [
        # 1.1.1. Upgrade CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1 to implementation
        # 0x02bEFd784c6C382a021774472563671Ae23980C0 and call finalizeUpgradeV2().
        # finalizeUpgradeV2() must run atomically with the upgrade: it bumps the initialized version to 2,
        # enables top-up allocation for operators with totalDepositedKeys > totalWithdrawnKeys and bumps the nonce.
        agent_forward(
            [
                (
                    curated_v2_proxy.address,
                    curated_v2_proxy.proxy__upgradeToAndCall.encode_input(
                        CURATED_V2_NEW_IMPL,
                        curated_v2.finalizeUpgradeV2.encode_input(),
                    ),
                )
            ]
        ),
        # 1.2.1. Grant ENABLE_TOP_UP_ALLOCATION_ROLE 0xf541c17eb0542b50d1f6df03622f7d9ab80d01dffb50bbd033a4dd4c57f09889
        # to Curated Module Committee 0x2570e0b22AD904501dfB0d49575991ACB801dD91 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=curated_v2,
                    role_name="ENABLE_TOP_UP_ALLOCATION_ROLE",
                    grant_to=CURATED_V2_TOP_UP_ALLOCATION_ENABLER,
                )
            ]
        ),
        # 1.3.1. Grant PUBLISH_ROLE 0xf3156f38966c62e303ac6c7519c63e00636409e3b3ca4abecd13cd0092fee53e
        # to CMv2 internal ConsolidationMigrator 0xc8a7F4917cA03FDCD24a5E11A48Ab448318976e7
        # on ConsolidationBus 0xd907CE33B4Be423823d1CFFe80BD147E8b8554C8.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=consolidation_bus,
                    role_name="PUBLISH_ROLE",
                    grant_to=CMV2_INTERNAL_MIGRATOR,
                )
            ]
        ),
    ]


def get_vote_items() -> Tuple[List[str], List[Tuple[str, str]]]:
    dg_call_script, *_ = submit_proposals([(get_dg_items(), DG_PROPOSAL_METADATA)])

    vote_desc_items, call_script_items = zip(
        (
            DG_SUBMISSION_DESCRIPTION,
            dg_call_script,
        ),
        (
            f"2. Add Lido Lend ActivateMarket EVM script factory {ACTIVATE_MARKET_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {ACTIVATE_MARKET_PERMISSIONS})",
            add_evmscript_factory(ACTIVATE_MARKET_FACTORY, ACTIVATE_MARKET_PERMISSIONS),
        ),
        (
            f"3. Add Lido Lend CircuitBreakerActions EVM script factory {CIRCUIT_BREAKER_ACTIONS_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {CIRCUIT_BREAKER_ACTIONS_PERMISSIONS})",
            add_evmscript_factory(CIRCUIT_BREAKER_ACTIONS_FACTORY, CIRCUIT_BREAKER_ACTIONS_PERMISSIONS),
        ),
        (
            f"4. Add Lido Lend GuardianActions EVM script factory {GUARDIAN_ACTIONS_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {GUARDIAN_ACTIONS_PERMISSIONS})",
            add_evmscript_factory(GUARDIAN_ACTIONS_FACTORY, GUARDIAN_ACTIONS_PERMISSIONS),
        ),
        (
            f"5. Add Lido Lend MarketManagerActions EVM script factory {MARKET_MANAGER_ACTIONS_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {MARKET_MANAGER_ACTIONS_PERMISSIONS})",
            add_evmscript_factory(MARKET_MANAGER_ACTIONS_FACTORY, MARKET_MANAGER_ACTIONS_PERMISSIONS),
        ),
        (
            f"6. Add Lido Lend RiskStewardActions EVM script factory {RISK_STEWARD_ACTIONS_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {RISK_STEWARD_ACTIONS_PERMISSIONS})",
            add_evmscript_factory(RISK_STEWARD_ACTIONS_FACTORY, RISK_STEWARD_ACTIONS_PERMISSIONS),
        ),
        (
            f"7. Add Lido Lend ApplyIrmConfig EVM script factory {APPLY_IRM_CONFIG_FACTORY} to Easy Track {EASY_TRACK} "
            f"(permissions: {APPLY_IRM_CONFIG_PERMISSIONS})",
            add_evmscript_factory(APPLY_IRM_CONFIG_FACTORY, APPLY_IRM_CONFIG_PERMISSIONS),
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
