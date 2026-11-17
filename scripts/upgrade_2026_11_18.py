"""
Vote 2026_11_18

1. Submit a proposal to Dual Governance 0xc1db28b3301331277e307fdcff8de28242a4486e
    1.1.1. Upgrade CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1 to implementation 0x02bEFd784c6C382a021774472563671Ae23980C0 and call finalizeUpgradeV2() with setupCalldata_ = 0x88984a97
    1.2.1. Grant ENABLE_TOP_UP_ALLOCATION_ROLE 0xf541c17eb0542b50d1f6df03622f7d9ab80d01dffb50bbd033a4dd4c57f09889 to Curated Module Committee 0x2570e0b22AD904501dfB0d49575991ACB801dD91 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.3.1. Grant PUBLISH_ROLE 0xf3156f38966c62e303ac6c7519c63e00636409e3b3ca4abecd13cd0092fee53e to CMv2 ConsolidationMigrator 0xc8a7F4917cA03FDCD24a5E11A48Ab448318976e7 on ConsolidationBus 0xd907CE33B4Be423823d1CFFe80BD147E8b8554C8
    1.4.1. Revoke VERIFIER_ROLE 0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09 from Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.5.1. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE 0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094 from Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.6.1. Grant VERIFIER_ROLE 0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09 to CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.7.1. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE 0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094 to CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
    1.8.1. Unregister Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3 from CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7
    1.9.1. Register CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser Curated Module Committee 0x2570e0b22AD904501dfB0d49575991ACB801dD91
2. Add LidoLendActivateMarket EVM script factory 0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xf6f1565f4fd3d29e6bdab86764a50bcde381422f2078614b81b7cc9523b30429110282d90db2fa90ff443d914451cfc585378a1073e8f338e11a97e090e47e2f0fdd3d5abee60e2ec3c241bc213ef3ba16234a7c689999209ce515d7182d4cbbd0a81a130a303237d338a0b5835edcb011ab3afd338d93fc3f107d1fbca49f425321cb27f6ef5cbb94a72c419e90390c85378a1073e8f338e11a97e090e47e2f0fdd3d5a2b4f013c)
3. Add LidoLendCircuitBreakerActions EVM script factory 0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xd0a81a130a303237d338a0b5835edcb011ab3afd338d93fcd0a81a130a303237d338a0b5835edcb011ab3afdc9387332d0a81a130a303237d338a0b5835edcb011ab3afd71a99c22)
4. Add LidoLendGuardianActions EVM script factory 0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x85378a1073e8f338e11a97e090e47e2f0fdd3d5a8543159685378a1073e8f338e11a97e090e47e2f0fdd3d5af3ad2cac85378a1073e8f338e11a97e090e47e2f0fdd3d5a3cab947d85378a1073e8f338e11a97e090e47e2f0fdd3d5ad9101d1785378a1073e8f338e11a97e090e47e2f0fdd3d5adf03d75d85378a1073e8f338e11a97e090e47e2f0fdd3d5a42abe0fd)
5. Add LidoLendMarketManagerActions EVM script factory 0x9D75EaE321976e85e472847AFD21246F1f87dC43 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x85378a1073e8f338e11a97e090e47e2f0fdd3d5a6835da9685378a1073e8f338e11a97e090e47e2f0fdd3d5a084f4e3f85378a1073e8f338e11a97e090e47e2f0fdd3d5a3d15094a85378a1073e8f338e11a97e090e47e2f0fdd3d5abf96eb0185378a1073e8f338e11a97e090e47e2f0fdd3d5ac49495df85378a1073e8f338e11a97e090e47e2f0fdd3d5a2b4f013c)
6. Add LidoLendRiskStewardActions EVM script factory 0x7276CE5f92911216d41C7b0A9C3575DE873763E9 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xc3c241bc213ef3ba16234a7c689999209ce515d7182d4cbbc3c241bc213ef3ba16234a7c689999209ce515d79fdcc880)
7. Add LidoLendApplyIrmConfig EVM script factory 0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x026a770badc7126c7252ef8d407e5b9c56147491151c1adef6f1565f4fd3d29e6bdab86764a50bcde381422f2078614b)

TODO (after vote) Vote #{vote number} passed & executed on {date+time}, block {blockNumber}.
"""

from typing import Dict, List, Tuple

from brownie import ZERO_ADDRESS, interface

from utils.agent import agent_forward
from utils.dual_governance import submit_proposals
from utils.permissions import encode_oz_grant_role, encode_oz_revoke_role
from utils.voting import bake_vote_items, confirm_vote_script, create_vote
from utils.ipfs import upload_vote_ipfs_description, calculate_vote_ipfs_description
from utils.config import (
    get_deployer_account,
    get_is_live,
    get_priority_fee,
    CIRCUIT_BREAKER,
    CURATED_V2_STAKING_MODULE_ADDRESS,
    CURATED_V2_COMMITTEE_MS,
    CURATED_V2_CIRCUIT_BREAKER_PAUSER,
    CURATED_V2_VERIFIER,
    CURATED_V2_VERIFIER_OLD,
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
# CMv2 implementation with top-up allocation controls
CURATED_V2_NEW_IMPL = "0x02bEFd784c6C382a021774472563671Ae23980C0"

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
# Lido Lend, CMv2 Top-Up Allocation Controls, Consolidation Migration & Curated Verifier

1. **Lido Lend: Accept Admin Roles and Approve Committee Mandates** | [Full proposal on IPFS](https://ipfs.filebase.io/ipfs/QmanvVjB7LBcRHGaZpnaA4saPucZePCUBN8x3u3quGVRym) | [Forum discussion](https://research.lido.fi/t/unveiling-lido-lend-security-first-lending/11987) | Audits: [Lido Lend - Cyfrin](https://github.com/lidofinance/audits/blob/main/lend/2026-10-26_Cyfrin_Lido-Lend.pdf), [Easy Track factories - MixBytes](https://github.com/lidofinance/audits/blob/main/lend/2026-11-10-mixbytes-lido-lend-easy-track-factories-audit-report.pdf), [Guardian Daemon SDK - MixBytes](https://github.com/lidofinance/audits/blob/main/lend/2026-11-9-mixbytes-lido-lend-guardian-daemon-sdk.pdf) | Deployment verification: [Lido Lend - Cyfrin](https://github.com/lidofinance/audits/blob/main/lend/2026-11-11-cyfrin-lido-lend-core-deployment-verification.pdf), [Easy Track factories - MixBytes](https://github.com/lidofinance/audits/blob/main/lend/2026-11-10-mixbytes-lido-lend-easy-track-factories-audit-report.pdf) | On-chain items register 6 Lido Lend Easy Track factories to:
    - create and activate markets (item 2)
    - configure CircuitBreaker for markets (item 3)
    - configure Guardians and unban accounts (item 4)
    - configure collateral activation, settlement parameters, supply caps, market fees, and unfreeze markets (item 5)
    - add/remove Risk Stewards for markets (item 6)
    - update market interest-rate model (IRM) configuration (item 7)
2. **Upgrade CMv2 to enable top-up allocation controls**, as [proposed on the forum](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/52) | Audits & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20CMv2%20Top-Up%20Control%20Security%20Audit%20Report%2011-2026.pdf) | On-chain items 1.1.1, 1.2.1.
3. **Enable CMv2 Consolidation Migrator**, as [proposed on the forum](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/53) | Audits: [Certora](https://github.com/lidofinance/audits/blob/main/Certora%20Staking%20Router%20v3%20Audit%20Report%2007-2026.pdf), [Statemind](https://github.com/lidofinance/audits/blob/main/Statemind%20Staking%20Router%20v3%20Audit%20Report%2007-2026.pdf) | Deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20CMv2%20ConsolidationMigrator%20Deployment%20Verification%20Report%2011-2026.pdf) | On-chain item 1.3.1.
4. **Replace CMv2 Verifier with CuratedVerifier** and update CircuitBreaker registration, as [proposed on the forum](https://research.lido.fi/t/future-of-the-curated-module-cmv2-landscape/10929/52) | Audits & deployment verification: [MixBytes](https://github.com/lidofinance/audits/blob/main/MixBytes%20Lido%20CuratedVerifier%20%28CMv2%29%20Security%20Audit%20Report%2011-2026.pdf) | On-chain items 1.4.1 - 1.9.1.
"""

DG_PROPOSAL_METADATA = (
    "Enable CMv2 top-up allocation controls, consolidation migration and Curated Verifier for consolidated validators"
)
DG_SUBMISSION_DESCRIPTION = "1. Submit a Dual Governance proposal to enable CMv2 top-up allocation controls, consolidation migration and Curated Verifier for consolidated validators"


# ================================ Main ======================================
def get_dg_items() -> List[Tuple[str, str]]:
    # staking-modules OssifiableProxy (OZ v5): proxy__upgradeToAndCall(address,bytes), without forceCall_.
    curated_v2_proxy = interface.StakingModulesOssifiableProxy(CURATED_V2_STAKING_MODULE_ADDRESS)
    curated_v2 = interface.CuratedModule(CURATED_V2_STAKING_MODULE_ADDRESS)
    consolidation_bus = interface.ConsolidationBus(CONSOLIDATION_BUS)
    circuit_breaker = interface.CircuitBreaker(CIRCUIT_BREAKER)

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
                    grant_to=CURATED_V2_COMMITTEE_MS,
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
                    grant_to=CONSOLIDATION_MIGRATOR_CMV2,
                )
            ]
        ),
        # 1.4.1. Revoke VERIFIER_ROLE 0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09
        # from Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1.
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=curated_v2,
                    role_name="VERIFIER_ROLE",
                    revoke_from=CURATED_V2_VERIFIER_OLD,
                )
            ]
        ),
        # 1.5.1. Revoke REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE 0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094
        # from Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1.
        agent_forward(
            [
                encode_oz_revoke_role(
                    contract=curated_v2,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    revoke_from=CURATED_V2_VERIFIER_OLD,
                )
            ]
        ),
        # 1.6.1. Grant VERIFIER_ROLE 0x0ce23c3e399818cfee81a7ab0880f714e53d7672b08df0fa62f2843416e1ea09
        # to CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=curated_v2,
                    role_name="VERIFIER_ROLE",
                    grant_to=CURATED_V2_VERIFIER,
                )
            ]
        ),
        # 1.7.1. Grant REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE 0xb169cb0459e6d91326174ff566a2fcc3c7bb31ef3d4d83bec1d5679c611ab094
        # to CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CMv2 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1.
        agent_forward(
            [
                encode_oz_grant_role(
                    contract=curated_v2,
                    role_name="REPORT_REGULAR_WITHDRAWN_VALIDATORS_ROLE",
                    grant_to=CURATED_V2_VERIFIER,
                )
            ]
        ),
        # 1.8.1. Unregister Verifier 0xC392F457960f1B13Ebaf1aa6C065479dD507E1E3
        # from CircuitBreaker 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 (a zero pauser removes the pausable).
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CURATED_V2_VERIFIER_OLD, ZERO_ADDRESS),
                )
            ]
        ),
        # 1.9.1. Register CuratedVerifier 0x8c9C8c8C91D6de09D256264B33E7C54794feb033 on CircuitBreaker
        # 0x6019CB557978296BA3C08a7B73225C0975DFB2F7 with pauser Curated Module Committee 0x2570e0b22AD904501dfB0d49575991ACB801dD91.
        agent_forward(
            [
                (
                    circuit_breaker.address,
                    circuit_breaker.registerPauser.encode_input(CURATED_V2_VERIFIER, CURATED_V2_CIRCUIT_BREAKER_PAUSER),
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
            "2. Add LidoLendActivateMarket EVM script factory 0x17bb2A2B5983D29392A5d31D627D4C8B13383fe6 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xf6f1565f4fd3d29e6bdab86764a50bcde381422f2078614b81b7cc9523b30429110282d90db2fa90ff443d914451cfc585378a1073e8f338e11a97e090e47e2f0fdd3d5abee60e2ec3c241bc213ef3ba16234a7c689999209ce515d7182d4cbbd0a81a130a303237d338a0b5835edcb011ab3afd338d93fc3f107d1fbca49f425321cb27f6ef5cbb94a72c419e90390c85378a1073e8f338e11a97e090e47e2f0fdd3d5a2b4f013c)",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_ACTIVATE_MARKET_FACTORY, ACTIVATE_MARKET_PERMISSIONS),
        ),
        (
            "3. Add LidoLendCircuitBreakerActions EVM script factory 0x4e89cc970F0DBAE2f8C38C083D5D345B4F9e76b8 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xd0a81a130a303237d338a0b5835edcb011ab3afd338d93fcd0a81a130a303237d338a0b5835edcb011ab3afdc9387332d0a81a130a303237d338a0b5835edcb011ab3afd71a99c22)",
            add_evmscript_factory(
                EASYTRACK_LIDO_LEND_CIRCUIT_BREAKER_ACTIONS_FACTORY, CIRCUIT_BREAKER_ACTIONS_PERMISSIONS
            ),
        ),
        (
            "4. Add LidoLendGuardianActions EVM script factory 0x9fE41afb2114bF9430D7f9B1Fb65f0a4B9DeF779 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x85378a1073e8f338e11a97e090e47e2f0fdd3d5a8543159685378a1073e8f338e11a97e090e47e2f0fdd3d5af3ad2cac85378a1073e8f338e11a97e090e47e2f0fdd3d5a3cab947d85378a1073e8f338e11a97e090e47e2f0fdd3d5ad9101d1785378a1073e8f338e11a97e090e47e2f0fdd3d5adf03d75d85378a1073e8f338e11a97e090e47e2f0fdd3d5a42abe0fd)",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_GUARDIAN_ACTIONS_FACTORY, GUARDIAN_ACTIONS_PERMISSIONS),
        ),
        (
            "5. Add LidoLendMarketManagerActions EVM script factory 0x9D75EaE321976e85e472847AFD21246F1f87dC43 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x85378a1073e8f338e11a97e090e47e2f0fdd3d5a6835da9685378a1073e8f338e11a97e090e47e2f0fdd3d5a084f4e3f85378a1073e8f338e11a97e090e47e2f0fdd3d5a3d15094a85378a1073e8f338e11a97e090e47e2f0fdd3d5abf96eb0185378a1073e8f338e11a97e090e47e2f0fdd3d5ac49495df85378a1073e8f338e11a97e090e47e2f0fdd3d5a2b4f013c)",
            add_evmscript_factory(
                EASYTRACK_LIDO_LEND_MARKET_MANAGER_ACTIONS_FACTORY, MARKET_MANAGER_ACTIONS_PERMISSIONS
            ),
        ),
        (
            "6. Add LidoLendRiskStewardActions EVM script factory 0x7276CE5f92911216d41C7b0A9C3575DE873763E9 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0xc3c241bc213ef3ba16234a7c689999209ce515d7182d4cbbc3c241bc213ef3ba16234a7c689999209ce515d79fdcc880)",
            add_evmscript_factory(EASYTRACK_LIDO_LEND_RISK_STEWARD_ACTIONS_FACTORY, RISK_STEWARD_ACTIONS_PERMISSIONS),
        ),
        (
            "7. Add LidoLendApplyIrmConfig EVM script factory 0x5795E73C0c2007ceD7D65cE4FC21c0C09F14C668 to Easy Track 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea (permissions: 0x026a770badc7126c7252ef8d407e5b9c56147491151c1adef6f1565f4fd3d29e6bdab86764a50bcde381422f2078614b)",
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
